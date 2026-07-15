"""ADR-0017 kappa / quadratic ceiling in DistribucionParcial."""
from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from analytics_engine.core.distribucion_parcial import distribute_parcial
from analytics_engine.core.pedido_baseline import BaselineLine
from analytics_engine.core.presets import (
    PresetKnobs,
    PresetSencillo,
    apply_living_overrides,
    living_override_schema,
    max_sustitucion_base_from_elasticidad,
    resolve_preset_knobs,
)

CRIT = [
    "principio_activo",
    "forma_farmaceutica",
    "concentracion",
    "cantidad_presentacion",
    "contenido_neto",
]


def _knobs(**over) -> PresetKnobs:
    base = resolve_preset_knobs(PresetSencillo.CONSERVADOR)
    return replace(base, split_lead_time_enabled=False, amplifier_enabled=False, **over)


def _catalog_market():
    catalog = pd.DataFrame(
        [
            {
                "barra": "A1",
                "descripcion": "Baseline A1",
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
                "barra": "S2",
                "descripcion": "Sucedaneo S2",
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
                "barra": "S2",
                "proveedor": "P_S",
                "precio": 5.0,
                "stock_proveedor": 1000,
                "lead_time_dias": 2.0,
                "desvio": -0.2,
                "principio_activo": "PA",
                "forma_farmaceutica": "TAB",
                "concentracion": "1",
                "cantidad_presentacion": "1",
                "contenido_neto": "1",
            }
        ]
    )
    return catalog, market


def test_max_sustitucion_base_map():
    assert max_sustitucion_base_from_elasticidad(0) == 0.0
    assert max_sustitucion_base_from_elasticidad(2) == 0.4
    assert max_sustitucion_base_from_elasticidad(4) == 0.8


def test_kappa_off_allows_full_substitute():
    catalog, market = _catalog_market()
    baseline = [BaselineLine(barra="A1", descripcion="Baseline A1", cantidad=100)]
    out = distribute_parcial(baseline, catalog, market, _knobs(sust_kappa=None), CRIT)
    assert out[0].barra_propuesto == "S2"
    assert out[0].qty_propuesto == 100
    assert out[0].extra_legs == ()


def test_kappa_caps_substitute_and_keeps_baseline_rest():
    catalog, market = _catalog_market()
    baseline = [BaselineLine(barra="A1", descripcion="Baseline A1", cantidad=100)]
    # elast 2 → base 0.4; desvio -0.2 → techo = 0.4 * (1 + 5 * 0.04) = 0.48
    out = distribute_parcial(baseline, catalog, market, _knobs(sust_kappa=5.0), CRIT)
    assert out[0].barra_propuesto == "S2"
    assert out[0].qty_propuesto == 100
    primary = out[0].qty_propuesto - sum(l.cantidad for l in out[0].extra_legs)
    assert primary == 48
    assert out[0].extra_legs[0].barra == "A1"
    assert out[0].extra_legs[0].cantidad == 52
    codes = {f.codigo for f in out[0].justificacion_factores}
    assert "kappa" in codes and "sucedaneo" in codes
    kappa_f = next(f for f in out[0].justificacion_factores if f.codigo == "kappa")
    assert kappa_f.datos.get("kappa") == 5.0


def test_same_barra_ignores_kappa():
    catalog, market = _catalog_market()
    market = market.copy()
    market.loc[0, "barra"] = "A1"
    baseline = [BaselineLine(barra="A1", descripcion="Baseline A1", cantidad=100)]
    out = distribute_parcial(baseline, catalog, market, _knobs(sust_kappa=5.0), CRIT)
    assert out[0].barra_propuesto == "A1"
    assert out[0].qty_propuesto == 100
    assert out[0].extra_legs == ()
    assert "techo κ" not in (out[0].justificacion_delta or "")


def test_override_max_sustitucion_base_forces_zero_sub():
    catalog, market = _catalog_market()
    baseline = [BaselineLine(barra="A1", descripcion="Baseline A1", cantidad=100)]
    out = distribute_parcial(
        baseline, catalog, market, _knobs(sust_kappa=5.0, max_sustitucion_base=0.0), CRIT
    )
    assert out[0].barra_propuesto == "A1"
    assert out[0].qty_propuesto == 100
    codes = {f.codigo for f in out[0].justificacion_factores}
    assert "kappa" in codes
    assert any("0%" in f.detalle for f in out[0].justificacion_factores)


def test_sust_kappa_living_not_dead():
    base = resolve_preset_knobs(PresetSencillo.NORMAL)
    knobs = apply_living_overrides(base, {"sust_kappa": 5.0}, nivel="Intermedio")
    assert knobs.sust_kappa == 5.0
    knobs2 = apply_living_overrides(base, {"kappa": 3.0}, nivel="Avanzado")
    assert knobs2.sust_kappa == 3.0
    with pytest.raises(ValueError, match="muerto"):
        apply_living_overrides(base, {"s4_enabled": True}, nivel="Avanzado")


def test_schema_exposes_sust_kappa_help():
    inter = living_override_schema(nivel="Intermedio")
    adv = living_override_schema(nivel="Avanzado")
    assert "sust_kappa" in inter["living_keys"]
    assert "sust_kappa" not in inter["dead_keys_excluded"]
    assert "s4_enabled" in inter["dead_keys_excluded"]
    field = next(f for f in inter["fields"] if f["key"] == "sust_kappa")
    help_txt = (field.get("help") or field.get("hint") or "").lower()
    assert "sucedáneo" in help_txt or "sucedaneos" in help_txt or "sucedáneos" in help_txt
    assert "max_sustitucion_base" in adv["living_keys"]
    assert "max_sustitucion_base" not in inter["living_keys"]
    assert "no se limita" in (adv.get("note") or "").lower()
