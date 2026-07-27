"""HTTP generar-batch endpoint — generacion-unica ticket 02."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers.generar_sencillo import router


def _body(perfiles=None):
    return {
        "cobertura": 30,
        "criterios_agrupacion": [
            "principio_activo",
            "forma_farmaceutica",
            "concentracion",
            "cantidad_presentacion",
            "contenido_neto",
        ],
        "include_generics": True,
        "include_brands": True,
        "umbral_rotacion": 0.0,
        "num_rows": 5000,
        "perfiles": perfiles
        or [
            {"id": "c", "label": "Conservador", "preset": "Conservador"},
            {"id": "n", "label": "Normal", "preset": "Normal"},
        ],
        "catalog": [
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
        ],
        "market_offers": [
            {
                "barra": "111",
                "proveedor": "BARATO",
                "precio": 5.0,
                "stock_proveedor": 1000,
            }
        ],
        "backorder": [],
    }


def test_generar_batch_endpoint_returns_baseline_and_perfiles():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    resp = client.post("/api/pedidos/generar-batch", json=_body())
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["pedido_baseline"]
    assert len(data["perfiles"]) == 2
    assert data["perfiles"][0]["result"]["pedido_propuesto"]
    assert data["perfiles"][0]["result"]["comparativa_cantidades"]
    assert data["meta"]["baseline_shared"] is True
    assert data["meta"]["data_source"] == "injected"
    assert data["meta"]["catalog_rows"] == 1


def test_generar_batch_endpoint_rejects_four_perfiles():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    perfiles = [
        {"id": str(i), "label": str(i), "preset": "Normal"} for i in range(4)
    ]
    resp = client.post("/api/pedidos/generar-batch", json=_body(perfiles=perfiles))
    assert resp.status_code == 400
    assert "3" in resp.json()["detail"]


def test_generar_batch_loads_catalog_once():
    """DB/catalog load must not be tripled for a 3-perfil batch."""
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    catalog = _body()["catalog"]
    offers = _body()["market_offers"]
    call_count = {"n": 0}

    def fake_load(**kwargs):
        call_count["n"] += 1
        return catalog, offers, [], 12, "injected"

    with patch(
        "backend.routers.generar_sencillo._load_catalog_offers_backorder",
        side_effect=fake_load,
    ):
        body = _body(
            perfiles=[
                {"id": "c", "label": "C", "preset": "Conservador"},
                {"id": "n", "label": "N", "preset": "Normal"},
                {"id": "a", "label": "A", "preset": "Agresivo"},
            ]
        )
        del body["catalog"]
        del body["market_offers"]
        del body["backorder"]
        resp = client.post("/api/pedidos/generar-batch", json=body)

    assert resp.status_code == 200, resp.text
    assert call_count["n"] == 1
    assert len(resp.json()["perfiles"]) == 3


def test_generar_batch_engine_failure_returns_500_not_half_grid():
    """Coherent failure: no 200 with partial perfiles."""
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    with patch(
        "analytics_engine.core.generar_sencillo_api.run_generar_pedido_batch",
        side_effect=RuntimeError("boom mid-batch"),
    ):
        resp = client.post("/api/pedidos/generar-batch", json=_body())
    assert resp.status_code == 500
    body = resp.json()
    assert "detail" in body
    assert "perfiles" not in body
