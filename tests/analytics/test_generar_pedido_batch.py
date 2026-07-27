"""generar_pedido_batch — Baseline once + ≤3 perfiles (generacion-unica ticket 01)."""
from __future__ import annotations

import pandas as pd
import pytest

from analytics_engine.core.generar_pedido import (
    NivelPerfil,
    PerfilDescriptor,
    PerfilPedido,
    FiltrosCompartidos,
    generar_pedido,
    generar_pedido_batch,
)
from analytics_engine.core.pedido_baseline import FiltrosOperativos
from analytics_engine.core.presets import PresetSencillo


def _offer_fixture():
    """Same fixture family as test_presets_normal_agresivo — presets diverge on Y."""
    catalog = pd.DataFrame(
        [
            {
                "barra": "X1",
                "descripcion": "X1",
                "rotacion_mensual": 30.0,
                "existen": 0.0,
                "elasticidad_demanda": 4.0,
                "principio_activo": "PA",
                "forma_farmaceutica": "TAB",
                "concentracion": "1",
                "cantidad_presentacion": "1",
                "contenido_neto": "1",
            },
            {
                "barra": "Y",
                "descripcion": "Y oferta",
                "rotacion_mensual": 30.0,
                "existen": 0.0,
                "elasticidad_demanda": 2.0,
                "principio_activo": "PA",
                "forma_farmaceutica": "TAB",
                "concentracion": "1",
                "cantidad_presentacion": "1",
                "contenido_neto": "1",
            },
        ]
    )
    market = pd.DataFrame(
        [
            {
                "barra": "X1",
                "proveedor": "PX",
                "precio": 10.0,
                "stock_proveedor": 5000,
                "desvio": 0.0,
                "lead_time_dias": 5.0,
            },
            {
                "barra": "Y",
                "proveedor": "PY",
                "precio": 5.0,
                "stock_proveedor": 5000,
                "desvio": -0.50,
                "lead_time_dias": 5.0,
            },
        ]
    )
    return catalog, market


def _shared() -> FiltrosCompartidos:
    return FiltrosCompartidos(
        cobertura=30,
        criterios_agrupacion=[],
        filtros_operativos=FiltrosOperativos(),
    )


def test_batch_shares_identical_baseline_across_perfiles():
    catalog, market = _offer_fixture()
    batch = generar_pedido_batch(
        _shared(),
        [
            PerfilDescriptor(id="c", label="Conservador", preset=PresetSencillo.CONSERVADOR),
            PerfilDescriptor(id="n", label="Normal", preset=PresetSencillo.NORMAL),
            PerfilDescriptor(id="a", label="Agresivo", preset=PresetSencillo.AGRESIVO),
        ],
        catalog=catalog,
        market_offers=market,
    )

    assert len(batch.perfiles) == 3
    base_barras = [b.barra for b in batch.pedido_baseline]
    base_qtys = [b.cantidad for b in batch.pedido_baseline]
    for slot in batch.perfiles:
        assert [r.barra_baseline for r in slot.result.comparativa_cantidades] == base_barras
        assert [r.qty_baseline for r in slot.result.comparativa_cantidades] == base_qtys
        assert [b.barra for b in slot.result.pedido_baseline] == base_barras
        assert [b.cantidad for b in slot.result.pedido_baseline] == base_qtys


def test_batch_perfiles_yield_distinct_propuesto_totals():
    catalog, market = _offer_fixture()
    batch = generar_pedido_batch(
        _shared(),
        [
            PerfilDescriptor(id="c", label="Conservador", preset=PresetSencillo.CONSERVADOR),
            PerfilDescriptor(id="n", label="Normal", preset=PresetSencillo.NORMAL),
            PerfilDescriptor(id="a", label="Agresivo", preset=PresetSencillo.AGRESIVO),
        ],
        catalog=catalog,
        market_offers=market,
    )

    def qty_y(slot):
        return next(
            r.qty_propuesto
            for r in slot.result.comparativa_cantidades
            if r.barra_baseline == "Y"
        )

    by_id = {s.id: s for s in batch.perfiles}
    assert qty_y(by_id["n"]) > qty_y(by_id["c"])
    assert qty_y(by_id["a"]) > qty_y(by_id["n"])


def test_batch_rejects_more_than_three_perfiles():
    catalog, market = _offer_fixture()
    slots = [
        PerfilDescriptor(id=str(i), label=str(i), preset=PresetSencillo.NORMAL)
        for i in range(4)
    ]
    with pytest.raises(ValueError, match="3"):
        generar_pedido_batch(
            _shared(), slots, catalog=catalog, market_offers=market
        )


def test_batch_slot_matches_single_generar_pedido_shape():
    catalog, market = _offer_fixture()
    shared = _shared()
    batch = generar_pedido_batch(
        shared,
        [PerfilDescriptor(id="n", label="Normal", preset=PresetSencillo.NORMAL)],
        catalog=catalog,
        market_offers=market,
    )
    single = generar_pedido(
        PerfilPedido(
            cobertura=shared.cobertura,
            criterios_agrupacion=shared.criterios_agrupacion,
            filtros_operativos=shared.filtros_operativos,
            nivel=NivelPerfil.SENCILLO,
            preset=PresetSencillo.NORMAL,
        ),
        catalog=catalog,
        market_offers=market,
    )
    slot = batch.perfiles[0].result
    assert [p.barra for p in slot.pedido_propuesto] == [
        p.barra for p in single.pedido_propuesto
    ]
    assert [p.cantidad for p in slot.pedido_propuesto] == [
        p.cantidad for p in single.pedido_propuesto
    ]
    assert [r.qty_propuesto for r in slot.comparativa_cantidades] == [
        r.qty_propuesto for r in single.comparativa_cantidades
    ]
