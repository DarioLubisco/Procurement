"""Preset Conservador → Propuesto + Comparativa (ticket 04)."""
from __future__ import annotations

import pandas as pd

from analytics_engine.core.generar_pedido import (
    NivelPerfil,
    PerfilPedido,
    PresetSencillo,
    generar_pedido,
)
from analytics_engine.core.pedido_baseline import FiltrosOperativos
from analytics_engine.core.presets import resolve_preset_knobs


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
                "proveedor": "CARO",
                "precio": 10.0,
                "stock_proveedor": 1000,
            },
            {
                "barra": "111",
                "proveedor": "BARATO",
                "precio": 5.0,
                "stock_proveedor": 1000,
            },
        ]
    )
    return catalog, market


def test_conservador_knobs_match_adr_0010():
    knobs = resolve_preset_knobs(PresetSencillo.CONSERVADOR)
    assert knobs.amplifier_enabled is False
    assert knobs.ext_max_dias_extra == 0
    assert knobs.w3_posicionamiento == 1.0
    assert knobs.w1 == knobs.w2 == knobs.w4 == knobs.w5 == 0.0
    assert knobs.lead_time_soft == "low"


def test_conservador_propuesto_has_proveedor_and_near_zero_delta():
    catalog, market = _catalog_and_market()
    perfil = PerfilPedido(
        cobertura=30,
        criterios_agrupacion=[],
        filtros_operativos=FiltrosOperativos(),
        nivel=NivelPerfil.SENCILLO,
        preset=PresetSencillo.CONSERVADOR,
        presupuesto_maximo=None,
    )
    result = generar_pedido(perfil, catalog=catalog, market_offers=market)

    assert len(result.pedido_propuesto) == 1
    prop = result.pedido_propuesto[0]
    assert prop.proveedor == "BARATO"  # cheapest (w3 posicionamiento / price)
    assert prop.cantidad == 60
    assert prop.barra == "111"

    assert len(result.comparativa_cantidades) == 1
    row = result.comparativa_cantidades[0]
    assert row.qty_baseline == 60
    assert row.qty_propuesto == 60
    assert row.barra_baseline == row.barra_propuesto == "111"
    # near-minimal delta: same qty → no quantity justification required beyond empty/explicit
    assert row.qty_propuesto - row.qty_baseline == 0


def test_conservador_justificacion_when_quantities_would_differ_is_quantity_aware():
    """If Propuesto qty differs, JustificacionDelta mentions cantidad."""
    catalog, market = _catalog_and_market()
    # Force a tiny stock cap so Conservador still picks proveedor but qty capped
    market.loc[market["proveedor"] == "BARATO", "stock_proveedor"] = 10
    market.loc[market["proveedor"] == "CARO", "stock_proveedor"] = 10
    perfil = PerfilPedido(
        cobertura=30,
        criterios_agrupacion=[],
        filtros_operativos=FiltrosOperativos(),
        nivel=NivelPerfil.SENCILLO,
        preset=PresetSencillo.CONSERVADOR,
    )
    result = generar_pedido(perfil, catalog=catalog, market_offers=market)
    row = result.comparativa_cantidades[0]
    assert row.qty_propuesto == 10
    assert row.qty_baseline == 60
    assert "cantidad" in row.justificacion_delta.lower()


def test_presupuesto_maximo_accepted_on_sencillo():
    catalog, market = _catalog_and_market()
    perfil = PerfilPedido(
        cobertura=30,
        criterios_agrupacion=[],
        filtros_operativos=FiltrosOperativos(),
        nivel=NivelPerfil.SENCILLO,
        preset=PresetSencillo.CONSERVADOR,
        presupuesto_maximo=1_000_000.0,
    )
    result = generar_pedido(perfil, catalog=catalog, market_offers=market)
    assert result.pedido_propuesto
    assert perfil.presupuesto_maximo == 1_000_000.0
