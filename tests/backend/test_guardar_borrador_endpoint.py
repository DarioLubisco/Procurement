"""HTTP Guardar borrador — ADR-0018 (injected fixtures, dry_run, no live DB)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers.guardar_borrador import router


def _groups():
    return [
        {
            "proveedor_id": 1,
            "cod_prov": "DROCERCA",
            "nombre_corto": "Drocerca",
            "monto_minimo_pedido_usd": 100.0,
            "aliases": ["DROCERCA"],
        }
    ]


def _body(**over):
    base = {
        "pedido_propuesto": [
            {
                "barra": "A",
                "descripcion": "Prod A",
                "proveedor": "DROCERCA",
                "cantidad": 4,
                "precio": 2.5,
            }
        ],
        "proveedor_groups": _groups(),
        "saprod_codprods": ["A"],
        "dry_run": True,
    }
    base.update(over)
    return base


def test_guardar_borrador_dry_run_ok():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    resp = client.post(
        "/api/pedidos/guardar-borrador",
        json=_body(
            parametros={
                "nivel": "Intermedio",
                "base_preset": "Normal",
                "overrides": {"sust_kappa": 5.0},
            }
        ),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ok"] is True
    assert data["dry_run"] is True
    assert data["meta"]["cabeceras"] == 1
    assert data["meta"]["detalle"][0]["monto_total_usd"] == 10.0
    assert data["meta"]["parametros"]["nivel"] == "Intermedio"
    assert data["meta"]["detalle"][0]["tiene_parametros"] is True


def test_fe_guardar_sends_parametros_hook():
    from pathlib import Path

    js = (Path(__file__).resolve().parents[2] / "frontend" / "js" / "app_pedidos.js").read_text(
        encoding="utf-8"
    )
    assert "lastDefinitivoParams" in js
    assert "buildDefinitivoParamsSnapshot" in js
    assert "parametros: lastDefinitivoParams" in js or "parametros: lastDefinitivoParams ||" in js


def test_guardar_borrador_422_when_nothing_to_write():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    resp = client.post(
        "/api/pedidos/guardar-borrador",
        json=_body(
            pedido_propuesto=[
                {
                    "barra": "A",
                    "descripcion": "A",
                    "proveedor": "NOPE",
                    "cantidad": 1,
                    "precio": 1.0,
                }
            ]
        ),
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["error"] == "no_cabeceras_utiles"


def test_guardar_borrador_persist_mocked():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    fake_written = [
        {
            "propuesta_id": 99,
            "cod_prov": "DROCERCA",
            "proveedor_id": 1,
            "total_lineas": 1,
            "total_unidades": 4,
            "monto_total_usd": 10.0,
        }
    ]
    with patch(
        "backend.services.guardar_borrador_service.guardar_borradores_from_db",
        return_value=fake_written,
    ):
        resp = client.post(
            "/api/pedidos/guardar-borrador",
            json=_body(dry_run=False),
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["cabeceras"][0]["propuesta_id"] == 99
