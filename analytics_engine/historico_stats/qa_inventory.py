"""Inventario SQL y QA pre-stats (Fase 0)."""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from .constants import HISTORICO_DESVIO_LOOKBACK_DAYS, RECONVERSION_DATE
from .currency import classify_row_dict, to_usd_candidate
from .outliers import exclusion_rows, flag_mad_outliers

logger = logging.getLogger(__name__)

_SQL_INVENTORY = """
SELECT
  (SELECT COUNT_BIG(*) FROM Analitica.Mercado_Historico
   WHERE fecha_snapshot >= ?) AS hist_rows_since_reconversion,
  (SELECT COUNT(DISTINCT CAST(codigo_barras AS NVARCHAR(50)))
   FROM Analitica.Mercado_Historico
   WHERE fecha_snapshot >= ?) AS hist_barras,
  (SELECT MIN(fecha_snapshot) FROM Analitica.Mercado_Historico) AS hist_min_fecha,
  (SELECT MAX(fecha_snapshot) FROM Analitica.Mercado_Historico) AS hist_max_fecha,
  (SELECT COUNT_BIG(*) FROM Analitica.Mercado_Vivo) AS vivo_rows,
  (SELECT COUNT_BIG(*) FROM dbo.SACOMP WHERE FechaE >= ?) AS sacomp_rows,
  (SELECT COUNT_BIG(*) FROM dbo.SAITEMCOM i
   INNER JOIN dbo.SACOMP c ON c.NumeroD = i.NumeroD
   WHERE c.FechaE >= ?) AS saitemcom_rows,
  (SELECT COUNT_BIG(*) FROM dbo.dolartoday
   WHERE fecha >= ?) AS bcv_rows
"""

_SQL_HIST_SAMPLE = """
SELECT TOP (?)
  CAST(codigo_barras AS NVARCHAR(50)) AS codigo_barras,
  CAST(fecha_snapshot AS date) AS fecha,
  CAST(precio_mediana AS FLOAT) AS precio,
  CAST(precio_min AS FLOAT) AS precio_min_diario
FROM Analitica.Mercado_Historico
WHERE fecha_snapshot >= ?
  AND precio_mediana IS NOT NULL
  AND CAST(precio_mediana AS FLOAT) > 0
ORDER BY fecha_snapshot DESC
"""

_SQL_BCV_BY_DATE = """
SELECT CAST(fecha AS date) AS fecha, CAST(dolarbcv AS FLOAT) AS dolarbcv
FROM dbo.dolartoday
WHERE dolarbcv IS NOT NULL AND dolarbcv > 0 AND fecha >= ?
"""


def _default_reports_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "reports" / "historico_qa"


def run_inventory(conn: Any, *, since: date = RECONVERSION_DATE) -> Dict[str, Any]:
    cur = conn.cursor()
    d = since.isoformat()
    cur.execute(_SQL_INVENTORY, [d, d, d, d, d])
    row = cur.fetchone()
    keys = [
        "hist_rows_since_reconversion",
        "hist_barras",
        "hist_min_fecha",
        "hist_max_fecha",
        "vivo_rows",
        "sacomp_rows",
        "saitemcom_rows",
        "bcv_rows",
    ]
    out: Dict[str, Any] = {"since": d, "lookback_days_motor": HISTORICO_DESVIO_LOOKBACK_DAYS}
    for i, k in enumerate(keys):
        v = row[i] if row else None
        if hasattr(v, "isoformat"):
            v = v.isoformat()
        out[k] = int(v) if isinstance(v, (int,)) or (hasattr(v, "__int__") and k.endswith("rows") or k.endswith("barras")) else v
        try:
            if k.endswith(("rows", "barras")) and v is not None:
                out[k] = int(v)
        except (TypeError, ValueError):
            out[k] = v
    return out


def load_bcv_map(conn: Any, *, since: date = RECONVERSION_DATE) -> Dict[str, float]:
    cur = conn.cursor()
    cur.execute(_SQL_BCV_BY_DATE, [since.isoformat()])
    out: Dict[str, float] = {}
    for r in cur.fetchall():
        f = r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0])[:10]
        try:
            out[f] = float(r[1])
        except (TypeError, ValueError):
            continue
    return out


def sample_historico_for_qa(
    conn: Any,
    *,
    since: date = RECONVERSION_DATE,
    top_n: int = 50000,
) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute(_SQL_HIST_SAMPLE, [int(top_n), since.isoformat()])
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    return pd.DataFrame.from_records(rows, columns=cols)


