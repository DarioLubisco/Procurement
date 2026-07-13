"""GapExtensionOferta F5 — ADR-0012 (ticket 06)."""
from __future__ import annotations

from analytics_engine.core.gap_extension import (
    MiembroGrupo,
    compute_f_no_oferta,
    compute_gap_extension_oferta,
)
from analytics_engine.core.presets import PresetKnobs
from analytics_engine.core.distribucion_parcial import distribute_parcial
from analytics_engine.core.pedido_baseline import BaselineLine
import pandas as pd


def test_f_uses_non_offer_rotation_denominator_adr_0012():
    # X1 e=4 rot=10; X2 e=1 rot=5; Y on offer
    miembros = [
        MiembroGrupo("X1", 10.0, 4.0, gap=50.0, en_oferta=False),
        MiembroGrupo("X2", 5.0, 1.0, gap=50.0, en_oferta=False),
        MiembroGrupo("Y", 20.0, 2.0, gap=100.0, en_oferta=True),
    ]
    f = compute_f_no_oferta(miembros)
    # (4/5)*(10/15) + (1/5)*(5/15) = 0.8*(2/3) + 0.2*(1/3) = 0.6
    assert abs(f - 0.6) < 1e-9


def test_gap_ext_intermediate_not_full_group_dump():
    miembros = [
        MiembroGrupo("X1", 10.0, 4.0, gap=50.0, en_oferta=False),
        MiembroGrupo("X2", 5.0, 1.0, gap=50.0, en_oferta=False),
        MiembroGrupo("Y", 20.0, 2.0, gap=100.0, en_oferta=True),
    ]
    result = compute_gap_extension_oferta(miembros)
    # Gap_grupo=200, Gap_oferta=100, f=0.6 → Gap_ext=100+(100)*0.6=160
    assert result.gap_grupo == 200.0
    assert result.gap_oferta == 100.0
    assert abs(result.gap_ext - 160.0) < 1e-9
    assert result.gap_ext < result.gap_grupo  # not full dump
    assert result.barras_refuerzo == ("Y",)


def test_f5_reinforces_only_offer_in_distribution():
    """When F5 knobs active and Desvío triggers, only offer BARRA gets extra qty."""
    knobs = PresetKnobs(
        amplifier_enabled=True,
        ext_max_dias_extra=21,
        w1=0.0,
        w2=0.0,
        w3_posicionamiento=1.0,
        w4=0.0,
        w5=0.15,
        lead_time_soft="medium",
    )
    catalog = pd.DataFrame(
        [
            {
                "barra": "X1",
                "descripcion": "X1",
                "rotacion_mensual": 10.0,
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
                "rotacion_mensual": 20.0,
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
                "stock_proveedor": 1000,
                "desvio": 0.0,
            },
            {
                "barra": "Y",
                "proveedor": "PY",
                "precio": 5.0,
                "stock_proveedor": 1000,
                "desvio": -0.20,  # under typical -0.10 threshold
            },
        ]
    )
    criterios = [
        "principio_activo",
        "forma_farmaceutica",
        "concentracion",
        "cantidad_presentacion",
        "contenido_neto",
    ]
    baseline = [
        BaselineLine("X1", "X1", 10),
        BaselineLine("Y", "Y oferta", 20),
    ]
    allocs = distribute_parcial(baseline, catalog, market, knobs, criterios)
    by_b = {a.barra_baseline: a for a in allocs}
    # Non-offer X1 must not receive F5 extras (qty_propuesto <= baseline)
    assert by_b["X1"].qty_propuesto <= by_b["X1"].qty_baseline
    # Offer Y gets reinforcement
    assert by_b["Y"].qty_propuesto > by_b["Y"].qty_baseline
    assert "f5" in by_b["Y"].justificacion_delta.lower() or "f=" in by_b["Y"].justificacion_delta.lower()
