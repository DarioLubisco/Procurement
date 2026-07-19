"""Purchase-cost USD observations from SAITEMCOM → CUSTOM_LOTES (ADR-0024 hybrid C)."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Iterable, Optional, Sequence

import pandas as pd

from analytics_engine.historico_stats.constants import RECONVERSION_DATE

# SAITEMCOM.NroUnicoL = CUSTOM_LOTES.NroUnico (= SALOTE.NroUnico)
SQL_LOTES_USD_OBS = """
SELECT
    CAST(i.CodItem AS NVARCHAR(50)) AS codigo_barras,
    CAST(c.FechaE AS date) AS fecha,
    CAST(cl.[Precio$ (per unit)] AS FLOAT) AS precio_usd,
    CAST(i.NroUnicoL AS INT) AS nro_unico_l
FROM dbo.SAITEMCOM i
INNER JOIN dbo.SACOMP c ON c.NumeroD = i.NumeroD
INNER JOIN dbo.CUSTOM_LOTES cl ON cl.NroUnico = i.NroUnicoL
WHERE c.FechaE >= ?
  AND i.CodItem IS NOT NULL
  AND i.NroUnicoL IS NOT NULL
  AND i.NroUnicoL <> 0
  AND cl.[Precio$ (per unit)] IS NOT NULL
  AND CAST(cl.[Precio$ (per unit)] AS FLOAT) > 0
"""

_JUNK_EXACT = frozenset({"", "none", "nan", "null", "n/a"})
_JUNK_PREFIX = ("bli_", "amp_")
_BARRA_RE = re.compile(r"^[0-9A-Za-z\-]{8,}$")


def is_clean_barcode(barra: Any) -> bool:
    s = str(barra or "").strip()
    if not s or s.lower() in _JUNK_EXACT:
        return False
    low = s.lower()
    if any(low.startswith(p) for p in _JUNK_PREFIX):
        return False
    return bool(_BARRA_RE.match(s))


def filter_lotes_observations(
    df: pd.DataFrame,
    *,
    since: date = RECONVERSION_DATE,
) -> pd.DataFrame:
    """Keep usable USD purchase rows for weekly aggregate."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["codigo_barras", "fecha", "precio_usd"])
    out = df.copy()
    out["codigo_barras"] = out["codigo_barras"].map(lambda x: str(x).strip() if x is not None else "")
    out["fecha"] = pd.to_datetime(out["fecha"], errors="coerce")
    out["precio_usd"] = pd.to_numeric(out["precio_usd"], errors="coerce")
    out = out[out["codigo_barras"].map(is_clean_barcode)]
    out = out[out["precio_usd"].notna() & (out["precio_usd"] > 0)]
    out = out[out["fecha"].notna()]
    out = out[out["fecha"] >= pd.Timestamp(since)]
    return out.reset_index(drop=True)


def fetch_lotes_usd_observations(
    conn: Any,
    *,
    since: date = RECONVERSION_DATE,
) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute(SQL_LOTES_USD_OBS, [since.isoformat()])
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    raw = pd.DataFrame.from_records(rows, columns=cols)
    return filter_lotes_observations(raw, since=since)