def annotate_qa_frame(
    df: pd.DataFrame,
    bcv_by_date: Dict[str, float],
    *,
    mediana_usd_by_barra: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """Clasifica moneda, convierte a USD candidato, marca BCV missing + MAD."""
    if df is None or df.empty:
        return pd.DataFrame()

    records = []
    med_map = mediana_usd_by_barra or {}
    for _, raw in df.iterrows():
        row = raw.to_dict()
        barra = str(row.get("codigo_barras") or "").strip()
        fecha = row.get("fecha")
        fkey = fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha)[:10]
        row = classify_row_dict(row, mediana_usd_barra=med_map.get(barra))
        bcv = bcv_by_date.get(fkey)
        row["bcv_missing"] = bcv is None and row.get("moneda_clasificada") == "VES"
        row["dolarbcv"] = bcv
        try:
            if row["bcv_missing"]:
                row["precio_usd"] = None
            else:
                row["precio_usd"] = to_usd_candidate(
                    float(row.get("precio") or 0.0),
                    moneda=row["moneda_clasificada"],
                    dolarbcv=float(bcv or 1.0) if row["moneda_clasificada"] == "VES" else 1.0,
                )
        except (TypeError, ValueError):
            row["precio_usd"] = None
            row["bcv_missing"] = True
        records.append(row)

    out = pd.DataFrame(records)
    out = flag_mad_outliers(out, precio_col="precio_usd", barra_col="codigo_barras")
    return out


def write_qa_artifacts(
    inventory: Dict[str, Any],
    annotated: pd.DataFrame,
    *,
    out_dir: Optional[Path] = None,
) -> Dict[str, str]:
    """Escribe inventory.json, exclusiones.csv, qa_summary.html."""
    dest = Path(out_dir) if out_dir else _default_reports_dir()
    dest.mkdir(parents=True, exist_ok=True)

    inv_path = dest / "inventory.json"
    inv_path.write_text(json.dumps(inventory, indent=2, default=str), encoding="utf-8")

    excl = exclusion_rows(annotated) if annotated is not None and not annotated.empty else pd.DataFrame()
    excl_path = dest / "exclusiones.csv"
    excl.to_csv(excl_path, index=False)

    n = 0 if annotated is None or annotated.empty else len(annotated)
    n_out = 0 if excl.empty else len(excl)
    n_heur = 0
    n_bcv = 0
    if annotated is not None and not annotated.empty:
        n_heur = int((annotated.get("fuente_moneda") == "heuristica_magnitud").sum()) if "fuente_moneda" in annotated.columns else 0
        n_bcv = int(annotated["bcv_missing"].fillna(False).sum()) if "bcv_missing" in annotated.columns else 0

    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><title>QA Histórico pre-stats</title></head>
<body>
<h1>QA Histórico pre-stats</h1>
<p>Generado: {datetime.utcnow().isoformat()}Z</p>
<pre>{json.dumps(inventory, indent=2, default=str)}</pre>
<ul>
  <li>Filas anotadas (sample): {n}</li>
  <li>Exclusiones / revisión: {n_out}</li>
  <li>Heurística magnitud: {n_heur}</li>
  <li>BCV missing (VES): {n_bcv}</li>
</ul>
<p>Ver <code>exclusiones.csv</code> y <code>inventory.json</code> en este directorio.</p>
<p>Proceso: <code>analytics_engine/historico_stats/README.md</code></p>
</body></html>
"""
    html_path = dest / "qa_summary.html"
    html_path.write_text(html, encoding="utf-8")

    # Profiling opcional
    try:
        from ydata_profiling import ProfileReport  # type: ignore

        if annotated is not None and not annotated.empty:
            cols = [c for c in ("precio", "precio_usd", "moneda_clasificada", "fuente_moneda") if c in annotated.columns]
            if cols:
                profile = ProfileReport(
                    annotated[cols].head(20000),
                    title="Histórico QA sample",
                    minimal=True,
                )
                profile.to_file(dest / "profile_sample.html")
    except Exception as exc:
        logger.info("ydata-profiling omitido: %s", exc)

    return {
        "inventory": str(inv_path),
        "exclusiones": str(excl_path),
        "summary_html": str(html_path),
        "out_dir": str(dest),
    }


def run_qa_pipeline(conn: Any, *, out_dir: Optional[Path] = None, sample_n: int = 50000) -> Dict[str, Any]:
    inventory = run_inventory(conn)
    bcv = load_bcv_map(conn)
    sample = sample_historico_for_qa(conn, top_n=sample_n)
    # mediana cruda por barra (sample) como ancla heurística débil
    med: Dict[str, float] = {}
    if not sample.empty:
        tmp = sample.copy()
        tmp["precio"] = pd.to_numeric(tmp["precio"], errors="coerce")
        for b, g in tmp.groupby("codigo_barras"):
            m = g["precio"].median()
            if pd.notna(m) and m > 0:
                med[str(b)] = float(m)
    annotated = annotate_qa_frame(sample, bcv, mediana_usd_by_barra=med)
    paths = write_qa_artifacts(inventory, annotated, out_dir=out_dir)
    return {"inventory": inventory, "paths": paths, "annotated_rows": len(annotated)}
