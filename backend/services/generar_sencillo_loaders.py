"""Load catalog + market offers for Generar Sencillo (DB adapters)."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import pandas as pd

from analytics_engine.core.criterios_agrupacion import (
    ATRIBUTOS_VALIDOS_ORDER,
    CRITERIOS_AGRUPACION_DEFAULT,
    resolve_criterios_agrupacion,
)

logger = logging.getLogger(__name__)

QUERY_PATH = os.path.join(os.path.dirname(__file__), "..", "queries", "pedidos.sql")

# Legacy fallback only — parameterized IN against Mercado_Vivo (UNION view) is ~20s+.
MERCADO_VIVO_IN_CHUNK = 2000

# CodProv strings excluded from Generar market offers (ops 2026-07-21).
# ProveedorConfig.Activo alone does NOT filter Mercado_Vivo — must list here.
# MASTRANTO_B = Barquisimeto (inactive); Centro remains MASTRANTO_C.
MERCADO_PROVEEDORES_EXCLUIDOS: frozenset[str] = frozenset({"MASTRANTO_B"})

_OFFERS_EMPTY = pd.DataFrame(
    columns=[
        "codigo_barras",
        "proveedor",
        "precio_unitario_final",
        "stock_disponible",
        "descripcion_producto",
    ]
)

# ADR-0021 / 0024: lookback diario; fallback semanal si cobertura diaria baja
try:
    from analytics_engine.historico_stats.constants import (
        HISTORICO_DESVIO_LOOKBACK_DAYS as _LOOKBACK,
        MIN_DIAS_DIARIO_COBERTURA as _MIN_DIAS,
    )

    HISTORICO_DESVIO_LOOKBACK_DAYS = int(_LOOKBACK)
    MIN_DIAS_DIARIO_COBERTURA = int(_MIN_DIAS)
except Exception:  # pragma: no cover — path/import edge in some test harnesses
    HISTORICO_DESVIO_LOOKBACK_DAYS = 120
    MIN_DIAS_DIARIO_COBERTURA = 7

_SQL_HISTORICO_BASELINES_OPENJSON = """
    SELECT
        CAST(h.codigo_barras AS NVARCHAR(50)) AS codigo_barras,
        AVG(CAST(h.precio_mediana AS FLOAT)) AS media_de_mediana,
        AVG(CAST(h.precio_min AS FLOAT)) AS media_min_diario,
        COUNT_BIG(*) AS dias_hist,
        MIN(h.fecha_snapshot) AS fecha_desde,
        MAX(h.fecha_snapshot) AS fecha_hasta
    FROM Analitica.Mercado_Historico h
    INNER JOIN OPENJSON(?) WITH (codigo_barras NVARCHAR(50) '$.b') AS j
      ON CAST(h.codigo_barras AS NVARCHAR(50)) = j.codigo_barras
    WHERE h.fecha_snapshot >= DATEADD(day, -?, CAST(GETDATE() AS date))
      AND h.precio_mediana IS NOT NULL
      AND CAST(h.precio_mediana AS FLOAT) > 0
    GROUP BY CAST(h.codigo_barras AS NVARCHAR(50))
"""

_SQL_SEMANAL_BASELINES_OPENJSON = """
    SELECT
        CAST(s.codigo_barras AS NVARCHAR(50)) AS codigo_barras,
        AVG(CAST(s.precio_mediana AS FLOAT)) AS media_de_mediana,
        AVG(CAST(s.media_precio_min AS FLOAT)) AS media_min_diario,
        COUNT_BIG(*) AS semanas_hist,
        MIN(s.fecha_semana_ini) AS fecha_desde,
        MAX(s.fecha_semana_fin) AS fecha_hasta
    FROM Analitica.Mercado_Historico_Semanal s
    INNER JOIN OPENJSON(?) WITH (codigo_barras NVARCHAR(50) '$.b') AS j
      ON CAST(s.codigo_barras AS NVARCHAR(50)) = j.codigo_barras
    WHERE s.fecha_semana_fin >= DATEADD(day, -?, CAST(GETDATE() AS date))
      AND s.precio_mediana IS NOT NULL
      AND CAST(s.precio_mediana AS FLOAT) > 0
    GROUP BY CAST(s.codigo_barras AS NVARCHAR(50))
"""

# ADR-0025/0026: PDR view (+ ppp for gate)
_SQL_MERCADO_VIVO_IN = """
    SELECT codigo_barras, proveedor, precio_unitario_final,
           stock_disponible, descripcion_producto, pdr, pdr_semaforo,
           peso_producto_en_proveedor
    FROM Analitica.Mercado_Vivo_PDR
    WHERE codigo_barras IN ({placeholders})
