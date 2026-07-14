"""HTTP Generar Sencillo endpoint — ticket 10 (injected catalog, no live DB)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers.generar_sencillo import router


def test_generar_sencillo_endpoint_returns_comparativa_and_propuesto():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    body = {
        "cobertura": 30,
        "preset": "Conservador",
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
        "presupuesto_maximo": 100000,
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
    resp = client.post("/api/pedidos/generar-sencillo", json=body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["comparativa_cantidades"]
    assert data["pedido_propuesto"][0]["proveedor"] == "BARATO"
    assert data["meta"]["nivel"] == "Sencillo"
    assert data["meta"]["artifact_primary"] == "comparativa_propuesto"
    assert data["meta"]["offers_unique"] == 1
    assert data["meta"]["offers_rows"] == 1
    assert data["meta"]["catalog_rows"] == 1
    assert data["meta"]["backorder_rows"] == 0
    assert data["meta"]["data_source"] == "injected"
    assert "load_ms" in data["meta"]


def test_regenerar_definitivo_endpoint_rejects_dead_knobs():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    body = {
        "cobertura": 30,
        "nivel": "Avanzado",
        "overrides": {"s4_enabled": True},
        "catalog": [
            {
                "barra": "111",
                "descripcion": "X",
                "rotacion_mensual": 10.0,
                "existen": 0.0,
                "principio_activo": "PA",
                "forma_farmaceutica": "TAB",
                "concentracion": "1",
                "cantidad_presentacion": "1",
                "contenido_neto": "1",
            }
        ],
        "market_offers": [
            {"barra": "111", "proveedor": "P", "precio": 1.0, "stock_proveedor": 100}
        ],
    }
    resp = client.post("/api/pedidos/regenerar-definitivo", json=body)
    assert resp.status_code == 400
    assert "muerto" in resp.json()["detail"].lower() or "s4" in resp.json()["detail"].lower()
