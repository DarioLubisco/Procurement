"""Ahorro por motor principal — registry extensible (grill 2026-07-24).

P1 motors:
  - cantidad_vs_historico (same barcode, Δqty vs media_de_mediana)
  - sucedaneo (barcode change vs oferta_baseline / histórico)

Total = algebraic sum (negatives allowed). Missing prices → line contributes 0 + partial flag.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

# Stable P1 registry order (future motors append here).
AHORRO_MOTORS_P1: Tuple[Dict[str, str], ...] = (
    {
        "codigo": "cantidad_vs_historico",
        "titulo": "Ahorro · cantidad vs histórico",
    },
    {
        "codigo": "sucedaneo",
        "titulo": "Ahorro · sucedáneo",
    },
)


def _as_float(val: Any) -> Optional[float]:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _as_int(val: Any) -> int:
    try:
        return int(val or 0)
    except (TypeError, ValueError):
        return 0


def _precio_by_barra_from_propuesto(
    propuesto: Optional[Sequence[Mapping[str, Any]]],
) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for line in propuesto or []:
        barra = str(line.get("barra") or "").strip()
        px = _as_float(line.get("precio"))
        if barra and px is not None and barra not in out:
            out[barra] = px
    return out


def _factores(row: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    raw = row.get("justificacion_factores") or []
    return [f for f in raw if isinstance(f, Mapping)]


def _precio_propuesto(
    row: Mapping[str, Any],
    precio_by_barra: Mapping[str, float],
) -> Optional[float]:
    bp = str(row.get("barra_propuesto") or "").strip()
    if bp and bp in precio_by_barra:
        return float(precio_by_barra[bp])
    for f in _factores(row):
        if str(f.get("codigo") or "").lower() != "oferta":
            continue
        px = _as_float((f.get("datos") or {}).get("precio"))
        if px is not None:
            return px
    for f in _factores(row):
        datos = f.get("datos") or {}
        px = _as_float(datos.get("precio"))
        if px is not None:
            return px
        rivales = datos.get("rivales") or []
        for r in rivales:
            if not isinstance(r, Mapping):
                continue
            if r.get("elegida") or r.get("chosen"):
                px = _as_float(r.get("precio"))
                if px is not None:
                    return px
            if bp and str(r.get("barra") or "").strip() == bp:
                px = _as_float(r.get("precio"))
                if px is not None:
                    return px
    return _as_float(row.get("precio")) or _as_float(row.get("precio_propuesto"))


def _oferta_baseline(row: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    bb = str(row.get("barra_baseline") or "").strip()
    if not bb:
        return None
    for f in _factores(row):
        ob = (f.get("datos") or {}).get("oferta_baseline") or {}
        if isinstance(ob, Mapping) and str(ob.get("barra") or "").strip() == bb:
            return ob
    for f in _factores(row):
        for r in (f.get("datos") or {}).get("rivales") or []:
            if isinstance(r, Mapping) and str(r.get("barra") or "").strip() == bb:
                return r
    return None


def _media_historica(row: Mapping[str, Any]) -> Optional[float]:
    """media_de_mediana from oferta / baseline payloads."""
    for f in _factores(row):
        datos = f.get("datos") or {}
        if str(f.get("codigo") or "").lower() == "oferta":
            media = _as_float(datos.get("media_de_mediana"))
            if media is not None:
                return media
        media = _as_float(datos.get("media_de_mediana"))
        if media is not None:
            return media
        ob = datos.get("oferta_baseline") or {}
        if isinstance(ob, Mapping):
            media = _as_float(ob.get("media_de_mediana"))
            if media is not None:
                return media
    return None


def _precio_original_sucedaneo(row: Mapping[str, Any]) -> Optional[float]:
    """P_original: oferta_baseline.precio → fallback media_de_mediana."""
    ob = _oferta_baseline(row)
    if ob is not None:
        px = _as_float(ob.get("precio"))
        if px is not None:
            return px
        media = _as_float(ob.get("media_de_mediana"))
        if media is not None:
            return media
    return _media_historica(row)


def _qty_nueva(row: Mapping[str, Any]) -> int:
    """Primary propuesto qty + SplitLeadTime extra legs (ADR-0027)."""
    qp = _as_int(row.get("qty_propuesto"))
    extra = _as_int(row.get("extra_legs_qty"))
    if extra <= 0:
        # Some payloads embed legs instead of the sum field
        legs = row.get("extra_legs") or []
        if isinstance(legs, (list, tuple)):
            for leg in legs:
                if isinstance(leg, Mapping):
                    extra += _as_int(leg.get("cantidad") or leg.get("qty"))
    return qp + max(0, extra)


def empty_ahorros_payload() -> Dict[str, Any]:
    motors = [
        {
            "codigo": m["codigo"],
            "titulo": m["titulo"],
            "usd": 0.0,
            "n_lineas": 0,
        }
        for m in AHORRO_MOTORS_P1
    ]
    return {
        "ahorros_motores": motors,
        "ahorro_total_usd": 0.0,
        "ahorro_parcial": False,
        "ahorro_lineas_sin_valorizar": 0,
    }


def compute_ahorros_motores(
    comparativa: Optional[Sequence[Mapping[str, Any]]],
    propuesto: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    """Pure savings rollup from Comparativa (+ optional propuesto prices)."""
    precio_by_barra = _precio_by_barra_from_propuesto(propuesto)
    usd_by: Dict[str, float] = {m["codigo"]: 0.0 for m in AHORRO_MOTORS_P1}
    n_by: Dict[str, int] = {m["codigo"]: 0 for m in AHORRO_MOTORS_P1}
    incomplete = 0

    for row in comparativa or []:
        if not isinstance(row, Mapping):
            continue
        bb = str(row.get("barra_baseline") or "").strip()
        bp = str(row.get("barra_propuesto") or "").strip()
        qb = _as_int(row.get("qty_baseline"))
        q_new = _qty_nueva(row)

        if bb and bp and bb != bp:
            p_new = _precio_propuesto(row, precio_by_barra)
            p_orig = _precio_original_sucedaneo(row)
            if p_new is None or p_orig is None or q_new <= 0:
                if q_new > 0:
                    incomplete += 1
                continue
            usd_by["sucedaneo"] += float(q_new) * (p_orig - p_new)
            n_by["sucedaneo"] += 1
            continue

        if bb and bp and bb == bp and q_new != qb:
            p_act = _precio_propuesto(row, precio_by_barra)
            p_hist = _media_historica(row)
            if p_act is None or p_hist is None:
                incomplete += 1
                continue
            usd_by["cantidad_vs_historico"] += float(q_new - qb) * (p_hist - p_act)
            n_by["cantidad_vs_historico"] += 1

    motors = [
        {
            "codigo": m["codigo"],
            "titulo": m["titulo"],
            "usd": round(usd_by[m["codigo"]], 4),
            "n_lineas": int(n_by[m["codigo"]]),
        }
        for m in AHORRO_MOTORS_P1
    ]
    total = round(sum(float(x["usd"]) for x in motors), 4)
    return {
        "ahorros_motores": motors,
        "ahorro_total_usd": total,
        "ahorro_parcial": incomplete > 0,
        "ahorro_lineas_sin_valorizar": int(incomplete),
    }


def attach_ahorros_to_meta(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge ahorros_* into payload['meta'] from comparativa/propuesto."""
    meta = payload.setdefault("meta", {})
    computed = compute_ahorros_motores(
        payload.get("comparativa_cantidades") or [],
        payload.get("pedido_propuesto") or [],
    )
    meta.update(computed)
    return payload