"""

_SQL_MERCADO_VIVO_OPENJSON = """
    SELECT mv.codigo_barras, mv.proveedor, mv.precio_unitario_final,
           mv.stock_disponible, mv.descripcion_producto, mv.pdr, mv.pdr_semaforo,
           mv.peso_producto_en_proveedor
    FROM Analitica.Mercado_Vivo_PDR mv
    INNER JOIN OPENJSON(?) WITH (codigo_barras NVARCHAR(50) '$.b') AS j
      ON CAST(mv.codigo_barras AS NVARCHAR(50)) = j.codigo_barras
"""

_SQL_MERCADO_VIVO_FULL = """
    SELECT codigo_barras, proveedor, precio_unitario_final,
           stock_disponible, descripcion_producto, pdr, pdr_semaforo,
           peso_producto_en_proveedor
    FROM Analitica.Mercado_Vivo_PDR
"""


def _ensure_analytics_path() -> None:
    import sys

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if root not in sys.path:
        sys.path.insert(0, root)


def map_catalog_dataframe(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Map legacy pedidos.sql columns → seam catalog rows."""
    if df.empty:
        return []
    out = df.copy()
    rename = {}
    if "CodProd" in out.columns:
        rename["CodProd"] = "barra"
    if "Descrip" in out.columns:
        rename["Descrip"] = "descripcion"
    if "RotacionMensual" in out.columns:
        rename["RotacionMensual"] = "rotacion_mensual"
    if "Existen" in out.columns:
        rename["Existen"] = "existen"
    if "Instancia" in out.columns:
        rename["Instancia"] = "categoria"
    out = out.rename(columns=rename)
    out["barra"] = out["barra"].astype(str)
    if "descripcion" not in out.columns:
        out["descripcion"] = ""
    if "rotacion_mensual" not in out.columns:
        out["rotacion_mensual"] = 0.0
    if "existen" not in out.columns:
        out["existen"] = 0.0
    if "es_generico" not in out.columns:
        out["es_generico"] = True
    for attr in ATRIBUTOS_VALIDOS_ORDER:
        if attr not in out.columns:
            out[attr] = ""
        else:
            out[attr] = out[attr].fillna("").astype(str).replace(
                {"nan": "", "None": "", "<NA>": "", "NaT": ""}
            ).str.strip()
    if "elasticidad_demanda" not in out.columns:
        out["elasticidad_demanda"] = 0.0
    else:
        out["elasticidad_demanda"] = pd.to_numeric(
            out["elasticidad_demanda"], errors="coerce"
        ).fillna(0.0)
    cols = [
        "barra",
        "descripcion",
        "rotacion_mensual",
        "existen",
        "es_generico",
        "categoria",
        "elasticidad_demanda",
        *ATRIBUTOS_VALIDOS_ORDER,
    ]
    cols = [c for c in cols if c in out.columns]
    return out[cols].to_dict(orient="records")


