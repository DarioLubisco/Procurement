"""Presets Normal y Agresivo — ADR-0011/0013 (ticket 08)."""
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


def test_normal_knobs_match_adr_0011():
    knobs = resolve_preset_knobs(PresetSencillo.NORMAL)
    assert knobs.amplifier_enabled is True
    assert knobs.amp_a == 5.84
    assert knobs.amp_b == 1.29
    assert knobs.amp_max_increment_pct == 500.0
    assert knobs.amp_floor_pct == 0.2
    assert knobs.ext_max_dias_extra == 21
    assert knobs.f5_umbral == -0.10
    assert knobs.w1 == 0.15
    assert knobs.w2 == 0.25
    assert knobs.w3_posicionamiento == 0.25
    assert knobs.w4 == 0.20
    assert knobs.w5 == 0.15
    assert knobs.lead_time_soft == "medium"
    assert knobs.opp_lambda == 1.0


def test_agresivo_knobs_match_adr_0013():
    knobs = resolve_preset_knobs(PresetSencillo.AGRESIVO)
    assert knobs.amplifier_enabled is True
    assert knobs.amp_max_increment_pct == 800.0
    assert knobs.amp_floor_pct == 0.15
    assert knobs.ext_max_dias_extra == 45
    assert knobs.f5_umbral == -0.05
    assert knobs.w1 == 0.05
    assert knobs.w2 == 0.20
    assert knobs.w3_posicionamiento == 0.15
    assert knobs.w4 == 0.35
    assert knobs.w5 == 0.25
    assert knobs.lead_time_soft == "high"
    assert knobs.opp_lambda == 1.5
    assert knobs.split_lead_time_enabled is True


def _offer_fixture():
    """Catalog+market where amp/F5 distinguish presets (offer desvío on Y).

    Same LT on both offers so SplitLeadTime does not mask amp differences.
    """
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


def _run(preset: PresetSencillo):
    catalog, market = _offer_fixture()
    perfil = PerfilPedido(
        cobertura=30,
        criterios_agrupacion=[],
        filtros_operativos=FiltrosOperativos(),
        nivel=NivelPerfil.SENCILLO,
        preset=preset,
    )
    return generar_pedido(perfil, catalog=catalog, market_offers=market)


def test_baseline_unchanged_when_only_preset_changes():
    c = _run(PresetSencillo.CONSERVADOR)
    n = _run(PresetSencillo.NORMAL)
    a = _run(PresetSencillo.AGRESIVO)
    assert [b.cantidad for b in c.pedido_baseline] == [
        b.cantidad for b in n.pedido_baseline
    ]
    assert [b.cantidad for b in c.pedido_baseline] == [
        b.cantidad for b in a.pedido_baseline
    ]
    assert [b.barra for b in c.pedido_baseline] == [b.barra for b in a.pedido_baseline]


def test_three_presets_yield_materially_different_propuesto():
    c = _run(PresetSencillo.CONSERVADOR)
    n = _run(PresetSencillo.NORMAL)
    a = _run(PresetSencillo.AGRESIVO)

    def qty_by_barra(result):
        return {r.barra_baseline: r.qty_propuesto for r in result.comparativa_cantidades}

    qc, qn, qa = qty_by_barra(c), qty_by_barra(n), qty_by_barra(a)
    # Conservador: no amp/F5 → offer Y stays at baseline ceiling
    # Normal: amp (+F5) pushes Y above Conservador
    # Agresivo: stronger amp cap / F5 → at least as aggressive as Normal, typically more
    assert qn["Y"] > qc["Y"]
    assert qa["Y"] > qn["Y"]
    assert not (qc["Y"] == qn["Y"] == qa["Y"])
