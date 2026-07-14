"""Generar Sencillo HTTP — unified seam (ticket 10)."""
from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

router = APIRouter(prefix="/api/pedidos", tags=["Pedidos"])


class GenerarSencilloRequest(BaseModel):
    cobertura: int = Field(..., ge=1, le=365)
    preset: str = "Conservador"
    criterios_agrupacion: Optional[List[str]] = None
    categorias: Optional[List[str]] = None
    include_generics: bool = True
    include_brands: bool = True
    umbral_rotacion: float = 0.0
    num_rows: int = 5000
    presupuesto_maximo: Optional[float] = None
    catalog: Optional[List[Dict[str, Any]]] = None
    market_offers: Optional[List[Dict[str, Any]]] = None
    backorder: Optional[List[Dict[str, Any]]] = None


class RegenerarDefinitivoRequest(BaseModel):
    cobertura: int = Field(..., ge=1, le=365)
    nivel: str = Field(..., description="Intermedio | Avanzado")
    base_preset: str = "Normal"
    criterios_agrupacion: Optional[List[str]] = None
    categorias: Optional[List[str]] = None
    include_generics: bool = True
    include_brands: bool = True
    umbral_rotacion: float = 0.0
    num_rows: int = 5000
    presupuesto_maximo: Optional[float] = None
    overrides: Optional[Dict[str, Any]] = None
    catalog: Optional[List[Dict[str, Any]]] = None
    market_offers: Optional[List[Dict[str, Any]]] = None
    backorder: Optional[List[Dict[str, Any]]] = None


def _load_catalog_offers_backorder(
    *,
    categorias: Optional[List[str]],
    include_generics: bool,
    include_brands: bool,
    catalog: Optional[List[Dict[str, Any]]],
    market_offers: Optional[List[Dict[str, Any]]],
    backorder: Optional[List[Dict[str, Any]]],
    log_label: str,
) -> Tuple[
    Sequence[Dict[str, Any]],
    Sequence[Dict[str, Any]],
    Sequence[Dict[str, Any]],
    int,
    str,
]:
    """Load DB inputs when not injected; return rows + load_ms + data_source."""
    t0 = time.perf_counter()
    data_source = "injected"
    out_catalog = catalog
    out_offers = market_offers

    if out_catalog is None or out_offers is None:
        data_source = "db"
        try:
            try:
                from backend.services.generar_sencillo_loaders import (
                    load_catalog_and_offers_from_db,
                )
            except ImportError:
                from services.generar_sencillo_loaders import (  # type: ignore
                    load_catalog_and_offers_from_db,
                )

            out_catalog, out_offers = load_catalog_and_offers_from_db(
                categorias=categorias,
                include_generics=include_generics,
                include_brands=include_brands,
            )
        except Exception as exc:
            logging.error("DB load for %s failed: %s", log_label, exc, exc_info=True)
            raise HTTPException(
                status_code=503,
                detail=f"No se pudo cargar catálogo/mercado: {exc}",
            ) from exc

    backorder_rows = backorder
    if backorder_rows is None:
        if data_source == "injected":
            # Injected catalog/offers but no backorder → still try DB for open BOs
            data_source = "injected+db_backorder"
        try:
            try:
                from backend.services.backorder_loader import load_backorder_from_db
            except ImportError:
                from services.backorder_loader import load_backorder_from_db  # type: ignore

            backorder_rows = load_backorder_from_db()
        except Exception as exc:
            logging.warning("Backorder DB load skipped: %s", exc)
            backorder_rows = []

    load_ms = int((time.perf_counter() - t0) * 1000)
    assert out_catalog is not None and out_offers is not None
    return out_catalog, out_offers, backorder_rows or [], load_ms, data_source


@router.post("/generar-sencillo")
async def generar_sencillo(body: GenerarSencilloRequest):
    """Productive Generar Sencillo → Comparativa + Propuesto (not Excel-primary)."""
    from analytics_engine.core.generar_sencillo_api import (
        attach_input_observability_meta,
        run_generar_sencillo,
    )

    catalog, offers, backorder_rows, load_ms, data_source = (
        _load_catalog_offers_backorder(
            categorias=body.categorias,
            include_generics=body.include_generics,
            include_brands=body.include_brands,
            catalog=body.catalog,
            market_offers=body.market_offers,
            backorder=body.backorder,
            log_label="generar-sencillo",
        )
    )

    try:
        payload = run_generar_sencillo(
            cobertura=body.cobertura,
            catalog_rows=catalog,
            market_offers_rows=offers,
            criterios_agrupacion=body.criterios_agrupacion,
            categorias=body.categorias,
            include_generics=body.include_generics,
            include_brands=body.include_brands,
            umbral_rotacion=body.umbral_rotacion,
            num_rows=body.num_rows,
            preset=body.preset,
            presupuesto_maximo=body.presupuesto_maximo,
            backorder_rows=backorder_rows,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.error("generar-sencillo failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    attach_input_observability_meta(
        payload,
        catalog_rows=catalog,
        market_offers_rows=offers,
        backorder_rows=backorder_rows,
        load_ms=load_ms,
        data_source=data_source,
    )
    return JSONResponse(payload)


@router.get("/overrides-schema")
async def overrides_schema(nivel: str = "Avanzado"):
    """Living OptimizerConfig knobs for Definitivo UI (excludes dead S4/kappa)."""
    from analytics_engine.core.presets import living_override_schema

    if nivel not in ("Intermedio", "Avanzado"):
        raise HTTPException(status_code=400, detail="nivel must be Intermedio|Avanzado")
    return living_override_schema(nivel=nivel)


@router.post("/regenerar-definitivo")
async def regenerar_definitivo(body: RegenerarDefinitivoRequest):
    """Regenerar PedidoDefinitivo (Intermedio/Avanzado) — distinct from first Generar."""
    from analytics_engine.core.generar_sencillo_api import (
        attach_input_observability_meta,
        run_regenerar_definitivo,
    )

    catalog, offers, backorder_rows, load_ms, data_source = (
        _load_catalog_offers_backorder(
            categorias=body.categorias,
            include_generics=body.include_generics,
            include_brands=body.include_brands,
            catalog=body.catalog,
            market_offers=body.market_offers,
            backorder=body.backorder,
            log_label="regenerar-definitivo",
        )
    )

    try:
        payload = run_regenerar_definitivo(
            cobertura=body.cobertura,
            nivel=body.nivel,
            catalog_rows=catalog,
            market_offers_rows=offers,
            criterios_agrupacion=body.criterios_agrupacion,
            categorias=body.categorias,
            include_generics=body.include_generics,
            include_brands=body.include_brands,
            umbral_rotacion=body.umbral_rotacion,
            num_rows=body.num_rows,
            base_preset=body.base_preset,
            presupuesto_maximo=body.presupuesto_maximo,
            overrides=body.overrides,
            backorder_rows=backorder_rows,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.error("regenerar-definitivo failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    attach_input_observability_meta(
        payload,
        catalog_rows=catalog,
        market_offers_rows=offers,
        backorder_rows=backorder_rows,
        load_ms=load_ms,
        data_source=data_source,
    )
    return JSONResponse(payload)