def map_mercado_vivo_dataframe(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Map Analitica.Mercado_Vivo_PDR → market_offers rows (ADR-0025)."""
    if df.empty:
        return []
    out = df.copy()
    rename = {
        "codigo_barras": "barra",
        "precio_unitario_final": "precio",
        "stock_disponible": "stock_proveedor",
        "descripcion_producto": "descripcion",
        "peso_producto_en_proveedor": "ppp",
    }
    out = out.rename(columns={k: v for k, v in rename.items() if k in out.columns})
    if "barra" not in out.columns:
        return []
    out["barra"] = out["barra"].astype(str)
    if "proveedor" not in out.columns:
        out["proveedor"] = ""
    if "precio" not in out.columns:
        out["precio"] = 0.0
    if "stock_proveedor" not in out.columns:
        out["stock_proveedor"] = None
    excl = {p.strip().upper() for p in MERCADO_PROVEEDORES_EXCLUIDOS if p}
    if excl and "proveedor" in out.columns:
        before = len(out)
        out = out.loc[
            ~out["proveedor"].astype(str).str.strip().str.upper().isin(excl)
        ].copy()
        dropped = before - len(out)
        if dropped:
            logger.info(
                "Mercado exclude %s: dropped %s offer rows",
                sorted(excl),
                dropped,
            )
    cols = ["barra", "proveedor", "precio", "stock_proveedor"]
    if "descripcion" in out.columns:
        cols.append("descripcion")
    if "pdr" in out.columns:
        cols.append("pdr")
    if "pdr_semaforo" in out.columns:
        cols.append("pdr_semaforo")
    if "ppp" in out.columns:
        cols.append("ppp")
    return out[cols].to_dict(orient="records")


def normalize_offers_to_usd(
    offers: Sequence[Dict[str, Any]],
    *,
    moneda_by_prov: Dict[str, str],
    dolarbcv: float,
) -> List[Dict[str, Any]]:
    """Normalize Mercado_Vivo unit prices to USD before desvío / scoring.

    MonedaOferta=VES → precio / dolarbcv (ecosistema dbo.dolartoday).
    MonedaOferta=USD → unchanged. Always stores precio in USD thereafter.
    """
    from .fx_bcv import to_usd

    out: List[Dict[str, Any]] = []
    for raw in offers:
        row = dict(raw)
        prov_u = str(row.get("proveedor") or "").strip().upper()
        mon = moneda_by_prov.get(prov_u, "USD")
        try:
            raw_px = float(row.get("precio") or 0.0)
        except (TypeError, ValueError):
            raw_px = 0.0
        row["precio_raw"] = round(raw_px, 6)
        row["moneda_oferta"] = mon
        row["precio"] = round(to_usd(raw_px, moneda=mon, dolarbcv=dolarbcv), 6)
        row["dolarbcv"] = float(dolarbcv)
        out.append(row)
    return out


def enrich_offers_with_desvio(
    offers: Sequence[Dict[str, Any]],
    baselines: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Attach media_de_mediana / media_min_diario / desvio (ADR-0021 / 0024).

    Comparativa vs histórico siempre en USD: `precio` debe estar ya normalizado
    a USD (normalize_offers_to_usd). desvio = (precio_usd − media) / media.
    """
    from analytics_engine.core.nonlinear import calculate_price_deviation

    enriched: List[Dict[str, Any]] = []
    for raw in offers:
        row = dict(raw)
        barra = str(row.get("barra") or "").strip()
        base = baselines.get(barra)
        if not base:
            enriched.append(row)
            continue
        media = float(base["media_de_mediana"])
        row["media_de_mediana"] = round(media, 6)
        if base.get("media_min_diario") is not None:
            row["media_min_diario"] = round(float(base["media_min_diario"]), 6)
        row["dias_hist"] = int(base.get("dias_hist") or 0)
        if base.get("semanas_hist") is not None:
            row["semanas_hist"] = int(base["semanas_hist"] or 0)
        fuente = str(base.get("fuente_baseline") or "diario")
        row["fuente_baseline"] = fuente
        try:
            precio = float(row.get("precio") or 0.0)
        except (TypeError, ValueError):
            precio = 0.0
        row["desvio"] = round(calculate_price_deviation(precio, media), 6)
        row["delta_vs_media_usd"] = round(precio - media, 6)
        enriched.append(row)
    return enriched


def _parse_baseline_row(
    row: Sequence[Any],
    *,
    fuente: str,
    count_key: str,
) -> Optional[Dict[str, Any]]:
    barra = str(row[0] or "").strip()
    if not barra:
        return None
    try:
        media_med_f = float(row[1]) if row[1] is not None else None
    except (TypeError, ValueError):
        media_med_f = None
    try:
        media_min_f = float(row[2]) if row[2] is not None else None
    except (TypeError, ValueError):
        media_min_f = None
    if media_med_f is None or media_med_f <= 0:
        return None
    out: Dict[str, Any] = {
        "media_de_mediana": media_med_f,
        "media_min_diario": media_min_f,
        count_key: int(row[3] or 0),
        "fecha_desde": row[4].isoformat() if row[4] is not None else None,
        "fecha_hasta": row[5].isoformat() if row[5] is not None else None,
        "fuente_baseline": fuente,
    }
    if count_key == "dias_hist":
        out["dias_hist"] = out[count_key]
    else:
        out["semanas_hist"] = out[count_key]
        out["dias_hist"] = 0
    return out


def fetch_historico_baselines(
    conn: Any,
    barras: Sequence[str],
    *,
    lookback_days: int = HISTORICO_DESVIO_LOOKBACK_DAYS,
    min_dias_diario: int = MIN_DIAS_DIARIO_COBERTURA,
) -> Dict[str, Dict[str, Any]]:
    """Baselines 120d: diario primero; fallback semanal si cobertura &lt; min_dias.

    Returns barra → media_de_mediana, media_min_diario, dias_hist/semanas_hist,
    fuente_baseline (diario|semanal|mixto).
    """
    clean = _normalize_barras(barras)
    if not clean:
        return {}
    payload = json.dumps([{"b": b} for b in clean])
    cur = conn.cursor()
    cur.execute(
        _SQL_HISTORICO_BASELINES_OPENJSON,
        [payload, int(lookback_days)],
    )
    out: Dict[str, Dict[str, Any]] = {}
    for row in cur.fetchall():
        parsed = _parse_baseline_row(row, fuente="diario", count_key="dias_hist")
        if parsed:
            out[str(row[0]).strip()] = parsed

    need_weekly = [
        b
        for b in clean
        if b not in out or int(out[b].get("dias_hist") or 0) < int(min_dias_diario)
    ]
    if not need_weekly:
        return out

    payload_w = json.dumps([{"b": b} for b in need_weekly])
    try:
        cur.execute(
            _SQL_SEMANAL_BASELINES_OPENJSON,
            [payload_w, int(lookback_days)],
        )
        weekly_rows = cur.fetchall()
    except Exception as exc:
        logger.warning("Mercado_Historico_Semanal baselines skipped: %s", exc)
        return out

    for row in weekly_rows:
        parsed = _parse_baseline_row(row, fuente="semanal", count_key="semanas_hist")
        if not parsed:
            continue
        barra = str(row[0]).strip()
        prev = out.get(barra)
        if not prev:
            out[barra] = parsed
            continue
        # Cobertura diaria insuficiente → fallback semanal (ADR-0024)
        if int(prev.get("dias_hist") or 0) < int(min_dias_diario):
            parsed["dias_hist"] = int(prev.get("dias_hist") or 0)
            parsed["fuente_baseline"] = (
                "mixto" if int(prev.get("dias_hist") or 0) > 0 else "semanal"
            )
            out[barra] = parsed
    return out


def prioritize_barras_for_offers(
    catalog_rows: Sequence[Dict[str, Any]],
    *,
    cobertura_dias: float = 30.0,
    only_positive_need: bool = True,
    max_barras: Optional[int] = None,
    criterios_agrupacion: Optional[Sequence[str]] = None,
) -> List[str]:
    """Unique barras for Mercado_Vivo lookup.

    Prefers SKUs with positive SKU-level need (rot×cobertura/30 − stock),
    highest rotación first. Optionally expands to MDM siblings so sucedáneos
    remain visible without scanning the entire catalog.
    """
    attrs = resolve_criterios_agrupacion(criterios_agrupacion)
    scored: List[Tuple[float, str, Dict[str, Any]]] = []
    for row in catalog_rows:
        barra = str(row.get("barra") or "").strip()
        if not barra:
            continue
        rot = float(row.get("rotacion_mensual") or 0.0)
        stock = float(row.get("existen") or 0.0)
        qty = int(round(rot * float(cobertura_dias) / 30.0 - stock))
        if only_positive_need and qty <= 0:
            continue
        scored.append((rot, barra, row))

    scored.sort(key=lambda t: t[0], reverse=True)
    primary: List[str] = []
    seen: set[str] = set()
    group_keys: set[Tuple[str, ...]] = set()
    for rot, barra, row in scored:
        if barra in seen:
            continue
        seen.add(barra)
        primary.append(barra)
        vals = tuple(str(row.get(a) or "").strip() for a in attrs)
        if any(vals):
            group_keys.add(vals)
        if max_barras is not None and len(primary) >= int(max_barras):
            break

    # Include MDM siblings of selected primary SKUs (sucedáneo pool).
    if group_keys:
        for row in catalog_rows:
            barra = str(row.get("barra") or "").strip()
            if not barra or barra in seen:
                continue
            vals = tuple(str(row.get(a) or "").strip() for a in attrs)
            if vals in group_keys:
                seen.add(barra)
                primary.append(barra)

    if not primary and catalog_rows:
        # Fallback: all barras by rotación (still chunked by caller).
        ranked = sorted(
            catalog_rows,
            key=lambda r: float(r.get("rotacion_mensual") or 0.0),
            reverse=True,
        )
        for row in ranked:
            barra = str(row.get("barra") or "").strip()
            if barra and barra not in seen:
                seen.add(barra)
                primary.append(barra)

    return primary


def _normalize_barras(barras: Sequence[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for raw in barras:
        b = str(raw or "").strip()
        if not b or b in seen:
            continue
        seen.add(b)
        out.append(b)
    return out


def _records_to_offers_df(cols: Sequence[str], rows: Sequence[Any]) -> pd.DataFrame:
    if not rows:
        return _OFFERS_EMPTY.copy()
    return pd.DataFrame.from_records(rows, columns=list(cols))


def _read_mercado_chunk_via_cursor(conn: Any, sql: str, chunk: Sequence[str]) -> pd.DataFrame:
    """Prefer raw cursor — avoids pandas/pyodbc 'Gaps in blk ref_locs' on some chunks."""
    cur = conn.cursor()
    cur.execute(sql, list(chunk))
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    return _records_to_offers_df(cols, rows)


def _fetch_mercado_via_openjson(conn: Any, barras: Sequence[str]) -> pd.DataFrame:
    """JOIN Mercado_Vivo once via OPENJSON — ~0.5s vs ~20s for big IN lists."""
    payload = json.dumps([{"b": b} for b in barras])
    cur = conn.cursor()
    cur.execute(_SQL_MERCADO_VIVO_OPENJSON, [payload])
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    return _records_to_offers_df(cols, rows)


def _fetch_mercado_via_full_scan_filter(
    conn: Any, wanted: Set[str]
) -> pd.DataFrame:
    """Scan Mercado_Vivo (~65k rows, <1s) and filter barras in Python."""
    cur = conn.cursor()
    cur.execute(_SQL_MERCADO_VIVO_FULL)
    cols = [d[0] for d in cur.description]
    # codigo_barras is column 0 in the SELECT
    rows = [r for r in cur.fetchall() if str(r[0]).strip() in wanted]
    return _records_to_offers_df(cols, rows)


def _fetch_mercado_via_chunked_in(
    conn: Any,
    barras: Sequence[str],
    *,
    chunk_size: int,
    read_sql=None,
) -> pd.DataFrame:
    """Legacy path: chunked parameterized IN (slow against UNION view)."""
    chunks_out: List[pd.DataFrame] = []
    size = max(1, int(chunk_size))
    for i in range(0, len(barras), size):
        chunk = list(barras[i : i + size])
        placeholders = ",".join(["?"] * len(chunk))
        sql = _SQL_MERCADO_VIVO_IN.format(placeholders=placeholders)
        try:
            if read_sql is not None:
                part = read_sql(sql, conn, params=chunk)
            else:
                part = _read_mercado_chunk_via_cursor(conn, sql, chunk)
        except Exception as exc:
            logger.warning(
                "Mercado_Vivo chunk %s–%s failed (%s barras): %s",
                i,
                i + len(chunk),
                len(chunk),
                exc,
            )
            continue
        if part is not None and not getattr(part, "empty", True):
            chunks_out.append(part.copy())

    if not chunks_out:
        return _OFFERS_EMPTY.copy()
    return pd.concat(chunks_out, ignore_index=True).copy()


def fetch_mercado_vivo_offers(
    conn: Any,
    barras: Sequence[str],
    *,
    chunk_size: int = MERCADO_VIVO_IN_CHUNK,
    read_sql=None,
    strategy: Optional[str] = None,
) -> pd.DataFrame:
    """Load Mercado_Vivo for selected barras.

    Default strategy order (live DB):
      1) OPENJSON join (one scan of the view, ~0.5s)
      2) full view scan + Python filter (~0.7s)
      3) chunked IN (legacy; ~20s — last resort)

    If ``read_sql`` is provided (unit tests), uses chunked IN only.
    """
    clean = _normalize_barras(barras)
    if not clean:
        return _OFFERS_EMPTY.copy()

    if read_sql is not None or strategy == "chunked_in":
        return _fetch_mercado_via_chunked_in(
            conn, clean, chunk_size=chunk_size, read_sql=read_sql
        )

    if strategy in (None, "openjson", "auto"):
        try:
            out = _fetch_mercado_via_openjson(conn, clean)
            logger.info(
                "Mercado_Vivo via OPENJSON: barras=%s offer_rows=%s",
                len(clean),
                len(out),
            )
            return out
        except Exception as exc:
            if strategy == "openjson":
                raise
            logger.warning("Mercado_Vivo OPENJSON failed, trying full scan: %s", exc)

    if strategy in (None, "full_scan", "auto"):
        try:
            out = _fetch_mercado_via_full_scan_filter(conn, set(clean))
            logger.info(
                "Mercado_Vivo via full-scan filter: barras=%s offer_rows=%s",
                len(clean),
                len(out),
            )
            return out
        except Exception as exc:
            if strategy == "full_scan":
                raise
            logger.warning("Mercado_Vivo full scan failed, falling back to IN: %s", exc)

    return _fetch_mercado_via_chunked_in(
        conn, clean, chunk_size=chunk_size, read_sql=None
    )


def _read_catalog_via_cursor(conn: Any, query: str) -> pd.DataFrame:
    """Cursor path for pedidos.sql — avoids pandas Gaps-in-blk on large result."""
    cur = conn.cursor()
    cur.execute(query)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame.from_records(rows, columns=cols)


def load_catalog_and_offers_from_db(
    *,
    categorias: Optional[Sequence[str]] = None,
    include_generics: bool = True,
    include_brands: bool = True,
    criterios_agrupacion: Optional[Sequence[str]] = None,
    cobertura_dias: float = 30.0,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Load SAPROD rotation catalog + Mercado_Vivo offers (productive path)."""
    _ensure_analytics_path()
    import database

    with open(QUERY_PATH, "r", encoding="utf-8-sig") as f:
        query = f.read().strip()

    # Same filter placeholder strategy as legacy generate (generics/brands)
    if include_generics and include_brands:
        filter_sql = "1=1"
    elif include_generics and not include_brands:
        filter_sql = f"""EXISTS (
            SELECT 1 FROM Procurement.principio_activo pa
            WHERE LEFT(p.Descrip, 7) = LEFT(pa.descripcion, 7)
        )"""
    elif include_brands and not include_generics:
        filter_sql = f"""NOT EXISTS (
            SELECT 1 FROM Procurement.principio_activo pa
            WHERE LEFT(p.Descrip, 7) = LEFT(pa.descripcion, 7)
        )"""
    else:
        filter_sql = "1=0"
    query = query.replace("/* PRODUCT_FILTER_PLACEHOLDER */", f"AND ({filter_sql})")

    conn = database.get_db_connection()
    try:
        catalog_df = _read_catalog_via_cursor(conn, query)
        if categorias:
            wanted = {str(c).strip() for c in categorias if str(c).strip()}
            if wanted and "Instancia" in catalog_df.columns:
                catalog_df = catalog_df[
                    catalog_df["Instancia"].astype(str).isin(wanted)
                ]
        catalog_rows = map_catalog_dataframe(catalog_df)
        barras = prioritize_barras_for_offers(
            catalog_rows,
            cobertura_dias=float(cobertura_dias),
            criterios_agrupacion=criterios_agrupacion,
        )
        offers_df = fetch_mercado_vivo_offers(conn, barras)
        offers_rows = map_mercado_vivo_dataframe(offers_df)
        # Normalizar a USD antes del desvío (comparativa histórico siempre $).
        try:
            from .fx_bcv import fetch_dolarbcv
            from .proveedor_config_loader import (
                fetch_proveedor_groups,
                moneda_oferta_index_from_groups,
            )

            dolarbcv = fetch_dolarbcv(conn)
            groups = fetch_proveedor_groups(conn)
            moneda_by_prov = moneda_oferta_index_from_groups(groups)
            offers_rows = normalize_offers_to_usd(
                offers_rows,
                moneda_by_prov=moneda_by_prov,
                dolarbcv=dolarbcv,
            )
            n_ves = sum(1 for o in offers_rows if o.get("moneda_oferta") == "VES")
            logger.info(
                "Offers USD-normalized: bcv=%s ves_rows=%s/%s",
                dolarbcv,
                n_ves,
                len(offers_rows),
            )
        except Exception as exc:
            logger.warning("USD normalize skipped: %s", exc)
        try:
            baselines = fetch_historico_baselines(conn, barras)
            offers_rows = enrich_offers_with_desvio(offers_rows, baselines)
            with_desvio = sum(1 for o in offers_rows if o.get("desvio") is not None)
        except Exception as exc:
            logger.warning(
                "Mercado_Historico baselines failed (desvio omitted): %s", exc
            )
            baselines = {}
            with_desvio = 0
        logger.info(
            "Generar Sencillo load: catalog=%s barras=%s offer_rows=%s "
            "cobertura=%s hist_barras=%s offers_with_desvio=%s",
            len(catalog_rows),
            len(barras),
            len(offers_rows),
            cobertura_dias,
            len(baselines),
            with_desvio,
        )
        return catalog_rows, offers_rows
    finally:
        try:
            conn.close()
        except Exception:
            pass
