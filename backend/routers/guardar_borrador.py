"""Guardar BorradorPedidos from PedidoDefinitivo — ADR-0018."""
from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

router = APIRouter(prefix="/api/pedidos", tags=["Pedidos"])


class GuardarBorradorRequest(BaseModel):
    pedido_propuesto: List[Dict[str, Any]] = Field(
        ...,
        description="Definitivo lines (barra, descripcion, proveedor, cantidad, precio?)",
    )
    parametros: Optional[Dict[str, Any]] = Field(
        None,
        description="Snapshot Definitivo: nivel, base_preset, cobertura, criterios, overrides, meta",
    )
    # Test / offline inject
    proveedor_groups: Optional[List[Dict[str, Any]]] = None
    saprod_codprods: Optional[List[str]] = None
    dry_run: bool = False


def _load_groups(body: GuardarBorradorRequest) -> List[Dict[str, Any]]:
    if body.proveedor_groups is not None:
        return list(body.proveedor_groups)
    try:
        try:
            from backend.services.proveedor_config_loader import (
                load_proveedor_groups_from_db,
            )
        except ImportError:
            from services.proveedor_config_loader import (  # type: ignore
                load_proveedor_groups_from_db,
            )
        return load_proveedor_groups_from_db()
    except Exception as exc:
        logging.warning("ProveedorConfig/aliases load failed: %s", exc)
        return []


def _load_saprod(body: GuardarBorradorRequest, barras: List[str]) -> set:
    if body.saprod_codprods is not None:
        return {str(x).strip() for x in body.saprod_codprods if str(x).strip()}
    try:
        try:
            from backend.services.guardar_borrador_service import fetch_saprod_codprods
        except ImportError:
            from services.guardar_borrador_service import (  # type: ignore
                fetch_saprod_codprods,
            )
        import database

        conn = database.get_db_connection()
        try:
            return fetch_saprod_codprods(conn, barras)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as exc:
        logging.error("SAPROD lookup failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=503, detail=f"No se pudo validar CodProd en SAPROD: {exc}"
        ) from exc


@router.post("/guardar-borrador")
async def guardar_borrador(body: GuardarBorradorRequest):
    """Persist PedidoDefinitivo into BorradorPedidos (explicit save; ADR-0018)."""
    from analytics_engine.core.guardar_borrador import prepare_borradores, plan_to_meta

    if not body.pedido_propuesto:
        raise HTTPException(status_code=400, detail="pedido_propuesto vacío")

    groups = _load_groups(body)
    barras = [
        str(r.get("barra") or "").strip()
        for r in body.pedido_propuesto
        if str(r.get("barra") or "").strip()
    ]
    saprod = _load_saprod(body, barras)
    plan = prepare_borradores(
        body.pedido_propuesto,
        groups=groups,
        saprod_codprods=saprod,
        parametros=body.parametros,
    )
    meta = plan_to_meta(plan)

    if not plan.cabeceras:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "no_cabeceras_utiles",
                "message": "Ningún proveedor/línea quedó listo para guardar tras filtros.",
                "meta": meta,
            },
        )

    if body.dry_run:
        return {"ok": True, "dry_run": True, "cabeceras": [], "meta": meta}

    try:
        try:
            from backend.services.guardar_borrador_service import (
                guardar_borradores_from_db,
            )
        except ImportError:
            from services.guardar_borrador_service import (  # type: ignore
                guardar_borradores_from_db,
            )
        written = guardar_borradores_from_db(plan)
    except Exception as exc:
        logging.error("guardar-borrador persist failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error al persistir borradores: {exc}"
        ) from exc

    return {"ok": True, "dry_run": False, "cabeceras": written, "meta": meta}
