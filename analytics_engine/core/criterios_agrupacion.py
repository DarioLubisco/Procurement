"""CriteriosAgrupacion — system default, whitelist, and DemandaGrupal aggregation."""
from __future__ import annotations

from typing import List, Optional, Sequence

import pandas as pd

# Product default (ADR-0008) — checked in FE on load.
# Presentación (unidades en empaque), NOT contenido_neto (ml/g).
CRITERIOS_AGRUPACION_DEFAULT: tuple[str, ...] = (
    "principio_activo",
    "forma_farmaceutica",
    "concentracion",
    "cantidad_presentacion",
)

# Whitelist aligned with Procurement.RotacionGrupal_Atributos / ATRIBUTOS_VALIDOS.
ATRIBUTOS_VALIDOS: frozenset[str] = frozenset(
    {
        "principio_activo",
        "concentracion",
        "forma_farmaceutica",
        "cantidad_presentacion",
        "origen",
        "fabricante",
        "contenido_neto",
        "generico",
        "marca",
    }
)

# Stable order for catalog columns / FE fallback (es_base first, then id order).
ATRIBUTOS_VALIDOS_ORDER: tuple[str, ...] = (
    "principio_activo",
    "concentracion",
    "forma_farmaceutica",
    "cantidad_presentacion",
    "origen",
    "fabricante",
    "contenido_neto",
    "generico",
    "marca",
    
)


class CriteriosAgrupacionInvalid(ValueError):
    """Request criterios not ⊆ ATRIBUTOS_VALIDOS or empty after clean."""


def resolve_criterios_agrupacion(
    requested: Optional[Sequence[str]],
) -> List[str]:
    """Effective CriteriosAgrupacion for a run.

    None or empty → system default (5 attrs). Non-empty override must be
    non-empty after clean and ⊆ ATRIBUTOS_VALIDOS (grill layout 2026-07-15).
    """
    if not requested:
        return list(CRITERIOS_AGRUPACION_DEFAULT)
    cleaned: List[str] = []
    seen: set[str] = set()
    for raw in requested:
        a = str(raw or "").strip()
        if not a or a in seen:
            continue
        seen.add(a)
        cleaned.append(a)
    if not cleaned:
        return list(CRITERIOS_AGRUPACION_DEFAULT)
    invalid = sorted(a for a in cleaned if a not in ATRIBUTOS_VALIDOS)
    if invalid:
        raise CriteriosAgrupacionInvalid(
            f"CriteriosAgrupacion no válidos: {', '.join(invalid)}. "
            f"Válidos: {', '.join(ATRIBUTOS_VALIDOS_ORDER)}"
        )
    return cleaned


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
