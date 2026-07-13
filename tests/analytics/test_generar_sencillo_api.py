"""API Generar Sencillo — ticket 10."""
from __future__ import annotations

from analytics_engine.core.criterios_agrupacion import CRITERIOS_AGRUPACION_DEFAULT
from analytics_engine.core.generar_sencillo_api import run_generar_sencillo


def _fixture_catalog_and_offers():
    catalog = [
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
    offers = [
        {
            "barra": "111",
            "proveedor": "BARATO",
            "precio": 5.0,
            "stock_proveedor": 1000,
        },
        {
            "barra": "111",
            "proveedor": "CARO",
            "precio": 10.0,
            "stock_proveedor": 1000,
        },
    ]
    return catalog, offers


def test_run_generar_sencillo_returns_comparativa_and_propuesto_with_proveedor():
    catalog, offers = _fixture_catalog_and_offers()
    payload = run_generar_sencillo(
        cobertura=30,
        catalog_rows=catalog,
        market_offers_rows=offers,
        preset="Conservador",
        criterios_agrupacion=[],
    )
    assert payload["pedido_baseline"]
    assert payload["pedido_propuesto"]
    assert payload["comparativa_cantidades"]
    prop = payload["pedido_propuesto"][0]
    assert prop["proveedor"] == "BARATO"
    assert "barra" in prop and "cantidad" in prop
    row = payload["comparativa_cantidades"][0]
    for key in (
        "barra_baseline",
        "desc_baseline",
        "qty_baseline",
        "barra_propuesto",
        "desc_propuesto",
        "qty_propuesto",
        "justificacion_delta",
    ):
        assert key in row
    assert payload["meta"]["artifact_primary"] == "comparativa_propuesto"
    assert payload["meta"]["nivel"] == "Sencillo"


def test_criterios_agrupacion_sent_on_request_are_effective():
    catalog, offers = _fixture_catalog_and_offers()
    custom = ["principio_activo", "forma_farmaceutica"]
    payload = run_generar_sencillo(
        cobertura=30,
        catalog_rows=catalog,
        market_offers_rows=offers,
        preset="Normal",
        criterios_agrupacion=custom,
        presupuesto_maximo=50_000.0,
    )
    assert payload["meta"]["criterios_agrupacion_efectivos"] == custom
    assert payload["meta"]["preset"] == "Normal"


def test_default_criterios_when_empty_list():
    catalog, offers = _fixture_catalog_and_offers()
    payload = run_generar_sencillo(
        cobertura=30,
        catalog_rows=catalog,
        market_offers_rows=offers,
        criterios_agrupacion=[],
    )
    assert payload["meta"]["criterios_agrupacion_efectivos"] == list(
        CRITERIOS_AGRUPACION_DEFAULT
    )
