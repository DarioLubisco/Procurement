"""HTTP ValidarMinimos — ADR-0016 (injected fixtures, no live DB)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers.validar_minimos import router


def _body(**over):
    base = {
        "action": "evaluar",
        "cobertura": 30,
        "criterios_agrupacion": [
            "principio_activo",
            "forma_farmaceutica",
            "concentracion",
            "cantidad_presentacion",
            "contenido_neto",
        ],
        "pedido_propuesto": [
            {
                "barra": "A",
                "descripcion": "Prod A",
                "proveedor": "CHEAP",
                "cantidad": 10,
            }
        ],
        "comparativa_cantidades": [
            {
                "barra_baseline": "A",
                "desc_baseline": "Prod A",
                "qty_baseline": 10,
                "barra_propuesto": "A",
                "desc_propuesto": "Prod A",
                "qty_propuesto": 10,
                "justificacion_delta": "",
            }
        ],
        "catalog": [
            {
                "barra": "A",
                "descripcion": "Prod A",
                "rotacion_mensual": 30.0,
                "existen": 0.0,
                "principio_activo": "PA",
                "forma_farmaceutica": "TAB",
                "concentracion": "1",
                "cantidad_presentacion": "1",
                "contenido_neto": "1",
            }
        ],
        "market_offers": [
            {"barra": "A", "proveedor": "CHEAP", "precio": 1.0, "stock_proveedor": 100},
            {
                "barra": "A",
                "proveedor": "EXPENSIVE",
                "precio": 2.0,
                "stock_proveedor": 100,
            },
        ],
        "minimos_usd": {"CHEAP": 50.0},
    }
    base.update(over)
    return base


def test_evaluar_returns_cola():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    resp = client.post("/api/pedidos/validar-minimos", json=_body())
    assert resp.status_code == 200, resp.text
    meta = resp.json()["meta"]["validar_minimos"]
    assert meta["cola"][0]["proveedor"] == "CHEAP"
    assert meta["cola"][0]["deficit_usd"] == 40.0


def test_recalcular_boosts_qty():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    resp = client.post(
        "/api/pedidos/validar-minimos",
        json=_body(action="recalcular", proveedor="CHEAP", pct_extra=50),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["pedido_propuesto"][0]["cantidad"] == 45
    assert data["meta"]["validar_minimos"]["intentos_recalc"]["CHEAP"] == 1


def test_second_recalc_requires_panel_ack():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    resp = client.post(
        "/api/pedidos/validar-minimos",
        json=_body(
            action="recalcular",
            proveedor="CHEAP",
            pct_extra=50,
            intentos_recalc={"CHEAP": 1},
            panel_ack=False,
        ),
    )
    assert resp.status_code == 200
    meta = resp.json()["meta"]["validar_minimos"]
    assert meta["requiere_panel_antes_recalc"] is True
    assert resp.json()["pedido_propuesto"][0]["cantidad"] == 10  # unchanged


def test_aceptar_and_rechazar():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    acc = client.post(
        "/api/pedidos/validar-minimos",
        json=_body(action="aceptar", proveedor="CHEAP"),
    )
    assert acc.status_code == 200
    assert "aceptó submínimo" in acc.json()["comparativa_cantidades"][0]["justificacion_delta"]

    rej = client.post(
        "/api/pedidos/validar-minimos",
        json=_body(action="rechazar", proveedor="CHEAP"),
    )
    assert rej.status_code == 200
    assert rej.json()["pedido_propuesto"][0]["proveedor"] == "EXPENSIVE"
