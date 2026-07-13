"""Backorder equal subtraction — ADR-0009 (ticket 09)."""
from __future__ import annotations

import pandas as pd

from analytics_engine.core.generar_pedido import (
    NivelPerfil,
    PerfilPedido,
    PresetSencillo,
    generar_pedido,
)
from analytics_engine.core.pedido_baseline import FiltrosOperativos


def _catalog_and_market():
    catalog = pd.DataFrame(
        [
            {
                "barra": "111",
                "descripcion": "Paracetamol 500mg",
                "rotacion_mensual": 100.0,
                "existen": 40.0,
                "es_generico": True,
                "principio_activo": "PARACETAMOL",
                "forma_farmaceutica": "TAB",
                "concentracion": "500",
                "cantidad_presentacion": "20",
                "contenido_neto": "1",
            }
        ]
    )
    market = pd.DataFrame(
        [
            {
                "barra": "111",
                "proveedor": "BARATO",
                "precio": 5.0,
                "stock_proveedor": 1000,
            },
        ]
    )
    return catalog, market


def test_backorder_subtracts_equally_from_baseline_and_propuesto():
    """Same backorder qty leaves Comparativa delta unpolluted by tránsito."""
    catalog, market = _catalog_and_market()
    perfil = PerfilPedido(
        cobertura=30,
        criterios_agrupacion=[],
        filtros_operativos=FiltrosOperativos(),
        nivel=NivelPerfil.SENCILLO,
        preset=PresetSencillo.CONSERVADOR,
    )
    without = generar_pedido(perfil, catalog=catalog, market_offers=market)
    backorder = pd.DataFrame([{"barra": "111", "cantidad": 20}])
    with_bo = generar_pedido(
        perfil, catalog=catalog, market_offers=market, backorder=backorder
    )

    b0 = without.pedido_baseline[0].cantidad
    b1 = with_bo.pedido_baseline[0].cantidad
    assert b1 == b0 - 20

    p0 = without.pedido_propuesto[0].cantidad
    p1 = with_bo.pedido_propuesto[0].cantidad
    assert p1 == p0 - 20

    # Delta Baseline−Propuesto unchanged (no one-sided pollution)
    d0 = without.comparativa_cantidades[0].qty_baseline - without.comparativa_cantidades[0].qty_propuesto
    d1 = with_bo.comparativa_cantidades[0].qty_baseline - with_bo.comparativa_cantidades[0].qty_propuesto
    assert d0 == d1


def test_happy_path_does_not_require_subtraction_files():
    """Generar works with injected backorder tables reader; no Excel upload."""
    catalog, market = _catalog_and_market()
    perfil = PerfilPedido(
        cobertura=30,
        criterios_agrupacion=[],
        filtros_operativos=FiltrosOperativos(),
        nivel=NivelPerfil.SENCILLO,
        preset=PresetSencillo.CONSERVADOR,
    )
    # No subtraction_files kwarg exists — only optional backorder DataFrame
    result = generar_pedido(perfil, catalog=catalog, market_offers=market)
    assert result.pedido_baseline
    assert result.pedido_propuesto
