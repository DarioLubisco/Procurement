"""Unified Generar seam: PedidoBaseline + PedidoPropuesto + ComparativaCantidades."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence

import pandas as pd

from .criterios_agrupacion import resolve_criterios_agrupacion
from .distribucion_parcial import distribute_parcial
from .pedido_baseline import (
    BaselineLine,
    FiltrosOperativos,
    compute_pedido_baseline,
)
from .presets import PresetSencillo, resolve_preset_knobs


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


@dataclass(frozen=True)
class PropuestoLine:
    barra: str
    descripcion: str
    proveedor: str
    cantidad: int


@dataclass(frozen=True)
class ComparativaRow:
    barra_baseline: str
    desc_baseline: str
    qty_baseline: int
    barra_propuesto: str
    desc_propuesto: str
    qty_propuesto: int
    justificacion_delta: str


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
) -> GenerarResult:
    """Orchestrate Generar offline via injected catalog/offers (no live DB/HTTP)."""
    criterios = resolve_criterios_agrupacion(perfil.criterios_agrupacion)
    baseline = compute_pedido_baseline(
        catalog,
        cobertura_dias=float(perfil.cobertura),
        filtros=perfil.filtros_operativos,
        criterios_agrupacion=criterios,
    )

    if (
        perfil.nivel is NivelPerfil.SENCILLO
        and perfil.preset is PresetSencillo.CONSERVADOR
        and market_offers is not None
    ):
        propuesto, comparativa = _propuesto_conservador(
            baseline, catalog, market_offers, criterios
        )
    else:
        propuesto, comparativa = _identity_stubs(baseline)

    return GenerarResult(
        pedido_baseline=baseline,
        pedido_propuesto=propuesto,
        comparativa_cantidades=comparativa,
    )


def _propuesto_conservador(
    baseline: Sequence[BaselineLine],
    catalog: pd.DataFrame,
    market_offers: pd.DataFrame,
    criterios: Sequence[str],
) -> tuple[List[PropuestoLine], List[ComparativaRow]]:
    """Conservador via DistribucionParcial: qty ceiling = Baseline line; multi-factor pick."""
    knobs = resolve_preset_knobs(PresetSencillo.CONSERVADOR)
    assert knobs.amplifier_enabled is False
    assert knobs.ext_max_dias_extra == 0

    allocations = distribute_parcial(
        baseline, catalog, market_offers, knobs, criterios
    )
    propuesto: List[PropuestoLine] = []
    comparativa: List[ComparativaRow] = []
    for alloc in allocations:
        propuesto.append(
            PropuestoLine(
                barra=alloc.barra_propuesto,
                descripcion=alloc.desc_propuesto,
                proveedor=alloc.proveedor,
                cantidad=alloc.qty_propuesto,
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
