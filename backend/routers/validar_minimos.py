"""ValidarMinimosProveedor API — ADR-0016 (+ ProveedorID aliases)."""
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
    proveedor_groups: Optional[List[Dict[str, Any]]] = None


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

    try:
        from backend.services.proveedor_config_loader import (
            groups_from_flat_minimos,
            load_proveedor_groups_from_db,
            minimos_usd_from_groups,
        )
    except ImportError:
        from services.proveedor_config_loader import (  # type: ignore
            groups_from_flat_minimos,
            load_proveedor_groups_from_db,
            minimos_usd_from_groups,
        )

    if body.proveedor_groups is not None:
        groups = list(body.proveedor_groups)
        minimos = (
            body.minimos_usd
            if body.minimos_usd is not None
            else minimos_usd_from_groups(groups)
        )
    elif body.minimos_usd is not None:
        minimos = body.minimos_usd
        groups = groups_from_flat_minimos(minimos)
    else:
        try:
            groups = load_proveedor_groups_from_db()
            minimos = minimos_usd_from_groups(groups)
        except Exception as exc:
            logging.warning("ProveedorConfig/aliases load failed: %s", exc)
            groups = []
            minimos = {}

    return catalog, offers, minimos, groups


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


def _minimo_for_canonical(prov: str, groups: List[Dict[str, Any]], minimos: Dict):
    from analytics_engine.core.validar_minimos import resolve_group

    g = resolve_group(prov, groups)
    if g is not None and g.get("monto_minimo_pedido_usd") is not None:
        return float(g["monto_minimo_pedido_usd"]), g
    if prov in minimos and minimos[prov] is not None:
        return float(minimos[prov]), g
    return None, g


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
        resolve_group,
    )

    action = (body.action or "").strip().lower()
    if action not in ("evaluar", "recalcular", "aceptar", "rechazar"):
        raise HTTPException(
            status_code=400,
            detail="action must be evaluar|recalcular|aceptar|rechazar",
        )

    if not body.criterios_agrupacion:
        body.criterios_agrupacion = list(CRITERIOS_AGRUPACION_DEFAULT)

    catalog, offers, minimos, groups = _load_inputs(body)
    state = _state_from_body(body)

    def _queue():
        return build_deficit_queue(
            state.pedido_propuesto, offers, minimos, groups=groups
        )

    def _panel_for(prov: str) -> Optional[Dict[str, Any]]:
        minimo, _g = _minimo_for_canonical(prov, groups, minimos)
        if minimo is None:
            return None
        return build_decision_panel(
            proveedor=prov,
            state=state,
            catalog_rows=catalog,
            market_offers=offers,
            minimo_usd=float(minimo),
            groups=groups,
        )

    def _meta(**kwargs):
        m = meta_validar_minimos(**kwargs)
        if m.get("activo"):
            g = resolve_group(m["activo"], groups)
            if g is not None:
                m["activo_proveedor_id"] = g.get("proveedor_id")
                m["activo_nombre_corto"] = g.get("nombre_corto")
        m["proveedores"] = groups
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

    prov_raw = (body.proveedor or "").strip()
    if not prov_raw:
        raise HTTPException(status_code=400, detail="proveedor required for this action")

    g = resolve_group(prov_raw, groups)
    prov = str(g["cod_prov"]).strip() if g else prov_raw
    minimo, _ = _minimo_for_canonical(prov, groups, minimos)
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
        barras = barras_of_proveedor(
            state.pedido_propuesto, prov, groups=groups
        )
        boost = boost_qtys_for_barras(
            catalog, barras, cobertura=body.cobertura, pct_extra=body.pct_extra
        )
        state = apply_qty_boost(
            state,
            proveedor=prov,
            boost_qtys=boost,
            pct_extra=body.pct_extra,
            groups=groups,
        )
        queue = _queue()
        still = any(d.proveedor == prov for d in queue)
        # Always rebuild panel for the proveedor just recalculated so FE shows
        # updated total_usd / déficit even if they now meet the minimum.
        panel = _panel_for(prov)
        return _payload(
            state,
            _meta(
                queue=queue,
                activo=prov if still else (queue[0].proveedor if queue else None),
                panel=panel,
                intentos_recalc=state.intentos_recalc,
                requiere_panel_antes_recalc=still
                and int(state.intentos_recalc.get(prov, 0)) >= 1,
                decision="recalcular",
            ),
        )

    if action == "aceptar":
        state = accept_subminimo(
            state,
            proveedor=prov,
            minimo_usd=float(minimo),
            market_offers=offers,
            groups=groups,
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

    state, orphans = reject_proveedor(
        state,
        proveedor=prov,
        catalog_rows=catalog,
        market_offers=offers,
        groups=groups,
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
