"""ADR-0022 rivales / hermanos top-N."""
from __future__ import annotations

import pandas as pd

from dataclasses import replace

from analytics_engine.core.competencia_top_n import (
    clamp_top_n,
    competencia_payload,
    hermanos_reemplazables_top_n,
    rivales_top_n,
)
from analytics_engine.core.distribucion_parcial import distribute_parcial
from analytics_engine.core.pedido_baseline import BaselineLine
from analytics_engine.core.presets import PresetSencillo, resolve_preset_knobs


CRIT = [
    "principio_activo",
    "forma_farmaceutica",
    "concentracion",
    "cantidad_presentacion",
    "contenido_neto",
]


def test_clamp_top_n():
    assert clamp_top_n(3) == 3
    assert clamp_top_n(0) == 1
    assert clamp_top_n(99) == 10
    assert clamp_top_n("x") == 3


def test_rivales_and_hermanos_helpers():
    scored = pd.DataFrame(
        [
            {"barra": "A1", "proveedor": "P1", "precio": 1.0, "_score": 2.0, "desvio": -0.1},
            {"barra": "A1", "proveedor": "P2", "precio": 1.2, "_score": 1.5, "desvio": 0.0},
            {"barra": "B2", "proveedor": "P3", "precio": 0.9, "_score": 1.8, "desvio": -0.2},
            {"barra": "C3", "proveedor": "P4", "precio": 1.1, "_score": 1.0, "desvio": 0.0},
        ]
    )
    riv = rivales_top_n(scored, top_n=2, elegida_barra="A1", elegida_proveedor="P1")
    assert len(riv) == 2
    assert riv[0]["proveedor"] == "P1" and riv[0]["elegida"] is True
    assert riv[1]["barra"] == "B2"

    herm = hermanos_reemplazables_top_n(scored, baseline_barra="A1", top_n=2)
    assert [h["barra"] for h in herm] == ["B2", "C3"]

    payload = competencia_payload(
        scored,
        baseline_barra="A1",
        elegida_barra="A1",
        elegida_proveedor="P1",
        rivales_n=3,
        hermanos_n=1,
    )
    assert len(payload["rivales"]) == 3
    assert len(payload["hermanos_reemplazables"]) == 1


def test_distribute_embeds_rivales_in_oferta_factor():
    catalog = pd.DataFrame(
        [
            {
                "barra": "A1",
                "descripcion": "Base",
                "rotacion_mensual": 30.0,
                "existen": 0.0,
                "elasticidad_demanda": 2.0,
                "principio_activo": "PA",
                "forma_farmaceutica": "TAB",
                "concentracion": "1",
                "cantidad_presentacion": "1",
                "contenido_neto": "1",
            },
            {
                "barra": "B2",
                "descripcion": "Hermano",
                "rotacion_mensual": 10.0,
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
                "barra": "A1",
                "proveedor": "CHEAP",
                "precio": 1.0,
                "stock_proveedor": 100,
                "lead_time_dias": 5.0,
                "desvio": -0.1,
                "principio_activo": "PA",
                "forma_farmaceutica": "TAB",
                "concentracion": "1",
                "cantidad_presentacion": "1",
                "contenido_neto": "1",
            },
            {
                "barra": "A1",
                "proveedor": "OTHER",
                "precio": 1.5,
                "stock_proveedor": 100,
                "lead_time_dias": 2.0,
                "desvio": 0.0,
                "principio_activo": "PA",
                "forma_farmaceutica": "TAB",
                "concentracion": "1",
                "cantidad_presentacion": "1",
                "contenido_neto": "1",
            },
            {
                "barra": "B2",
                "proveedor": "SIB",
                "precio": 1.1,
                "stock_proveedor": 100,
                "lead_time_dias": 3.0,
                "desvio": -0.05,
                "principio_activo": "PA",
                "forma_farmaceutica": "TAB",
                "concentracion": "1",
                "cantidad_presentacion": "1",
                "contenido_neto": "1",
            },
        ]
    )
    knobs = resolve_preset_knobs(PresetSencillo.NORMAL)
    knobs = replace(
        knobs,
        rivales_top_n=3,
        hermanos_top_n=2,
        amplifier_enabled=False,
        split_lead_time_enabled=False,
        ext_max_dias_extra=0,
    )
    out = distribute_parcial(
        [BaselineLine(barra="A1", descripcion="Base", cantidad=10)],
        catalog,
        market,
        knobs,
        CRIT,
    )
    oferta = next(f for f in out[0].justificacion_factores if f.codigo == "oferta")
    assert oferta.datos.get("rivales")
    assert len(oferta.datos["rivales"]) >= 2
    assert any(r.get("elegida") for r in oferta.datos["rivales"])
    assert oferta.datos.get("hermanos_reemplazables")
    assert oferta.datos["hermanos_reemplazables"][0]["barra"] == "B2"
