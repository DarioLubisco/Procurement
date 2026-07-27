"""run_generar_pedido_batch adapter — generacion-unica ticket 02."""
from __future__ import annotations

import pytest

from analytics_engine.core.generar_sencillo_api import run_generar_pedido_batch


def _offer_fixture():
    catalog = [
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
    market = [
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
    return catalog, market


def test_run_batch_returns_shared_baseline_and_perfil_slots():
    catalog, market = _offer_fixture()
    payload = run_generar_pedido_batch(
        cobertura=30,
        catalog_rows=catalog,
        market_offers_rows=market,
        perfiles=[
            {"id": "c", "label": "Conservador", "preset": "Conservador"},
            {"id": "n", "label": "Normal", "preset": "Normal"},
            {"id": "a", "label": "Agresivo", "preset": "Agresivo"},
        ],
        backorder_rows=[],
    )
    assert payload["pedido_baseline"]
    assert len(payload["perfiles"]) == 3
    base_barras = [b["barra"] for b in payload["pedido_baseline"]]
    base_qtys = [b["cantidad"] for b in payload["pedido_baseline"]]
    for slot in payload["perfiles"]:
        assert slot["id"]
        assert slot["label"]
        assert isinstance(slot.get("knobs_efectivos"), dict)
        result = slot["result"]
        assert [r["barra_baseline"] for r in result["comparativa_cantidades"]] == base_barras
        assert [r["qty_baseline"] for r in result["comparativa_cantidades"]] == base_qtys
        assert result["pedido_propuesto"]
    assert payload["meta"]["baseline_shared"] is True
    assert payload["meta"]["n_perfiles"] == 3


def test_run_batch_rejects_more_than_three():
    catalog, market = _offer_fixture()
    with pytest.raises(ValueError, match="3"):
        run_generar_pedido_batch(
            cobertura=30,
            catalog_rows=catalog,
            market_offers_rows=market,
            perfiles=[
                {"id": str(i), "label": str(i), "preset": "Normal"} for i in range(4)
            ],
        )


def test_run_batch_rejects_empty_perfiles():
    catalog, market = _offer_fixture()
    with pytest.raises(ValueError, match="1"):
        run_generar_pedido_batch(
            cobertura=30,
            catalog_rows=catalog,
            market_offers_rows=market,
            perfiles=[],
        )


def test_run_batch_invalid_preset_raises():
    catalog, market = _offer_fixture()
    with pytest.raises(ValueError, match="preset"):
        run_generar_pedido_batch(
            cobertura=30,
            catalog_rows=catalog,
            market_offers_rows=market,
            perfiles=[{"id": "x", "label": "X", "preset": "NoExiste"}],
        )
