"""ValidarMinimosProveedor — ADR-0016 (mínimo USD post-Generar)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


@dataclass(frozen=True)
class ProveedorDeficit:
    proveedor: str  # canonical CodProv (stable key for activo / intentos)
    total_usd: float
    minimo_usd: float
    deficit_usd: float
    proveedor_id: Optional[int] = None
    nombre_corto: Optional[str] = None
    aliases: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ReplacementOption:
    barra: str
    descripcion: str
    proveedor: str
    precio: float
    ahorro_usd_vs_actual: float  # positive = cheaper than current line


def _upper(s: Any) -> str:
    return str(s or "").strip().upper()


def _annotate_vm_factor(
    row: Dict[str, Any],
    note: str,
    *,
    datos: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Append validar_minimos factor and rebuild short summary (grill)."""
    from .justificacion_factores import (
        append_factor,
        factor,
        factors_from_dicts,
        factors_to_dicts,
        finalize,
    )

    r = dict(row)
    facts = factors_from_dicts(r.get("justificacion_factores"))
    facts_t = append_factor(
        facts,
        factor("validar_minimos", note, datos=datos or {}),
    )
    resumen, tup = finalize(facts_t)
    r["justificacion_factores"] = factors_to_dicts(tup)
    r["justificacion_delta"] = resumen
    return r


