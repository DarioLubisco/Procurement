"""CriteriosAgrupacion — system default and DemandaGrupal aggregation."""
from __future__ import annotations

from typing import List, Optional, Sequence

import pandas as pd

CRITERIOS_AGRUPACION_DEFAULT: tuple[str, ...] = (
    "principio_activo",
    "forma_farmaceutica",
    "concentracion",
    "cantidad_presentacion",
    "contenido_neto",
)


def resolve_criterios_agrupacion(
    requested: Optional[Sequence[str]],
) -> List[str]:
    """Effective CriteriosAgrupacion for a run.

    None or empty → system default (5 attrs). Non-empty override wins.
    This is the runtime authority for the unified Generar path (not hardcoded Molécula-3).
    """
    if requested:
        return list(requested)
    return list(CRITERIOS_AGRUPACION_DEFAULT)


def compute_demanda_grupal(
    catalog: pd.DataFrame,
    criterios_agrupacion: Sequence[str],
    cobertura_dias: float,
) -> pd.DataFrame:
    """Aggregate rotación/stock by CriteriosAgrupacion and compute Gap.

    Same grouping contract as PedidoBaseline overlay.
    """
    if catalog.empty:
        return pd.DataFrame()

    attrs = list(criterios_agrupacion)
    missing = [a for a in attrs if a not in catalog.columns]
    if missing:
        raise ValueError(f"catalog missing CriteriosAgrupacion columns: {missing}")

    df = catalog.copy()
    df["rotacion_mensual"] = pd.to_numeric(df["rotacion_mensual"], errors="coerce").fillna(0.0)
    df["existen"] = pd.to_numeric(df["existen"], errors="coerce").fillna(0.0)

    grouped = (
        df.groupby(attrs, dropna=False)[["rotacion_mensual", "existen"]]
        .sum()
        .reset_index()
    )
    grouped["gap"] = (
        grouped["rotacion_mensual"] * float(cobertura_dias) / 30.0 - grouped["existen"]
    ).round().astype(int)
    return grouped
