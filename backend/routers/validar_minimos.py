"""ValidarMinimosProveedor API — ADR-0016."""
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


class ValidarMinimosRequest(BaseModel):
    action: str = Field(
        ...,
        description="evaluar | recalcular | aceptar | rechazar",
    )
    cobertura: int = Field(..., ge=1, le=365)
    criterios_agrupacion: Optional[List[str]] = None
    pedido_propuesto: List[Dict[str, Any]]
    comparativa_cantidades: List[Dict[str, Any]]
    pedido_baseline: Optional[List[Dict[str, Any]]] = None
    proveedor: Optional[str] = None
    pct_extra: float = 50.0
    panel_ack: bool = False
    intentos_recalc: Optional[Dict[str, int]] = None
    catalog: Optional[List[Dict[str, Any]]] = None
    market_offers: Optional[List[Dict[str, Any]]] = None
    minimos_usd: Optional[Dict[str, Optional[float]]] = None


def _load_inputs(body: ValidarMinimosRequest):
    catalog = body.catalog
    offers = body.market_offers
    if catalog is None or offers is None:
        try:
            try:
                from backend.services.generar_sencillo_loaders import (
                    load_catalog_and_offers_from_db,
                )
            except ImportError:
                from services.generar_sencillo_loaders import (  # type: ignore
                    load_catalog_and_offers_from_db,
                )

            catalog, offers = load_catalog_and_offers_from_db()
        except Exception as exc:
            logging.error("validar-minimos DB load failed: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=503, detail=f"No se pudo cargar catálogo/mercado: {exc}"
            ) from exc

    minimos = body.minimos_usd
    if minimos is None:
        try:
            try:
                from backend.services.proveedor_config_loader import (
                    load_minimos_usd_from_db,
                    load_proveedor_config_from_db,
                )
            except ImportError:
                from services.proveedor_config_loader import (  # type: ignore
                    load_minimos_usd_from_db,
                    load_proveedor_config_from_db,
                )

            minimos = load_minimos_usd_from_db()
            config_rows = load_proveedor_config_from_db()
        except Exception as exc:
            logging.warning("ProveedorConfig load failed: %s", exc)
            minimos = {}
            config_rows = []
    else:
        config_rows = []

    return catalog, offers, minimos, config_rows


def _state_from_body(body: ValidarMinimosRequest):
    from analytics_engine.core.validar_minimos import ValidarMinimosState

    return ValidarMinimosState(
        pedido_propuesto=[dict(x) for x in body.pedido_propuesto],
        comparativa_cantidades=[dict(x) for x in body.comparativa_cantidades],
        pedido_baseline=[dict(x) for x in (body.pedido_baseline or [])],
        cobertura=float(body.cobertura),
        criterios_agrupacion=list(body.criterios_agrupacion or []),
        intentos_recalc=dict(body.intentos_recalc or {}),
    )


def _payload(state, meta_vm: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "pedido_propuesto": state.pedido_propuesto,
        "comparativa_cantidades": state.comparativa_cantidades,
        "pedido_baseline": state.pedido_baseline,
        "meta": {"validar_minimos": meta_vm},
    }


