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

_OFFERS_EMPTY = pd.DataFrame(
    columns=[
        "codigo_barras",
        "proveedor",
        "precio_unitario_final",
        "stock_disponible",
        "descripcion_producto",
    ]
)

# ADR-0021: lookback for AVG(precio_mediana) / AVG(precio_min) on Mercado_Historico
HISTORICO_DESVIO_LOOKBACK_DAYS = 90

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

_SQL_MERCADO_VIVO_IN = """
    SELECT codigo_barras, proveedor, precio_unitario_final,
           stock_disponible, descripcion_producto
    FROM Analitica.Mercado_Vivo
    WHERE codigo_barras IN ({placeholders})
"""

_SQL_MERCADO_VIVO_OPENJSON = """
    SELECT mv.codigo_barras, mv.proveedor, mv.precio_unitario_final,
           mv.stock_disponible, mv.descripcion_producto
    FROM Analitica.Mercado_Vivo mv
    INNER JOIN OPENJSON(?) WITH (codigo_barras NVARCHAR(50) '$.b') AS j
      ON CAST(mv.codigo_barras AS NVARCHAR(50)) = j.codigo_barras
"""

_SQL_MERCADO_VIVO_FULL = """
    SELECT codigo_barras, proveedor, precio_unitario_final,
           stock_disponible, descripcion_producto
    FROM Analitica.Mercado_Vivo
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
    """Map Analitica.Mercado_Vivo → market_offers rows."""
    if df.empty:
        return []
    out = df.copy()
    rename = {
        "codigo_barras": "barra",
        "precio_unitario_final": "precio",
        "stock_disponible": "stock_proveedor",
        "descripcion_producto": "descripcion",
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
    cols = ["barra", "proveedor", "precio", "stock_proveedor"]
    if "descripcion" in out.columns:
        cols.append("descripcion")
    return out[cols].to_dict(orient="records")


def fetch_historico_baselines(
    conn: Any,
    barras: Sequence[str],
    *,
    lookback_days: int = HISTORICO_DESVIO_LOOKBACK_DAYS,
) -> Dict[str, Dict[str, Any]]:
    """AVG(precio_mediana) and AVG(precio_min) per barra from Mercado_Historico.

    Returns barra → {media_de_mediana, media_min_diario, dias_hist, fecha_desde, fecha_hasta}.
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
        barra = str(row[0] or "").strip()
        if not barra:
            continue
        media_med = row[1]
        media_min = row[2]
        try:
            media_med_f = float(media_med) if media_med is not None else None
        except (TypeError, ValueError):
            media_med_f = None
        try:
            media_min_f = float(media_min) if media_min is not None else None
        except (TypeError, ValueError):
            media_min_f = None
        if media_med_f is None or media_med_f <= 0:
            continue
        out[barra] = {
            "media_de_mediana": media_med_f,
            "media_min_diario": media_min_f,
            "dias_hist": int(row[3] or 0),
            "fecha_desde": row[4].isoformat() if row[4] is not None else None,
            "fecha_hasta": row[5].isoformat() if row[5] is not None else None,
        }
    return out


def enrich_offers_with_desvio(
    offers: Sequence[Dict[str, Any]],
    baselines: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Attach media_de_mediana / media_min_diario / desvio (ADR-0021).

    desvio = (precio − media_de_mediana) / media_de_mediana. Negative = cheaper.
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
        try:
            precio = float(row.get("precio") or 0.0)
        except (TypeError, ValueError):
            precio = 0.0
        row["desvio"] = round(calculate_price_deviation(precio, media), 6)
        enriched.append(row)
    return enriched


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
