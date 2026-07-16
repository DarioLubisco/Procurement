"""Detección de outliers por barra (MAD sobre log-precio USD)."""

from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd

from .constants import MAD_Z_THRESHOLD


def _mad(x: np.ndarray) -> float:
    med = float(np.median(x))
    return float(np.median(np.abs(x - med)))


def flag_mad_outliers(
    df: pd.DataFrame,
    *,
    precio_col: str = "precio_usd",
    barra_col: str = "codigo_barras",
    threshold: float = MAD_Z_THRESHOLD,
    min_n: int = 5,
) -> pd.DataFrame:
    """Añade columnas `mad_z` y `es_outlier_mad` (por barra, log-precio).

    Barras con n < min_n no se marcan (mad_z=NaN, es_outlier_mad=False).
    """
    out = df.copy()
    if out.empty or precio_col not in out.columns:
        out["mad_z"] = np.nan
        out["es_outlier_mad"] = False
        return out

    out["mad_z"] = np.nan
    out["es_outlier_mad"] = False
    precios = pd.to_numeric(out[precio_col], errors="coerce")
    valid = precios.notna() & (precios > 0)
    if barra_col not in out.columns:
        return out

    for barra, idx in out.loc[valid].groupby(out.loc[valid, barra_col]).groups.items():
        ix = list(idx)
        vals = precios.loc[ix].to_numpy(dtype=float)
        if len(vals) < min_n:
            continue
        logp = np.log(vals)
        mad = _mad(logp)
        med = float(np.median(logp))
        if mad <= 0:
            continue
        # Consistencia normal: 1.4826 * MAD ≈ σ
        z = np.abs(logp - med) / (1.4826 * mad)
        out.loc[ix, "mad_z"] = z
        out.loc[ix, "es_outlier_mad"] = z > float(threshold)
    return out


def exclusion_rows(
    df: pd.DataFrame,
    *,
    reasons: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Filas a revisar: outlier MAD, BCV missing, moneda heurística dudosa."""
    if df.empty:
        return df
    mask = pd.Series(False, index=df.index)
    if "es_outlier_mad" in df.columns:
        mask = mask | df["es_outlier_mad"].fillna(False)
    if "bcv_missing" in df.columns:
        mask = mask | df["bcv_missing"].fillna(False)
    if "fuente_moneda" in df.columns and (reasons is None or "heuristica" in reasons):
        mask = mask | (df["fuente_moneda"] == "heuristica_magnitud")
    return df.loc[mask].copy()
