"""Agregación semanal ISO: p25 / mediana / p75 / min / media_precio_min / n_obs."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd


def _iso_parts(ts: pd.Timestamp) -> tuple[int, int]:
    iso = ts.isocalendar()
    # pandas may return named tuple with .year/.week
    return int(iso.year), int(iso.week)


def aggregate_weekly_box(
    observations: pd.DataFrame,
    *,
    precio_col: str = "precio_usd",
    barra_col: str = "codigo_barras",
    fecha_col: str = "fecha",
    daily_min_col: Optional[str] = "precio_min_diario",
) -> pd.DataFrame:
    """Una fila por (barra, anio_iso, semana_iso).

    - precio_min: MIN de observaciones de la semana
    - media_precio_min: AVG de mínimos diarios si `daily_min_col` presente;
      si no, = precio_min (una sola obs agregada)
    """
    if observations is None or observations.empty:
        return pd.DataFrame(
            columns=[
                "codigo_barras",
                "anio_iso",
                "semana_iso",
                "precio_p25",
                "precio_mediana",
                "precio_p75",
                "precio_min",
                "media_precio_min",
                "n_obs",
                "fecha_semana_ini",
                "fecha_semana_fin",
            ]
        )

    df = observations.copy()
    df[fecha_col] = pd.to_datetime(df[fecha_col], errors="coerce")
    df[precio_col] = pd.to_numeric(df[precio_col], errors="coerce")
    df = df.dropna(subset=[fecha_col, precio_col, barra_col])
    df = df[df[precio_col] > 0]
    if df.empty:
        return aggregate_weekly_box(pd.DataFrame())

    parts = df[fecha_col].map(_iso_parts)
    df["anio_iso"] = [p[0] for p in parts]
    df["semana_iso"] = [p[1] for p in parts]

    rows: List[Dict[str, Any]] = []
    for (barra, anio, sem), g in df.groupby([barra_col, "anio_iso", "semana_iso"], sort=True):
        precios = g[precio_col].to_numpy(dtype=float)
        n = int(len(precios))
        pmin = float(np.min(precios))
        if daily_min_col and daily_min_col in g.columns:
            dm = pd.to_numeric(g[daily_min_col], errors="coerce").dropna()
            dm = dm[dm > 0]
            media_min = float(dm.mean()) if len(dm) else pmin
        else:
            # Sin mínimos diarios: media_precio_min = min de la semana
            media_min = pmin
        fechas = g[fecha_col]
        rows.append(
            {
                "codigo_barras": str(barra),
                "anio_iso": int(anio),
                "semana_iso": int(sem),
                "precio_p25": float(np.percentile(precios, 25)),
                "precio_mediana": float(np.median(precios)),
                "precio_p75": float(np.percentile(precios, 75)),
                "precio_min": pmin,
                "media_precio_min": media_min,
                "n_obs": n,
                "fecha_semana_ini": fechas.min().date().isoformat(),
                "fecha_semana_fin": fechas.max().date().isoformat(),
            }
        )
    return pd.DataFrame(rows)


def weekly_rows_to_dicts(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    return df.to_dict(orient="records")