@router.post("/validar-minimos")
async def validar_minimos(body: ValidarMinimosRequest):
    """Post-Generar step: evaluate / recalc % / accept / reject supplier minimums."""
    from analytics_engine.core.criterios_agrupacion import CRITERIOS_AGRUPACION_DEFAULT
    from analytics_engine.core.validar_minimos import (
        accept_subminimo,
        apply_qty_boost,
        barras_of_proveedor,
        boost_qtys_for_barras,
        build_decision_panel,
        build_deficit_queue,
        meta_validar_minimos,
        reject_proveedor,
    )

    action = (body.action or "").strip().lower()
    if action not in ("evaluar", "recalcular", "aceptar", "rechazar"):
        raise HTTPException(
            status_code=400,
            detail="action must be evaluar|recalcular|aceptar|rechazar",
        )

    if not body.criterios_agrupacion:
        body.criterios_agrupacion = list(CRITERIOS_AGRUPACION_DEFAULT)

    catalog, offers, minimos, config_rows = _load_inputs(body)
    state = _state_from_body(body)
    id_by_cod = {r["cod_prov"]: r["proveedor_id"] for r in config_rows}

    def _queue():
        return build_deficit_queue(state.pedido_propuesto, offers, minimos)

    def _panel_for(prov: str) -> Optional[Dict[str, Any]]:
        minimo = minimos.get(prov)
        if minimo is None:
            return None
        panel = build_decision_panel(
            proveedor=prov,
            state=state,
            catalog_rows=catalog,
            market_offers=offers,
            minimo_usd=float(minimo),
        )
        panel["proveedor_id"] = id_by_cod.get(prov)
        return panel

    def _meta(**kwargs):
        m = meta_validar_minimos(**kwargs)
        for item in m.get("cola") or []:
            item["proveedor_id"] = id_by_cod.get(item["proveedor"])
        if m.get("activo"):
            m["activo_proveedor_id"] = id_by_cod.get(m["activo"])
        m["proveedores"] = config_rows
        return m

    if action == "evaluar":
        queue = _queue()
        activo = queue[0].proveedor if queue else None
        panel = None
        requiere = False
        if activo and int(state.intentos_recalc.get(activo, 0)) >= 1:
            panel = _panel_for(activo)
            requiere = True
        elif activo:
            # First contact: light panel with suggested pct (no force)
            panel = _panel_for(activo)
        return _payload(
            state,
            _meta(
                queue=queue,
                activo=activo,
                panel=panel,
                intentos_recalc=state.intentos_recalc,
                requiere_panel_antes_recalc=requiere,
            ),
        )

    prov = (body.proveedor or "").strip()
    if not prov:
        raise HTTPException(status_code=400, detail="proveedor required for this action")

    minimo = minimos.get(prov)
    if minimo is None:
        raise HTTPException(
            status_code=400,
            detail=f"proveedor {prov} sin MontoMinimoPedidoUSD (omitido)",
        )

    if action == "recalcular":
        intentos = int(state.intentos_recalc.get(prov, 0))
        if intentos >= 1 and not body.panel_ack:
            queue = _queue()
            return _payload(
                state,
                _meta(
                    queue=queue,
                    activo=prov,
                    panel=_panel_for(prov),
                    intentos_recalc=state.intentos_recalc,
                    requiere_panel_antes_recalc=True,
                ),
            )
        barras = barras_of_proveedor(state.pedido_propuesto, prov)
        boost = boost_qtys_for_barras(
            catalog, barras, cobertura=body.cobertura, pct_extra=body.pct_extra
        )
        state = apply_qty_boost(
            state, proveedor=prov, boost_qtys=boost, pct_extra=body.pct_extra
        )
        queue = _queue()
        still = any(d.proveedor == prov for d in queue)
        panel = _panel_for(prov) if still else None
        return _payload(
            state,
            _meta(
                queue=queue,
                activo=queue[0].proveedor if queue else None,
                panel=panel,
                intentos_recalc=state.intentos_recalc,
                requiere_panel_antes_recalc=still
                and int(state.intentos_recalc.get(prov, 0)) >= 1,
                decision="recalcular",
            ),
        )

    if action == "aceptar":
        state = accept_subminimo(
            state, proveedor=prov, minimo_usd=float(minimo), market_offers=offers
        )
        queue = [d for d in _queue() if d.proveedor != prov]
        return _payload(
            state,
            _meta(
                queue=queue,
                activo=queue[0].proveedor if queue else None,
                panel=_panel_for(queue[0].proveedor) if queue else None,
                intentos_recalc=state.intentos_recalc,
                decision="aceptar",
            ),
        )

    # rechazar
    state, orphans = reject_proveedor(
        state,
        proveedor=prov,
        catalog_rows=catalog,
        market_offers=offers,
    )
    queue = _queue()
    return _payload(
        state,
        _meta(
            queue=queue,
            activo=queue[0].proveedor if queue else None,
            panel=_panel_for(queue[0].proveedor) if queue else None,
            intentos_recalc=state.intentos_recalc,
            orphans=orphans,
            decision="rechazar",
        ),
    )
