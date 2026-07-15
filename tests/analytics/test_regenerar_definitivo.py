"""Regenerar PedidoDefinitivo + deprecations — tickets 11/12."""
from __future__ import annotations

import pytest

from analytics_engine.core.generar_sencillo_api import (
    run_generar_sencillo,
    run_regenerar_definitivo,
)
from analytics_engine.core.presets import (
    DEAD_OPTIMIZER_KEYS,
    apply_living_overrides,
    living_override_schema,
    resolve_preset_knobs,
    PresetSencillo,
)


def _fixture():
    catalog = [
        {
            "barra": "Y",
            "descripcion": "Y oferta",
            "rotacion_mensual": 30.0,
            "existen": 0.0,
            "es_generico": True,
            "principio_activo": "PA",
            "forma_farmaceutica": "TAB",
            "concentracion": "1",
            "cantidad_presentacion": "1",
            "contenido_neto": "1",
        }
    ]
    offers = [
        {
            "barra": "Y",
            "proveedor": "PY",
            "precio": 5.0,
            "stock_proveedor": 5000,
            "desvio": -0.50,
        }
    ]
    return catalog, offers


def test_regenerar_intermedio_returns_propuesto_and_comparativa():
    catalog, offers = _fixture()
    payload = run_regenerar_definitivo(
        cobertura=30,
        nivel="Intermedio",
        catalog_rows=catalog,
        market_offers_rows=offers,
        overrides={"amp_max_increment_pct": 600.0},
        criterios_agrupacion=[],
    )
    assert payload["meta"]["phase"] == "PedidoDefinitivo"
    assert payload["meta"]["ux_label"] == "Regenerar Definitivo"
    assert payload["meta"]["nivel"] == "Intermedio"
    assert payload["pedido_propuesto"]
    assert payload["comparativa_cantidades"]
    assert "amp_max_increment_pct" in payload["meta"]["overrides_applied"]


def test_regenerar_avanzado_override_changes_qty_vs_sencillo():
    catalog, offers = _fixture()
    sencillo = run_generar_sencillo(
        cobertura=30,
        catalog_rows=catalog,
        market_offers_rows=offers,
        preset="Conservador",
        criterios_agrupacion=[],
    )
    definitivo = run_regenerar_definitivo(
        cobertura=30,
        nivel="Avanzado",
        catalog_rows=catalog,
        market_offers_rows=offers,
        base_preset="Normal",
        overrides={"amp_max_increment_pct": 800.0, "amp_a": 5.84, "amp_b": 1.29},
        criterios_agrupacion=[],
    )
    q_s = sencillo["comparativa_cantidades"][0]["qty_propuesto"]
    q_d = definitivo["comparativa_cantidades"][0]["qty_propuesto"]
    assert q_d > q_s
    assert definitivo["meta"]["phase"] == "PedidoDefinitivo"


def test_dead_s4_overrides_rejected_kappa_living():
    base = resolve_preset_knobs(PresetSencillo.NORMAL)
    for dead in ("s4_enabled", "monto_days_reduction_pct"):
        with pytest.raises(ValueError, match="muerto"):
            apply_living_overrides(base, {dead: 1}, nivel="Avanzado")
    knobs = apply_living_overrides(base, {"sust_kappa": 5.0}, nivel="Avanzado")
    assert knobs.sust_kappa == 5.0


def test_living_schema_excludes_dead_knobs():
    schema = living_override_schema(nivel="Avanzado")
    for dead in DEAD_OPTIMIZER_KEYS:
        assert dead not in schema["living_keys"]
    assert "s4_enabled" in schema["dead_keys_excluded"]
    assert "sust_kappa" in schema["living_keys"]
    assert "sust_kappa" not in schema["dead_keys_excluded"]


def test_living_schema_includes_labeled_fields_for_fe():
    inter = living_override_schema(nivel="Intermedio")
    adv = living_override_schema(nivel="Avanzado")
    assert inter["fields"]
    assert {f["key"] for f in inter["fields"]} == set(inter["living_keys"])
    assert all("label" in f and "type" in f for f in inter["fields"])
    assert len(adv["living_keys"]) >= len(inter["living_keys"])
    assert "amp_a" in adv["living_keys"]
    assert "amp_a" not in inter["living_keys"]


def test_sencillo_meta_marks_forced_includes_and_excel_deprecated():
    catalog, offers = _fixture()
    payload = run_generar_sencillo(
        cobertura=30,
        catalog_rows=catalog,
        market_offers_rows=offers,
        preset="Conservador",
        criterios_agrupacion=[],
    )
    assert payload["meta"]["artifact_primary"] == "comparativa_propuesto"
    assert payload["meta"]["excel_barra_cantidad"] == "secondary_export_only"
    assert payload["meta"]["forced_includes"] == "deprecated_not_required"
    assert payload["meta"]["subtraction_files"] == "contingency_only"
    assert "forced_includes" not in payload
