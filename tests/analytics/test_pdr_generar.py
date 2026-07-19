"""ADR-0025/0026 PDR in Generar — filter / gate / penalize / stock clamp."""
from __future__ import annotations

import pandas as pd

from analytics_engine.core.distribucion_parcial import distribute_parcial
from analytics_engine.core.pedido_baseline import BaselineLine
from analytics_engine.core.pdr_offers import (
    apply_pdr_gate,
    baja_score_multiplier,
    partition_by_pdr,
    should_clamp_stock,
)
from analytics_engine.core.presets import (
    PresetSencillo,
    apply_living_overrides,
    living_override_schema,
    resolve_preset_knobs,
)

CRIT = [
    "principio_activo",
    "forma_farmaceutica",
    "concentracion",
    "cantidad_presentacion",
    "contenido_neto",
]


def _cat_row(barra: str = "A"):
    return {
        "barra": barra,
        "descripcion": f"Prod {barra}",
        "rotacion_mensual": 10.0,
        "existen": 0.0,
        "es_generico": True,
        "categoria": "X",
        "elasticidad_demanda": 0.0,
        "principio_activo": "PA",
        "forma_farmaceutica": "TAB",
        "concentracion": "1",
        "cantidad_presentacion": "1",
        "contenido_neto": "1",
    }


def test_baja_score_multiplier_floor():
    assert baja_score_multiplier(0.49) == 0.5
    assert baja_score_multiplier(0.7) == 0.7
    assert baja_score_multiplier(None) == 0.5


def test_should_clamp_stock():
    assert should_clamp_stock("ALTA") is True
    assert should_clamp_stock("BAJA") is False
    assert should_clamp_stock(None) is True  # fail-open


def test_partition_excludes_no_confiable():
    df = pd.DataFrame(
        [
            {"barra": "A", "proveedor": "P1", "precio": 1.0, "pdr_semaforo": "ALTA"},
            {"barra": "A", "proveedor": "P2", "precio": 1.1, "pdr_semaforo": "NO_CONFIABLE"},
        ]
    )
    ok, bad = partition_by_pdr(df)
    assert len(ok) == 1 and ok.iloc[0]["proveedor"] == "P1"
    assert len(bad) == 1 and bad.iloc[0]["proveedor"] == "P2"


def test_gate_forces_no_confiable_on_low_stock_low_ppp():
    knobs = resolve_preset_knobs(PresetSencillo.NORMAL)
    assert knobs.pdr_gate_enabled is True
    df = pd.DataFrame(
        [
            {
                "barra": "A",
                "proveedor": "TESTIGO",
                "precio": 1.0,
                "stock_proveedor": 1,
                "ppp": 0.0001,
                "pdr_semaforo": "MODERADA",
            },
            {
                "barra": "A",
                "proveedor": "OK",
                "precio": 1.1,
                "stock_proveedor": 50,
                "ppp": 0.01,
                "pdr_semaforo": "MODERADA",
            },
        ]
    )
    gated = apply_pdr_gate(df, knobs)
    assert gated.iloc[0]["pdr_semaforo"] == "NO_CONFIABLE"
    assert gated.iloc[1]["pdr_semaforo"] == "MODERADA"


def test_gate_disabled_keeps_moderada():
    knobs = apply_living_overrides(
        resolve_preset_knobs(PresetSencillo.NORMAL),
        {"pdr_gate_enabled": False},
        nivel="Avanzado",
    )
    df = pd.DataFrame(
        [
            {
                "barra": "A",
                "proveedor": "TESTIGO",
                "precio": 1.0,
                "stock_proveedor": 1,
                "ppp": 0.0001,
                "pdr_semaforo": "MODERADA",
            }
        ]
    )
    gated = apply_pdr_gate(df, knobs)
    assert gated.iloc[0]["pdr_semaforo"] == "MODERADA"


def test_gate_action_baja_does_not_exclude():
    knobs = apply_living_overrides(
        resolve_preset_knobs(PresetSencillo.NORMAL),
        {"pdr_gate_action": "BAJA"},
        nivel="Avanzado",
    )
    df = pd.DataFrame(
        [
            {
                "barra": "A",
                "proveedor": "TESTIGO",
                "precio": 1.0,
                "stock_proveedor": 1,
                "ppp": 0.0001,
                "pdr_semaforo": "MODERADA",
            }
        ]
    )
    gated = apply_pdr_gate(df, knobs)
    assert gated.iloc[0]["pdr_semaforo"] == "BAJA"
    ok, bad = partition_by_pdr(gated)
    assert len(ok) == 1 and len(bad) == 0


