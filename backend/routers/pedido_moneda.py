"""Pedidos currency config — MonedaTrabajo + MonedaOferta por proveedor."""
from __future__ import annotations

import logging
import os
import sys
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

router = APIRouter(prefix="/api/pedidos", tags=["Pedidos"])


class MonedaTrabajoBody(BaseModel):
    moneda_trabajo: str = Field(..., description="USD | VES")


class MonedaOfertaBody(BaseModel):
    moneda_oferta: str = Field(..., description="USD | VES")


@router.get("/moneda-config")
async def get_moneda_config():
    """MonedaTrabajo (display) + BCV + MonedaOferta por lab."""
    import database

    try:
        from backend.services.pedido_app_config import fx_meta
        from backend.services.proveedor_config_loader import fetch_proveedor_groups
    except ImportError:
        from services.pedido_app_config import fx_meta  # type: ignore
        from services.proveedor_config_loader import fetch_proveedor_groups  # type: ignore

    conn = database.get_db_connection()
    try:
        meta = fx_meta(conn)
        groups = fetch_proveedor_groups(conn)
        return {
            **meta,
            "proveedores": [
                {
                    "proveedor_id": g["proveedor_id"],
                    "cod_prov": g["cod_prov"],
                    "nombre_corto": g["nombre_corto"],
                    "moneda_oferta": g.get("moneda_oferta") or "USD",
                    "monto_minimo_pedido_usd": g.get("monto_minimo_pedido_usd"),
                    "aliases": g.get("aliases") or [],
                }
                for g in groups
            ],
        }
    except Exception as exc:
        logging.error("moneda-config failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.put("/moneda-config/trabajo")
async def put_moneda_trabajo(body: MonedaTrabajoBody):
    import database

    try:
        from backend.services.pedido_app_config import set_moneda_trabajo, fx_meta
    except ImportError:
        from services.pedido_app_config import set_moneda_trabajo, fx_meta  # type: ignore

    conn = database.get_db_connection()
    try:
        m = set_moneda_trabajo(conn, body.moneda_trabajo)
        return {"ok": True, "moneda_trabajo": m, **fx_meta(conn)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.error("put moneda trabajo failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.put("/moneda-config/proveedor/{proveedor_id}")
async def put_moneda_oferta(proveedor_id: int, body: MonedaOfertaBody):
    import database

    try:
        from backend.services.proveedor_config_loader import (
            update_moneda_oferta,
            fetch_proveedor_config_rows,
        )
        from backend.services.pedido_app_config import fx_meta
    except ImportError:
        from services.proveedor_config_loader import (  # type: ignore
            update_moneda_oferta,
            fetch_proveedor_config_rows,
        )
        from services.pedido_app_config import fx_meta  # type: ignore

    conn = database.get_db_connection()
    try:
        update_moneda_oferta(conn, proveedor_id, body.moneda_oferta)
        rows = fetch_proveedor_config_rows(conn)
        row = next((r for r in rows if int(r["proveedor_id"]) == int(proveedor_id)), None)
        return {"ok": True, "proveedor": row, **fx_meta(conn)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logging.error("put moneda oferta failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
