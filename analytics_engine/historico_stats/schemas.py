"""Contratos ligeros (pandera opcional) + invariante dual VES/USD/tasa."""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from .constants import RECONVERSION_DATE

# |usd * tasa - ves| / max(ves, eps) must be <= this (floating noise / rounding)
DUAL_CURRENCY_REL_TOL = 0.02


def validate_weekly_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Valida columnas mínimas del box semanal; lanza ValueError si falla."""
    required = [
        "codigo_barras",
        "anio_iso",
        "semana_iso",
        "precio_mediana",
        "precio_min",
        "media_precio_min",
        "n_obs",
    ]
    if df is None or df.empty:
        return df
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"weekly frame falta columnas: {missing}")
    bad = df[
        (pd.to_numeric(df["precio_mediana"], errors="coerce") <= 0)
        | (pd.to_numeric(df["n_obs"], errors="coerce") < 1)
    ]
    if len(bad):
        raise ValueError(f"weekly frame tiene {len(bad)} filas inválidas (mediana/n_obs)")
    return df


def try_pandera_weekly(df: pd.DataFrame) -> Any:
    """Si pandera está instalado, valida schema; si no, validate_weekly_frame."""
    try:
        import pandera.pandas as pa
        from pandera import Check, Column

        schema = pa.DataFrameSchema(
            {
                "codigo_barras": Column(str),
                "anio_iso": Column(int, Check.ge(2021)),
                "semana_iso": Column(int, Check.in_range(1, 53)),
                "precio_mediana": Column(float, Check.gt(0)),
                "precio_min": Column(float, Check.gt(0)),
                "media_precio_min": Column(float, Check.gt(0)),
                "n_obs": Column(int, Check.ge(1)),
            },
            coerce=True,
        )
        return schema.validate(df, lazy=True)
    except ImportError:
        return validate_weekly_frame(df)


def dual_currency_row_ok(
    *,
    precio_usd: Optional[float],
    precio_ves: Optional[float],
    tasa_bcv: Optional[float],
    rel_tol: float = DUAL_CURRENCY_REL_TOL,
) -> bool:
    """True si ambos lados y tasa existen y cumplen ves ≈ usd * tasa."""
    try:
        u = float(precio_usd) if precio_usd is not None else None
        v = float(precio_ves) if precio_ves is not None else None
        t = float(tasa_bcv) if tasa_bcv is not None else None
    except (TypeError, ValueError):
        return False
    if u is None or v is None or t is None:
        return False
    if u <= 0 or v <= 0 or t <= 0:
        return False
    expected = u * t
    denom = max(abs(v), abs(expected), 1e-9)
    return abs(expected - v) / denom <= float(rel_tol)


def flag_dual_currency_violations(
    df: pd.DataFrame,
    *,
    usd_col: str = "precio_mediana_usd",
    ves_col: str = "precio_mediana_ves",
    tasa_col: str = "tasa_bcv",
    rel_tol: float = DUAL_CURRENCY_REL_TOL,
) -> pd.DataFrame:
    """Añade `dual_currency_ok` y `dual_currency_rel_err`."""
    if df is None or df.empty:
        out = pd.DataFrame() if df is None else df.copy()
        if not out.empty:
            out["dual_currency_ok"] = False
            out["dual_currency_rel_err"] = pd.NA
        return out
    out = df.copy()
    usd = pd.to_numeric(out.get(usd_col), errors="coerce")
    ves = pd.to_numeric(out.get(ves_col), errors="coerce")
    tasa = pd.to_numeric(out.get(tasa_col), errors="coerce")
    expected = usd * tasa
    denom = pd.concat([ves.abs(), expected.abs()], axis=1).max(axis=1).clip(lower=1e-9)
    rel_err = (expected - ves).abs() / denom
    ok = (
        usd.notna()
        & ves.notna()
        & tasa.notna()
        & (usd > 0)
        & (ves > 0)
        & (tasa > 0)
        & (rel_err <= float(rel_tol))
    )
    out["dual_currency_rel_err"] = rel_err
    out["dual_currency_ok"] = ok.fillna(False)
    return out


def validate_daily_dual_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Valida presencia de columnas duales y lanza si hay violaciones graves."""
    if df is None or df.empty:
        return df
    required = [
        "codigo_barras",
        "precio_mediana_usd",
        "precio_mediana_ves",
        "tasa_bcv",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"daily dual frame falta columnas: {missing}")
    flagged = flag_dual_currency_violations(df)
    bad = flagged[~flagged["dual_currency_ok"]]
    if len(bad):
        raise ValueError(
            f"daily dual frame: {len(bad)} filas violan VES≈USD×tasa "
            f"(tol={DUAL_CURRENCY_REL_TOL})"
        )
    return flagged


def try_pandera_daily_dual(df: pd.DataFrame) -> Any:
    """Pandera schema for dual daily rows; falls back to validate_daily_dual_frame."""
    try:
        import pandera.pandas as pa
        from pandera import Check, Column

        schema = pa.DataFrameSchema(
            {
                "codigo_barras": Column(str),
                "precio_mediana_usd": Column(float, Check.gt(0)),
                "precio_mediana_ves": Column(float, Check.gt(0)),
                "precio_min_usd": Column(float, Check.gt(0), nullable=True, required=False),
                "precio_min_ves": Column(float, Check.gt(0), nullable=True, required=False),
                "tasa_bcv": Column(float, Check.gt(0)),
                "moneda_origen": Column(
                    str, Check.isin(["USD", "VES", "MIX"]), nullable=True, required=False
                ),
            },
            coerce=True,
        )
        validated = schema.validate(df, lazy=True)
        return validate_daily_dual_frame(validated)
    except ImportError:
        return validate_daily_dual_frame(df)


def dual_currency_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Counts for QA inventory."""
    if df is None or df.empty:
        return {"n": 0, "ok": 0, "violations": 0, "missing_tasa": 0}
    flagged = flag_dual_currency_violations(df)
    tasa = pd.to_numeric(flagged.get("tasa_bcv"), errors="coerce")
    return {
        "n": int(len(flagged)),
        "ok": int(flagged["dual_currency_ok"].sum()),
        "violations": int((~flagged["dual_currency_ok"]).sum()),
        "missing_tasa": int(tasa.isna().sum() + (tasa <= 0).sum()),
    }
