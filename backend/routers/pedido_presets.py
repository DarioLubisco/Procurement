"""Custom Pedido Definitivo presets API — global company list."""
from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

router = APIRouter(prefix="/api/pedidos", tags=["Pedidos"])


class PedidoPresetBody(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    nivel: str = Field(..., description="Intermedio|Avanzado")
    base_preset: str = Field(..., description="Conservador|Normal|Agresivo")
    overrides: Dict[str, Any] = Field(default_factory=dict)


def _svc():
    try:
        from backend.services import pedido_presets_service as svc
    except ImportError:
        from services import pedido_presets_service as svc  # type: ignore
    return svc


def _conn():
    try:
        from backend import database
    except ImportError:
        import database  # type: ignore
    return database.get_db_connection()


@router.get("/presets")
async def list_pedido_presets():
    svc = _svc()
    try:
        conn = _conn()
        try:
            return {"presets": svc.list_presets(conn)}
        finally:
            conn.close()
    except Exception as exc:
        logging.error("list presets failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail=f"No se pudo listar presets: {exc}") from exc


@router.post("/presets")
async def upsert_pedido_preset(body: PedidoPresetBody):
    svc = _svc()
    try:
        conn = _conn()
        try:
            return svc.upsert_preset(
                conn,
                nombre=body.nombre,
                nivel=body.nivel,
                base_preset=body.base_preset,
                overrides=body.overrides,
            )
        finally:
            conn.close()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.error("upsert preset failed: %s", exc, exc_info=True)
        detail = str(exc)
        if "UQ_PedidoPresets_Nombre" in detail or "unique" in detail.lower():
            raise HTTPException(status_code=409, detail="Nombre de preset ya existe") from exc
        raise HTTPException(status_code=503, detail=f"No se pudo guardar preset: {exc}") from exc


@router.put("/presets/{preset_id}")
async def update_pedido_preset(preset_id: int, body: PedidoPresetBody):
    svc = _svc()
    try:
        conn = _conn()
        try:
            return svc.upsert_preset(
                conn,
                nombre=body.nombre,
                nivel=body.nivel,
                base_preset=body.base_preset,
                overrides=body.overrides,
                preset_id=preset_id,
            )
        finally:
            conn.close()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.error("update preset failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail=f"No se pudo actualizar preset: {exc}") from exc


@router.delete("/presets/{preset_id}")
async def delete_pedido_preset(preset_id: int):
    svc = _svc()
    try:
        conn = _conn()
        try:
            ok = svc.delete_preset(conn, preset_id)
        finally:
            conn.close()
    except Exception as exc:
        logging.error("delete preset failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail=f"No se pudo borrar preset: {exc}") from exc
    if not ok:
        raise HTTPException(status_code=404, detail=f"preset_id {preset_id} not found")
    return {"ok": True, "preset_id": preset_id}
