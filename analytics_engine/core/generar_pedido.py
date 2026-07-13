"""Unified Generar seam: PedidoBaseline + PedidoPropuesto + ComparativaCantidades."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence

import pandas as pd

from .criterios_agrupacion import resolve_criterios_agrupacion
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
        propuesto, comparativa = _propuesto_conservador(baseline, market_offers)
    else:
        propuesto, comparativa = _identity_stubs(baseline)

    return GenerarResult(
        pedido_baseline=baseline,
        pedido_propuesto=propuesto,
        comparativa_cantidades=comparativa,
    )


def _propuesto_conservador(
    baseline: Sequence[BaselineLine],
    market_offers: pd.DataFrame,
) -> tuple[List[PropuestoLine], List[ComparativaRow]]:
    """Conservador: qty_mult=1, no F5; pick cheapest offer for same BARRA (w3)."""
    knobs = resolve_preset_knobs(PresetSencillo.CONSERVADOR)
    assert knobs.amplifier_enabled is False
    assert knobs.ext_max_dias_extra == 0

    offers = market_offers.copy()
    offers["barra"] = offers["barra"].astype(str)
    offers["precio"] = pd.to_numeric(offers["precio"], errors="coerce")
    offers["stock_proveedor"] = pd.to_numeric(
        offers.get("stock_proveedor", pd.Series([None] * len(offers))),
        errors="coerce",
    )

    propuesto: List[PropuestoLine] = []
    comparativa: List[ComparativaRow] = []
    for line in baseline:
        qty = int(line.cantidad)
        proveedor = ""
        match = offers[offers["barra"] == line.barra]
        if not match.empty:
            # w3 posicionamiento ≈ prefer cheaper offer among same BARRA
            ranked = match.sort_values("precio", ascending=True)
            chosen = ranked.iloc[0]
            proveedor = str(chosen["proveedor"])
            stock = chosen["stock_proveedor"]
            if pd.notna(stock):
                qty = min(qty, int(stock))

        justificacion = ""
        if qty != line.cantidad:
            justificacion = (
                f"delta cantidad {line.cantidad}→{qty} "
                f"(Conservador: stock_proveedor/tope oferta)"
            )

        propuesto.append(
            PropuestoLine(
                barra=line.barra,
                descripcion=line.descripcion,
                proveedor=proveedor,
                cantidad=qty,
            )
        )
        comparativa.append(
            ComparativaRow(
                barra_baseline=line.barra,
                desc_baseline=line.descripcion,
                qty_baseline=line.cantidad,
                barra_propuesto=line.barra,
                desc_propuesto=line.descripcion,
                qty_propuesto=qty,
                justificacion_delta=justificacion,
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
