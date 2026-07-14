"""ValidarMinimosProveedor — ADR-0016 (mínimo USD post-Generar)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


@dataclass(frozen=True)
class ProveedorDeficit:
    proveedor: str
    total_usd: float
    minimo_usd: float
    deficit_usd: float


@dataclass(frozen=True)
class ReplacementOption:
    barra: str
    descripcion: str
    proveedor: str
    precio: float
    ahorro_usd_vs_actual: float  # positive = cheaper than current line


@dataclass
class ValidarMinimosState:
    """Mutable working copy of Generar artifacts for the validation step."""

    pedido_propuesto: List[Dict[str, Any]]
    comparativa_cantidades: List[Dict[str, Any]]
    pedido_baseline: List[Dict[str, Any]] = field(default_factory=list)
    cobertura: float = 30.0
    criterios_agrupacion: List[str] = field(default_factory=list)
    intentos_recalc: Dict[str, int] = field(default_factory=dict)


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _price_index(
    market_offers: Sequence[Dict[str, Any]],
) -> Dict[Tuple[str, str], float]:
    """(barra, proveedor) → best (lowest) precio."""
    idx: Dict[Tuple[str, str], float] = {}
    for o in market_offers or []:
        barra = str(o.get("barra") or "").strip()
        prov = str(o.get("proveedor") or "").strip()
        if not barra or not prov:
            continue
        precio = _f(o.get("precio"), default=-1.0)
        if precio < 0:
            continue
        key = (barra, prov)
        if key not in idx or precio < idx[key]:
            idx[key] = precio
    return idx


def line_usd(
    line: Dict[str, Any],
    prices: Dict[Tuple[str, str], float],
) -> float:
    barra = str(line.get("barra") or "").strip()
    prov = str(line.get("proveedor") or "").strip()
    qty = _f(line.get("cantidad"))
    precio = prices.get((barra, prov))
    if precio is None:
        return 0.0
    return qty * precio


def totals_by_proveedor(
    propuesto: Sequence[Dict[str, Any]],
    market_offers: Sequence[Dict[str, Any]],
) -> Dict[str, float]:
    prices = _price_index(market_offers)
    totals: Dict[str, float] = {}
    for line in propuesto:
        prov = str(line.get("proveedor") or "").strip()
        if not prov:
            continue
        totals[prov] = totals.get(prov, 0.0) + line_usd(line, prices)
    return totals


def build_deficit_queue(
    propuesto: Sequence[Dict[str, Any]],
    market_offers: Sequence[Dict[str, Any]],
    minimos_usd: Dict[str, Optional[float]],
) -> List[ProveedorDeficit]:
    """Proveedores under minimum, largest deficit first. NULL minimo → skip."""
    totals = totals_by_proveedor(propuesto, market_offers)
    out: List[ProveedorDeficit] = []
    for prov, total in totals.items():
        minimo = minimos_usd.get(prov)
        if minimo is None:
            continue
        minimo_f = float(minimo)
        if minimo_f <= 0:
            continue
        if total + 1e-9 >= minimo_f:
            continue
        out.append(
            ProveedorDeficit(
                proveedor=prov,
                total_usd=round(total, 2),
                minimo_usd=round(minimo_f, 2),
                deficit_usd=round(minimo_f - total, 2),
            )
        )
    out.sort(key=lambda d: d.deficit_usd, reverse=True)
    return out


def barras_of_proveedor(
    propuesto: Sequence[Dict[str, Any]], proveedor: str
) -> List[str]:
    prov = str(proveedor).strip()
    seen: Set[str] = set()
    out: List[str] = []
    for line in propuesto:
        if str(line.get("proveedor") or "").strip() != prov:
            continue
        b = str(line.get("barra") or "").strip()
        if b and b not in seen:
            seen.add(b)
            out.append(b)
    return out


def qty_for_cobertura(
    *,
    rotacion_mensual: float,
    existen: float,
    cobertura_dias: float,
) -> int:
    return max(
        0,
        int(round(float(rotacion_mensual) * float(cobertura_dias) / 30.0 - float(existen))),
    )


def boost_qtys_for_barras(
    catalog_rows: Sequence[Dict[str, Any]],
    barras: Sequence[str],
    *,
    cobertura: float,
    pct_extra: float,
) -> Dict[str, int]:
    """New baseline-style qty at cobertura*(1+pct/100) for selected barras only."""
    wanted = {str(b).strip() for b in barras if str(b).strip()}
    cov = float(cobertura) * (1.0 + float(pct_extra) / 100.0)
    by_barra = {
        str(r.get("barra") or "").strip(): r
        for r in catalog_rows
        if str(r.get("barra") or "").strip()
    }
    out: Dict[str, int] = {}
    for b in wanted:
        row = by_barra.get(b)
        if row is None:
            continue
        out[b] = qty_for_cobertura(
            rotacion_mensual=_f(row.get("rotacion_mensual")),
            existen=_f(row.get("existen")),
            cobertura_dias=cov,
        )
    return out


def apply_qty_boost(
    state: ValidarMinimosState,
    *,
    proveedor: str,
    boost_qtys: Dict[str, int],
    pct_extra: float,
) -> ValidarMinimosState:
    """Update propuesto + comparativa qty for lines of this proveedor."""
    prov = str(proveedor).strip()
    note = (
        f"ValidarMinimos: +{pct_extra:g}% cobertura en SKUs de {prov}"
    )
    new_prop: List[Dict[str, Any]] = []
    for line in state.pedido_propuesto:
        row = dict(line)
        if str(row.get("proveedor") or "").strip() == prov:
            b = str(row.get("barra") or "").strip()
            if b in boost_qtys:
                row["cantidad"] = int(boost_qtys[b])
        new_prop.append(row)

    new_comp: List[Dict[str, Any]] = []
    for row in state.comparativa_cantidades:
        r = dict(row)
        # Match by propuesto barra when line was assigned to this proveedor
        bp = str(r.get("barra_propuesto") or "").strip()
        # Find proveedor for this propuesto barra in new_prop
        prop_line = next(
            (
                p
                for p in new_prop
                if str(p.get("barra") or "").strip() == bp
                and str(p.get("proveedor") or "").strip() == prov
            ),
            None,
        )
        if prop_line is not None and bp in boost_qtys:
            r["qty_propuesto"] = int(boost_qtys[bp])
            prev = (r.get("justificacion_delta") or "").strip()
            r["justificacion_delta"] = f"{prev}; {note}".strip("; ")
        new_comp.append(r)

    intentos = dict(state.intentos_recalc)
    intentos[prov] = int(intentos.get(prov, 0)) + 1

    return ValidarMinimosState(
        pedido_propuesto=new_prop,
        comparativa_cantidades=new_comp,
        pedido_baseline=list(state.pedido_baseline),
        cobertura=state.cobertura,
        criterios_agrupacion=list(state.criterios_agrupacion),
        intentos_recalc=intentos,
    )


def _group_key(row: Dict[str, Any], criterios: Sequence[str]) -> Tuple[str, ...]:
    return tuple(str(row.get(a) or "").strip() for a in criterios)


def _catalog_index(
    catalog_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    return {
        str(r.get("barra") or "").strip(): r
        for r in catalog_rows
        if str(r.get("barra") or "").strip()
    }


def second_best_for_line(
    *,
    barra: str,
    proveedor_actual: str,
    precio_actual: float,
    catalog_by_barra: Dict[str, Dict[str, Any]],
    market_offers: Sequence[Dict[str, Any]],
    criterios: Sequence[str],
) -> Optional[ReplacementOption]:
    """Prefer same barra other proveedor; else same Grupo MDM (ADR-0016 Q8=C)."""
    prices = _price_index(market_offers)
    actual = str(proveedor_actual).strip()
    b = str(barra).strip()

    # Same barra
    same_barra: List[ReplacementOption] = []
    for (ob, op), precio in prices.items():
        if ob != b or op == actual:
            continue
        ahorro = (precio_actual - precio) * 1.0  # per unit; caller scales by qty
        desc = ""
        row = catalog_by_barra.get(b)
        if row:
            desc = str(row.get("descripcion") or "")
        same_barra.append(
            ReplacementOption(
                barra=b,
                descripcion=desc,
                proveedor=op,
                precio=precio,
                ahorro_usd_vs_actual=precio_actual - precio,
            )
        )
    if same_barra:
        same_barra.sort(key=lambda x: x.precio)
        return same_barra[0]

    # Grupo MDM
    row = catalog_by_barra.get(b)
    if row is None or not criterios:
        return None
    gk = _group_key(row, criterios)
    if not any(gk):
        return None
    group_opts: List[ReplacementOption] = []
    for o in market_offers:
        ob = str(o.get("barra") or "").strip()
        op = str(o.get("proveedor") or "").strip()
        if not ob or not op or op == actual:
            continue
        crow = catalog_by_barra.get(ob)
        if crow is None:
            continue
        if _group_key(crow, criterios) != gk:
            continue
        precio = _f(o.get("precio"), default=-1.0)
        if precio < 0:
            continue
        group_opts.append(
            ReplacementOption(
                barra=ob,
                descripcion=str(crow.get("descripcion") or o.get("descripcion") or ""),
                proveedor=op,
                precio=precio,
                ahorro_usd_vs_actual=precio_actual - precio,
            )
        )
    if not group_opts:
        return None
    group_opts.sort(key=lambda x: x.precio)
    return group_opts[0]


def build_decision_panel(
    *,
    proveedor: str,
    state: ValidarMinimosState,
    catalog_rows: Sequence[Dict[str, Any]],
    market_offers: Sequence[Dict[str, Any]],
    minimo_usd: float,
) -> Dict[str, Any]:
    """Savings vs 2nd, replacements, orphan risk — for post-1st-fail panel."""
    prices = _price_index(market_offers)
    cat = _catalog_index(catalog_rows)
    criterios = state.criterios_agrupacion
    prov = str(proveedor).strip()
    lines = [
        dict(l)
        for l in state.pedido_propuesto
        if str(l.get("proveedor") or "").strip() == prov
    ]
    total = sum(line_usd(l, prices) for l in lines)
    replacements: List[Dict[str, Any]] = []
    ahorro_total = 0.0
    huerfanos_si_rechaza: List[Dict[str, Any]] = []

    for line in lines:
        b = str(line.get("barra") or "").strip()
        qty = _f(line.get("cantidad"))
        precio_act = prices.get((b, prov), 0.0)
        alt = second_best_for_line(
            barra=b,
            proveedor_actual=prov,
            precio_actual=precio_act,
            catalog_by_barra=cat,
            market_offers=market_offers,
            criterios=criterios,
        )
        if alt is None:
            huerfanos_si_rechaza.append(
                {
                    "barra": b,
                    "descripcion": line.get("descripcion") or "",
                    "cantidad": int(qty),
                }
            )
            continue
        ahorro_line = (precio_act - alt.precio) * qty
        ahorro_total += ahorro_line
        replacements.append(
            {
                "barra_actual": b,
                "barra_alternativa": alt.barra,
                "proveedor_alt": alt.proveedor,
                "precio_actual": round(precio_act, 4),
                "precio_alt": round(alt.precio, 4),
                "cantidad": int(qty),
                "ahorro_usd": round(ahorro_line, 2),
                "descripcion_alt": alt.descripcion,
            }
        )

    return {
        "proveedor": prov,
        "total_usd": round(total, 2),
        "minimo_usd": round(float(minimo_usd), 2),
        "deficit_usd": round(max(0.0, float(minimo_usd) - total), 2),
        "ahorro_vs_segundo_usd": round(ahorro_total, 2),
        "reemplazos": replacements,
        "huerfanos_si_rechaza": huerfanos_si_rechaza,
        "intentos_recalc": int(state.intentos_recalc.get(prov, 0)),
        "pct_extra_sugerido": 50.0,
    }


def accept_subminimo(
    state: ValidarMinimosState,
    *,
    proveedor: str,
    minimo_usd: float,
    market_offers: Sequence[Dict[str, Any]],
) -> ValidarMinimosState:
    prices = _price_index(market_offers)
    prov = str(proveedor).strip()
    total = sum(
        line_usd(l, prices)
        for l in state.pedido_propuesto
        if str(l.get("proveedor") or "").strip() == prov
    )
    note = (
        f"ValidarMinimos: aceptó submínimo {prov} "
        f"(total ${total:.2f} < mín ${float(minimo_usd):.2f})"
    )
    new_comp = []
    for row in state.comparativa_cantidades:
        r = dict(row)
        bp = str(r.get("barra_propuesto") or "").strip()
        if any(
            str(p.get("barra") or "").strip() == bp
            and str(p.get("proveedor") or "").strip() == prov
            for p in state.pedido_propuesto
        ):
            prev = (r.get("justificacion_delta") or "").strip()
            r["justificacion_delta"] = f"{prev}; {note}".strip("; ")
        new_comp.append(r)
    return ValidarMinimosState(
        pedido_propuesto=[dict(x) for x in state.pedido_propuesto],
        comparativa_cantidades=new_comp,
        pedido_baseline=list(state.pedido_baseline),
        cobertura=state.cobertura,
        criterios_agrupacion=list(state.criterios_agrupacion),
        intentos_recalc=dict(state.intentos_recalc),
    )


def reject_proveedor(
    state: ValidarMinimosState,
    *,
    proveedor: str,
    catalog_rows: Sequence[Dict[str, Any]],
    market_offers: Sequence[Dict[str, Any]],
) -> Tuple[ValidarMinimosState, List[str]]:
    """Reassign lines to 2nd best (barra→Grupo) or orphan (proveedor='').

    Returns (new_state, orphan_barras).
    """
    prices = _price_index(market_offers)
    cat = _catalog_index(catalog_rows)
    criterios = state.criterios_agrupacion
    prov = str(proveedor).strip()
    orphans: List[str] = []

    # old_barra_propuesto → new line fields + note
    reassignments: Dict[str, Dict[str, Any]] = {}
    new_prop: List[Dict[str, Any]] = []

    for line in state.pedido_propuesto:
        row = dict(line)
        if str(row.get("proveedor") or "").strip() != prov:
            new_prop.append(row)
            continue
        old_b = str(row.get("barra") or "").strip()
        precio_act = prices.get((old_b, prov), 0.0)
        alt = second_best_for_line(
            barra=old_b,
            proveedor_actual=prov,
            precio_actual=precio_act,
            catalog_by_barra=cat,
            market_offers=market_offers,
            criterios=criterios,
        )
        if alt is None:
            row["proveedor"] = ""
            orphans.append(old_b)
            note = f"ValidarMinimos: rechazó {prov} → huérfano (sin 2º)"
        else:
            row["barra"] = alt.barra
            row["descripcion"] = alt.descripcion or row.get("descripcion")
            row["proveedor"] = alt.proveedor
            note = (
                f"ValidarMinimos: rechazó {prov} → {alt.proveedor}/{alt.barra}"
            )
        reassignments[old_b] = {
            "barra": row["barra"],
            "descripcion": row.get("descripcion"),
            "cantidad": row.get("cantidad"),
            "proveedor": row.get("proveedor"),
            "note": note,
        }
        new_prop.append(row)

    new_comp: List[Dict[str, Any]] = []
    for crow in state.comparativa_cantidades:
        r = dict(crow)
        bp = str(r.get("barra_propuesto") or "").strip()
        if bp in reassignments:
            info = reassignments[bp]
            r["barra_propuesto"] = info["barra"]
            r["desc_propuesto"] = info["descripcion"]
            r["qty_propuesto"] = info["cantidad"]
            prev = (r.get("justificacion_delta") or "").strip()
            r["justificacion_delta"] = f"{prev}; {info['note']}".strip("; ")
        new_comp.append(r)

    return (
        ValidarMinimosState(
            pedido_propuesto=new_prop,
            comparativa_cantidades=new_comp,
            pedido_baseline=list(state.pedido_baseline),
            cobertura=state.cobertura,
            criterios_agrupacion=list(state.criterios_agrupacion),
            intentos_recalc=dict(state.intentos_recalc),
        ),
        orphans,
    )


def serialize_queue(queue: Sequence[ProveedorDeficit]) -> List[Dict[str, Any]]:
    return [
        {
            "proveedor": d.proveedor,
            "total_usd": d.total_usd,
            "minimo_usd": d.minimo_usd,
            "deficit_usd": d.deficit_usd,
        }
        for d in queue
    ]


def meta_validar_minimos(
    *,
    queue: Sequence[ProveedorDeficit],
    activo: Optional[str],
    panel: Optional[Dict[str, Any]],
    intentos_recalc: Dict[str, int],
    requiere_panel_antes_recalc: bool = False,
    orphans: Optional[List[str]] = None,
    decision: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "cola": serialize_queue(queue),
        "activo": activo,
        "panel": panel,
        "intentos_recalc": dict(intentos_recalc),
        "requiere_panel_antes_recalc": bool(requiere_panel_antes_recalc),
        "huerfanos": list(orphans or []),
        "ultima_decision": decision,
    }
