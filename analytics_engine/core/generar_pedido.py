"""Unified Generar seam: PedidoBaseline + PedidoPropuesto + ComparativaCantidades."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, Tuple

import pandas as pd

from .backorder import normalize_backorder, subtract_backorder_from_baseline
from .criterios_agrupacion import resolve_criterios_agrupacion
from .distribucion_parcial import distribute_parcial
from .justificacion_factores import JustificacionFactor, factors_to_dicts
from .pedido_baseline import (
    BaselineLine,
    FiltrosOperativos,
    compute_pedido_baseline,
)
from .presets import PresetSencillo, apply_living_overrides, resolve_preset_knobs


class NivelPerfil(str, Enum):
    SENCILLO = "Sencillo"
    INTERMEDIO = "Intermedio"
    AVANZADO = "Avanzado"


@dataclass(frozen=True)
class PerfilPedido:
    cobertura: int
    criterios_agrupacion: Sequence[str]
    filtros_operativos: FiltrosOperativos
    nivel: NivelPerfil
    preset: Optional[PresetSencillo] = None
    presupuesto_maximo: Optional[float] = None
    # Intermedio/Avanzado: living OptimizerConfig overrides (no S4/kappa)
    overrides: Optional[dict] = None


@dataclass(frozen=True)
class PropuestoLine:
    barra: str
    descripcion: str
    proveedor: str
    cantidad: int
    precio: Optional[float] = None  # USD offer; ADR-0018 / Guardar borrador


@dataclass(frozen=True)
class ComparativaRow:
    barra_baseline: str
    desc_baseline: str
    qty_baseline: int
    barra_propuesto: str
    desc_propuesto: str
    qty_propuesto: int
    justificacion_delta: str
    justificacion_factores: Tuple[JustificacionFactor, ...] = ()


@dataclass(frozen=True)
class GenerarResult:
    pedido_baseline: List[BaselineLine]
    pedido_propuesto: List[PropuestoLine]
    comparativa_cantidades: List[ComparativaRow]


def generar_pedido(
    perfil: PerfilPedido,
    *,
    catalog: pd.DataFrame,
    market_offers: Optional[pd.DataFrame] = None,
    backorder: Optional[pd.DataFrame] = None,
) -> GenerarResult:
    """Orchestrate Generar offline via injected catalog/offers/backorder (no live DB/HTTP).

    `backorder` is BARRA×cantidad from dedicated backend tables (ADR-0009). Same
    subtraction applies to Baseline and (via Baseline ceiling) Propuesto.
    """
    criterios = resolve_criterios_agrupacion(perfil.criterios_agrupacion)
    baseline = compute_pedido_baseline(
        catalog,
        cobertura_dias=float(perfil.cobertura),
        filtros=perfil.filtros_operativos,
        criterios_agrupacion=criterios,
    )
    bo_map = normalize_backorder(backorder)
    baseline = subtract_backorder_from_baseline(baseline, bo_map)

    if market_offers is None:
        propuesto, comparativa = _identity_stubs(baseline)
    elif perfil.nivel is NivelPerfil.SENCILLO and perfil.preset is not None:
        propuesto, comparativa = _propuesto_desde_knobs(
            resolve_preset_knobs(perfil.preset),
            baseline,
            catalog,
            market_offers,
            criterios,
        )
    elif perfil.nivel in (NivelPerfil.INTERMEDIO, NivelPerfil.AVANZADO):
        # Definitivo: base = Normal (calibrado) or last Sencillo preset, then living overrides
        base_preset = perfil.preset or PresetSencillo.NORMAL
        knobs = apply_living_overrides(
            resolve_preset_knobs(base_preset),
            perfil.overrides,
            nivel=perfil.nivel.value,
        )
        propuesto, comparativa = _propuesto_desde_knobs(
            knobs, baseline, catalog, market_offers, criterios
        )
    else:
        propuesto, comparativa = _identity_stubs(baseline)

    return GenerarResult(
        pedido_baseline=baseline,
        pedido_propuesto=propuesto,
        comparativa_cantidades=comparativa,
    )


def _propuesto_desde_knobs(
    knobs,
    baseline: Sequence[BaselineLine],
    catalog: pd.DataFrame,
    market_offers: pd.DataFrame,
    criterios: Sequence[str],
) -> tuple[List[PropuestoLine], List[ComparativaRow]]:
    """PedidoPropuesto via DistribucionParcial with resolved knobs."""
    allocations = distribute_parcial(
        baseline, catalog, market_offers, knobs, criterios
    )
    propuesto: List[PropuestoLine] = []
    comparativa: List[ComparativaRow] = []
    for alloc in allocations:
        extra_qty = sum(leg.cantidad for leg in alloc.extra_legs)
        primary_qty = alloc.qty_propuesto - extra_qty
        propuesto.append(
            PropuestoLine(
                barra=alloc.barra_propuesto,
                descripcion=alloc.desc_propuesto,
                proveedor=alloc.proveedor,
                cantidad=primary_qty,
                precio=alloc.precio,
            )
        )
        for leg in alloc.extra_legs:
            propuesto.append(
                PropuestoLine(
                    barra=leg.barra,
                    descripcion=leg.descripcion,
                    proveedor=leg.proveedor,
                    cantidad=leg.cantidad,
                    precio=leg.precio,
                )
            )
        comparativa.append(
            ComparativaRow(
                barra_baseline=alloc.barra_baseline,
                desc_baseline=alloc.desc_baseline,
                qty_baseline=alloc.qty_baseline,
                barra_propuesto=alloc.barra_propuesto,
                desc_propuesto=alloc.desc_propuesto,
                qty_propuesto=alloc.qty_propuesto,
                justificacion_delta=alloc.justificacion_delta,
                justificacion_factores=alloc.justificacion_factores,
            )
        )
    return propuesto, comparativa

def _identity_stubs(
    baseline: Sequence[BaselineLine],
) -> tuple[List[PropuestoLine], List[ComparativaRow]]:
    propuesto: List[PropuestoLine] = []
    comparativa: List[ComparativaRow] = []
    for line in baseline:
        propuesto.append(
            PropuestoLine(
                barra=line.barra,
                descripcion=line.descripcion,
                proveedor="",
                cantidad=line.cantidad,
            )
        )
        comparativa.append(
            ComparativaRow(
                barra_baseline=line.barra,
                desc_baseline=line.descripcion,
                qty_baseline=line.cantidad,
                barra_propuesto=line.barra,
                desc_propuesto=line.descripcion,
                qty_propuesto=line.cantidad,
                justificacion_delta="",
            )
        )
    return propuesto, comparativa
