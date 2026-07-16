"""Contratos ligeros (pandera opcional)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .constants import RECONVERSION_DATE


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