def resolve_group(
    proveedor: str,
    groups: Optional[Sequence[Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
    """Find commercial group by canonical or any alias (case-insensitive)."""
    if not groups:
        return None
    u = _upper(proveedor)
    if not u:
        return None
    for g in groups:
        if _upper(g.get("cod_prov")) == u:
            return g
        for a in g.get("aliases") or []:
            if _upper(a) == u:
                return g
    return None


def group_cod_set(group: Optional[Dict[str, Any]], fallback: str = "") -> Set[str]:
    """Upper-cased CodProv set for a group (aliases + canonical)."""
    if group is None:
        f = _upper(fallback)
        return {f} if f else set()
    out: Set[str] = set()
    for a in group.get("aliases") or []:
        u = _upper(a)
        if u:
            out.add(u)
    u = _upper(group.get("cod_prov"))
    if u:
        out.add(u)
    return out


def line_in_cod_set(line: Dict[str, Any], cods: Set[str]) -> bool:
    return _upper(line.get("proveedor")) in cods


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
    """(barra, proveedor_upper) → best (lowest) precio USD."""
    idx: Dict[Tuple[str, str], float] = {}
    for o in market_offers or []:
        barra = str(o.get("barra") or "").strip()
        prov = _upper(o.get("proveedor"))
        if not barra or not prov:
            continue
        precio = _f(o.get("precio"), default=-1.0)
        if precio < 0:
            continue
        key = (barra, prov)
        if key not in idx or precio < idx[key]:
            idx[key] = precio
    return idx


def _lookup_precio(
    prices: Dict[Tuple[str, str], float],
    barra: str,
    proveedor: str,
    line: Optional[Dict[str, Any]] = None,
) -> Optional[float]:
    """Resolve USD unit price: market index (case-insensitive) then line.precio."""
    b = str(barra or "").strip()
    p = _upper(proveedor)
    if b and p and (b, p) in prices:
        return float(prices[(b, p)])
    if line is not None:
        lp = _f(line.get("precio"), default=-1.0)
        if lp >= 0:
            return float(lp)
    return None


def line_usd(
    line: Dict[str, Any],
    prices: Dict[Tuple[str, str], float],
) -> float:
    barra = str(line.get("barra") or "").strip()
    prov = str(line.get("proveedor") or "").strip()
    qty = _f(line.get("cantidad"))
    precio = _lookup_precio(prices, barra, prov, line)
    if precio is None:
        return 0.0
    return qty * precio


def totals_by_proveedor(
    propuesto: Sequence[Dict[str, Any]],
    market_offers: Sequence[Dict[str, Any]],
) -> Dict[str, float]:
    """Sum USD keyed by exact CodProv string (pre-alias / diagnostics)."""
    prices = _price_index(market_offers)
    totals: Dict[str, float] = {}
    for line in propuesto:
        prov = str(line.get("proveedor") or "").strip()
        if not prov:
            continue
        totals[prov] = totals.get(prov, 0.0) + line_usd(line, prices)
    return totals


def totals_by_group(
    propuesto: Sequence[Dict[str, Any]],
    market_offers: Sequence[Dict[str, Any]],
    groups: Sequence[Dict[str, Any]],
) -> Dict[str, float]:
    """Sum USD keyed by canonical CodProv (aliases aggregated)."""
    prices = _price_index(market_offers)
    idx = {_upper(a): g for g in groups for a in (g.get("aliases") or [g["cod_prov"]])}
    for g in groups:
        idx[_upper(g.get("cod_prov"))] = g
    totals: Dict[str, float] = {}
    for line in propuesto:
        raw = str(line.get("proveedor") or "").strip()
        if not raw:
            continue
        g = idx.get(_upper(raw))
        key = str(g["cod_prov"]).strip() if g else raw
        totals[key] = totals.get(key, 0.0) + line_usd(line, prices)
    return totals


def build_deficit_queue(
    propuesto: Sequence[Dict[str, Any]],
    market_offers: Sequence[Dict[str, Any]],
    minimos_usd: Dict[str, Optional[float]],
    *,
    groups: Optional[Sequence[Dict[str, Any]]] = None,
) -> List[ProveedorDeficit]:
    """Commercial entities under minimum, largest deficit first. NULL/0 minimo → skip."""
    if groups:
        totals = totals_by_group(propuesto, market_offers, groups)
        by_can = {str(g["cod_prov"]).strip(): g for g in groups}
        out: List[ProveedorDeficit] = []
        for can, total in totals.items():
            g = by_can.get(can)
            if g is not None:
                minimo = g.get("monto_minimo_pedido_usd")
            else:
                minimo = minimos_usd.get(can)
                if minimo is None:
                    # try any casing key in flat map
                    minimo = next(
                        (v for k, v in minimos_usd.items() if _upper(k) == _upper(can)),
                        None,
                    )
            if minimo is None:
                continue
            minimo_f = float(minimo)
            if minimo_f <= 0:
                continue
            if total + 1e-9 >= minimo_f:
                continue
            aliases = tuple(g.get("aliases") or [can]) if g else (can,)
            out.append(
                ProveedorDeficit(
                    proveedor=can,
                    total_usd=round(total, 2),
                    minimo_usd=round(minimo_f, 2),
                    deficit_usd=round(minimo_f - total, 2),
                    proveedor_id=int(g["proveedor_id"]) if g and g.get("proveedor_id") is not None else None,
                    nombre_corto=(g.get("nombre_corto") if g else None) or can,
                    aliases=aliases,
                )
            )
        out.sort(key=lambda d: d.deficit_usd, reverse=True)
        return out

    totals = totals_by_proveedor(propuesto, market_offers)
    out = []
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
                nombre_corto=prov,
                aliases=(prov,),
            )
        )
    out.sort(key=lambda d: d.deficit_usd, reverse=True)
    return out


def barras_of_proveedor(
    propuesto: Sequence[Dict[str, Any]],
    proveedor: str,
    *,
    groups: Optional[Sequence[Dict[str, Any]]] = None,
) -> List[str]:
    cods = group_cod_set(resolve_group(proveedor, groups), fallback=proveedor)
    seen: Set[str] = set()
    out: List[str] = []
    for line in propuesto:
        if not line_in_cod_set(line, cods):
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
    groups: Optional[Sequence[Dict[str, Any]]] = None,
) -> ValidarMinimosState:
    """Update propuesto + comparativa qty for all CodProv aliases of this group."""
    group = resolve_group(proveedor, groups)
    can = str(group["cod_prov"]).strip() if group else str(proveedor).strip()
    cods = group_cod_set(group, fallback=proveedor)
    note = (
        f"ValidarMinimos: +{pct_extra:g}% cobertura en SKUs de {can}"
    )
    new_prop: List[Dict[str, Any]] = []
    for line in state.pedido_propuesto:
        row = dict(line)
        if line_in_cod_set(row, cods):
            b = str(row.get("barra") or "").strip()
            if b in boost_qtys:
                row["cantidad"] = int(boost_qtys[b])
        new_prop.append(row)

    new_comp: List[Dict[str, Any]] = []
    for row in state.comparativa_cantidades:
        r = dict(row)
        bp = str(r.get("barra_propuesto") or "").strip()
        prop_line = next(
            (
                p
                for p in new_prop
                if str(p.get("barra") or "").strip() == bp
                and line_in_cod_set(p, cods)
            ),
            None,
        )
        if prop_line is not None and bp in boost_qtys:
            r["qty_propuesto"] = int(boost_qtys[bp])
            r = _annotate_vm_factor(
                r,
                note,
                datos={"accion": "recalcular", "qty": int(boost_qtys[bp])},
            )
        new_comp.append(r)

    intentos = dict(state.intentos_recalc)
    intentos[can] = int(intentos.get(can, 0)) + 1

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
    exclude_cod_provs: Optional[Set[str]] = None,
) -> Optional[ReplacementOption]:
    """Prefer same barra other proveedor; else same Grupo MDM (ADR-0016 Q8=C).

    exclude_cod_provs: upper-cased CodProvs treated as the same commercial entity
    (sibling aliases must not count as a valid 2nd supplier).
    """
    prices = _price_index(market_offers)
    actual = str(proveedor_actual).strip()
    excluded = set(exclude_cod_provs or ())
    excluded.add(_upper(actual))
    b = str(barra).strip()

    def _excluded(op: str) -> bool:
        return _upper(op) in excluded

    # Same barra
    same_barra: List[ReplacementOption] = []
    for (ob, op_u), precio in prices.items():
        if ob != b or op_u in excluded or _excluded(op_u):
            continue
        desc = ""
        row = catalog_by_barra.get(b)
        if row:
            desc = str(row.get("descripcion") or "")
        same_barra.append(
            ReplacementOption(
                barra=b,
                descripcion=desc,
                proveedor=op_u,  # index key is already upper
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
        if not ob or not op or _excluded(op):
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
    groups: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Savings vs 2nd, replacements, orphan risk — for post-1st-fail panel."""
    prices = _price_index(market_offers)
    cat = _catalog_index(catalog_rows)
    criterios = state.criterios_agrupacion
    group = resolve_group(proveedor, groups)
    can = str(group["cod_prov"]).strip() if group else str(proveedor).strip()
    cods = group_cod_set(group, fallback=proveedor)
    lines = [dict(l) for l in state.pedido_propuesto if line_in_cod_set(l, cods)]
    total = sum(line_usd(l, prices) for l in lines)
    replacements: List[Dict[str, Any]] = []
    ahorro_total = 0.0
    huerfanos_si_rechaza: List[Dict[str, Any]] = []

    for line in lines:
        b = str(line.get("barra") or "").strip()
        line_prov = str(line.get("proveedor") or "").strip()
        qty = _f(line.get("cantidad"))
        precio_act = _lookup_precio(prices, b, line_prov, line)
        precio_missing = precio_act is None
        if precio_act is None:
            precio_act = 0.0
        alt = second_best_for_line(
            barra=b,
            proveedor_actual=line_prov,
            precio_actual=float(precio_act),
            catalog_by_barra=cat,
            market_offers=market_offers,
            criterios=criterios,
            exclude_cod_provs=cods,
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
        # Skip bogus ahorro when we never resolved the current USD price
        # (was defaulting to 0 → fake ~-$qty*alt looking like a FX bug).
        if precio_missing:
            replacements.append(
                {
                    "barra_actual": b,
                    "barra_alternativa": alt.barra,
                    "proveedor_actual": line_prov,
                    "proveedor_alt": alt.proveedor,
                    "precio_actual": None,
                    "precio_alt": round(alt.precio, 4),
                    "cantidad": int(qty),
                    "ahorro_usd": None,
                    "delta_pct": None,
                    "precio_actual_missing": True,
                    "descripcion_alt": alt.descripcion,
                }
            )
            continue
        ahorro_line = (float(precio_act) - alt.precio) * qty
        # % vs costo actual de la línea (negativo = alt más caro)
        base_line = float(precio_act) * qty
        delta_pct = (ahorro_line / base_line * 100.0) if base_line > 1e-12 else None
        ahorro_total += ahorro_line
        replacements.append(
            {
                "barra_actual": b,
                "barra_alternativa": alt.barra,
                "proveedor_actual": line_prov,
                "proveedor_alt": alt.proveedor,
                "precio_actual": round(float(precio_act), 4),
                "precio_alt": round(alt.precio, 4),
                "cantidad": int(qty),
                "ahorro_usd": round(ahorro_line, 2),
                "delta_pct": round(delta_pct, 1) if delta_pct is not None else None,
                "precio_actual_missing": False,
                "descripcion_alt": alt.descripcion,
            }
        )

    return {
        "proveedor": can,
        "proveedor_id": int(group["proveedor_id"]) if group and group.get("proveedor_id") is not None else None,
        "nombre_corto": (group.get("nombre_corto") if group else None) or can,
        "aliases": list(group.get("aliases") or [can]) if group else [can],
        "total_usd": round(total, 2),
        "minimo_usd": round(float(minimo_usd), 2),
        "deficit_usd": round(max(0.0, float(minimo_usd) - total), 2),
        "ahorro_vs_segundo_usd": round(ahorro_total, 2),
        "reemplazos": replacements,
        "huerfanos_si_rechaza": huerfanos_si_rechaza,
        "intentos_recalc": int(state.intentos_recalc.get(can, 0)),
        "pct_extra_sugerido": 50.0,
    }


def accept_subminimo(
    state: ValidarMinimosState,
    *,
    proveedor: str,
    minimo_usd: float,
    market_offers: Sequence[Dict[str, Any]],
    groups: Optional[Sequence[Dict[str, Any]]] = None,
) -> ValidarMinimosState:
    prices = _price_index(market_offers)
    group = resolve_group(proveedor, groups)
    can = str(group["cod_prov"]).strip() if group else str(proveedor).strip()
    cods = group_cod_set(group, fallback=proveedor)
    total = sum(
        line_usd(l, prices)
        for l in state.pedido_propuesto
        if line_in_cod_set(l, cods)
    )
    note = (
        f"ValidarMinimos: aceptó submínimo {can} "
        f"(total ${total:.2f} < mín ${float(minimo_usd):.2f})"
    )
    new_comp = []
    for row in state.comparativa_cantidades:
        r = dict(row)
        bp = str(r.get("barra_propuesto") or "").strip()
        if any(
            str(p.get("barra") or "").strip() == bp and line_in_cod_set(p, cods)
            for p in state.pedido_propuesto
        ):
            r = _annotate_vm_factor(r, note, datos={"accion": "aceptar"})
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
    groups: Optional[Sequence[Dict[str, Any]]] = None,
) -> Tuple[ValidarMinimosState, List[str]]:
    """Reassign all group lines to 2nd best (barra→Grupo) or orphan (proveedor='').

    Sibling aliases of the same ProveedorID are never treated as a valid 2nd supplier.
    Returns (new_state, orphan_barras).
    """
    prices = _price_index(market_offers)
    cat = _catalog_index(catalog_rows)
    criterios = state.criterios_agrupacion
    group = resolve_group(proveedor, groups)
    can = str(group["cod_prov"]).strip() if group else str(proveedor).strip()
    cods = group_cod_set(group, fallback=proveedor)
    orphans: List[str] = []

    reassignments: Dict[str, Dict[str, Any]] = {}
    new_prop: List[Dict[str, Any]] = []

    for line in state.pedido_propuesto:
        row = dict(line)
        if not line_in_cod_set(row, cods):
            new_prop.append(row)
            continue
        old_b = str(row.get("barra") or "").strip()
        line_prov = str(row.get("proveedor") or "").strip()
        precio_act = _lookup_precio(prices, old_b, line_prov, row)
        if precio_act is None:
            precio_act = 0.0
        alt = second_best_for_line(
            barra=old_b,
            proveedor_actual=line_prov,
            precio_actual=float(precio_act),
            catalog_by_barra=cat,
            market_offers=market_offers,
            criterios=criterios,
            exclude_cod_provs=cods,
        )
        if alt is None:
            row["proveedor"] = ""
            orphans.append(old_b)
            note = f"ValidarMinimos: rechazó {can} → huérfano (sin 2º)"
        else:
            row["barra"] = alt.barra
            row["descripcion"] = alt.descripcion or row.get("descripcion")
            row["proveedor"] = alt.proveedor
            note = (
                f"ValidarMinimos: rechazó {can} → {alt.proveedor}/{alt.barra}"
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
            r = _annotate_vm_factor(
                r,
                info["note"],
                datos={
                    "accion": "rechazar",
                    "barra": info["barra"],
                    "cantidad": info["cantidad"],
                },
            )
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
            "proveedor_id": d.proveedor_id,
            "nombre_corto": d.nombre_corto or d.proveedor,
            "aliases": list(d.aliases),
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