def test_distribute_gate_ejects_testigo_stock1():
    knobs = resolve_preset_knobs(PresetSencillo.NORMAL)
    catalog = pd.DataFrame([_cat_row("A")])
    offers = pd.DataFrame(
        [
            {
                "barra": "A",
                "proveedor": "TESTIGO",
                "precio": 1.0,
                "stock_proveedor": 1,
                "desvio": -0.2,
                "lead_time_dias": 0,
                "pdr": 0.55,
                "pdr_semaforo": "MODERADA",
                "ppp": 0.00001,
                **{c: catalog.iloc[0][c] for c in CRIT},
            },
            {
                "barra": "A",
                "proveedor": "REAL",
                "precio": 1.05,
                "stock_proveedor": 100,
                "desvio": 0.0,
                "lead_time_dias": 0,
                "pdr": 0.9,
                "pdr_semaforo": "ALTA",
                "ppp": 0.01,
                **{c: catalog.iloc[0][c] for c in CRIT},
            },
        ]
    )
    baseline = [BaselineLine(barra="A", descripcion="Prod A", cantidad=5)]
    out = distribute_parcial(baseline, catalog, offers, knobs, CRIT)
    assert out[0].proveedor == "REAL"
    assert out[0].qty_propuesto == 5


def test_baja_does_not_clamp_stock_and_exposes_pdr_factor():
    knobs = resolve_preset_knobs(PresetSencillo.NORMAL)
    # Disable gate so BAJA fixture is not ejected by stock=3+low ppp
    knobs = apply_living_overrides(
        knobs, {"pdr_gate_enabled": False}, nivel="Avanzado"
    )
    catalog = pd.DataFrame([_cat_row("A")])
    offers = pd.DataFrame(
        [
            {
                "barra": "A",
                "proveedor": "CHEAP_BAJA",
                "precio": 1.0,
                "stock_proveedor": 3,
                "desvio": 0.0,
                "lead_time_dias": 0,
                "pdr": 0.49,
                "pdr_semaforo": "BAJA",
                "ppp": 0.01,
                **{c: catalog.iloc[0][c] for c in CRIT},
            },
            {
                "barra": "A",
                "proveedor": "EXP_ALTA",
                "precio": 1.05,
                "stock_proveedor": 100,
                "desvio": 0.0,
                "lead_time_dias": 30,
                "pdr": 0.9,
                "pdr_semaforo": "ALTA",
                "ppp": 0.01,
                **{c: catalog.iloc[0][c] for c in CRIT},
            },
        ]
    )
    baseline = [BaselineLine(barra="A", descripcion="Prod A", cantidad=5)]
    out = distribute_parcial(baseline, catalog, offers, knobs, CRIT)
    assert len(out) == 1
    row = out[0]
    assert row.proveedor == "CHEAP_BAJA"
    assert row.qty_propuesto == 5
    codes = {f.codigo for f in row.justificacion_factores}
    assert "pdr" in codes
    oferta = next(f for f in row.justificacion_factores if f.codigo == "oferta")
    assert oferta.datos.get("pdr_semaforo") == "BAJA"


def test_all_no_confiable_yields_sin_oferta_with_excluidas():
    knobs = resolve_preset_knobs(PresetSencillo.NORMAL)
    catalog = pd.DataFrame([_cat_row("A")])
    offers = pd.DataFrame(
        [
            {
                "barra": "A",
                "proveedor": "P1",
                "precio": 1.0,
                "stock_proveedor": 10,
                "desvio": 0.0,
                "lead_time_dias": 0,
                "pdr": 0.1,
                "pdr_semaforo": "NO_CONFIABLE",
                "ppp": 0.01,
                **{c: catalog.iloc[0][c] for c in CRIT},
            }
        ]
    )
    baseline = [BaselineLine(barra="A", descripcion="Prod A", cantidad=5)]
    out = distribute_parcial(baseline, catalog, offers, knobs, CRIT)
    assert out[0].proveedor == ""
    codes = {f.codigo for f in out[0].justificacion_factores}
    assert "sin_oferta" in codes and "pdr" in codes
    pdr_f = next(f for f in out[0].justificacion_factores if f.codigo == "pdr")
    assert pdr_f.datos.get("n_excluidas") == 1


def test_override_schema_exposes_pdr_gate_avanzado():
    schema = living_override_schema(nivel="Avanzado", base_preset="Normal")
    keys = {f["key"] for f in schema["fields"]}
    assert {
        "pdr_gate_enabled",
        "pdr_gate_stock_max",
        "pdr_gate_umbral_ppp",
        "pdr_gate_action",
    } <= keys
    inter = living_override_schema(nivel="Intermedio", base_preset="Normal")
    ikeys = {f["key"] for f in inter["fields"]}
    assert "pdr_gate_enabled" in ikeys and "pdr_gate_stock_max" in ikeys
    assert "pdr_gate_umbral_ppp" not in ikeys
