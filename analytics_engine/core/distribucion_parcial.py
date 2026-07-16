"""DistribucionParcial multi-factor within Grupo (ADR-0006) + kappa ceiling (ADR-0017)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import pandas as pd

from .competencia_top_n import competencia_payload
from .gap_extension import MiembroGrupo, compute_gap_extension_oferta
from .justificacion_factores import (
    JustificacionFactor,
    append_factor,
    factor,
    finalize,
)
from .nonlinear import quadratic_ceiling
from .pedido_baseline import BaselineLine
from .presets import PresetKnobs, max_sustitucion_base_from_elasticidad
from .split_lead_time import OfferCandidate, compute_split_lead_time

# Desvío threshold for F5 trigger (Normal default ADR-0011)
_F5_DESVIO_UMBRAL = -0.10


@dataclass(frozen=True)
class PropuestoLeg:
    barra: str
    descripcion: str
    proveedor: str
    cantidad: int
    precio: Optional[float] = None  # USD offer; None if unknown (ADR-0018)


@dataclass(frozen=True)
class Allocation:
    barra_baseline: str
    desc_baseline: str
    qty_baseline: int
    barra_propuesto: str
    desc_propuesto: str
    qty_propuesto: int
    proveedor: str
    justificacion_delta: str
    # Extra Propuesto lines when SplitLeadTime fires (same Baseline row)
    extra_legs: Tuple[PropuestoLeg, ...] = field(default_factory=tuple)
    precio: Optional[float] = None  # USD of primary leg offer
    justificacion_factores: Tuple[JustificacionFactor, ...] = field(default_factory=tuple)

def distribute_parcial(
    baseline: Sequence[BaselineLine],
    catalog: pd.DataFrame,
    market_offers: pd.DataFrame,
    knobs: PresetKnobs,
    criterios: Sequence[str],
) -> List[Allocation]:
    """Allocate each Baseline line a partial Propuesto quota using multi-factor scores.

    Not winner-takes-all: each Baseline BARRA keeps its own qty as the quota ceiling
    (before optional F5 reinforcement to offers only).
    """
    # Empty / schema-less catalog (filtered category, inject []) → no KeyError on barra
    if catalog is None or catalog.empty or "barra" not in catalog.columns:
        resumen, facts = finalize(
            [
                factor(
                    "sin_catalogo",
                    "sin catálogo (vacío o sin columna barra)",
                )
            ]
        )
        return [
            Allocation(
                barra_baseline=line.barra,
                desc_baseline=line.descripcion,
                qty_baseline=line.cantidad,
                barra_propuesto=line.barra,
                desc_propuesto=line.descripcion,
                qty_propuesto=line.cantidad,
                proveedor="",
                justificacion_delta=resumen,
                justificacion_factores=facts,
            )
            for line in baseline
        ]

    cat = catalog.copy()
    cat["barra"] = cat["barra"].astype(str)
    # Empty / failed market load (e.g. Mercado_Vivo timeout) → no columns
    if (
        market_offers is None
        or market_offers.empty
        or "barra" not in market_offers.columns
    ):
        resumen, facts = finalize(
            [
                factor(
                    "sin_oferta",
                    "sin ofertas de mercado (Mercado_Vivo vacío o timeout)",
                )
            ]
        )
        return [
            Allocation(
                barra_baseline=line.barra,
                desc_baseline=line.descripcion,
                qty_baseline=line.cantidad,
                barra_propuesto=line.barra,
                desc_propuesto=line.descripcion,
                qty_propuesto=line.cantidad,
                proveedor="",
                justificacion_delta=resumen,
                justificacion_factores=facts,
            )
            for line in baseline
        ]

    offers = _enrich_offers_with_grupo(market_offers, cat, criterios)

    by_barra = {str(r.barra): r for _, r in cat.iterrows()}
    out: List[Allocation] = []

    for line in baseline:
        row = by_barra.get(line.barra)
        group_key = _group_key(row, criterios) if row is not None else None
        candidates = _offers_for_group(offers, group_key, criterios) if group_key else pd.DataFrame()

        if candidates.empty:
            resumen, facts = finalize(
                [factor("sin_oferta", "sin ofertas para el Grupo de esta línea")]
            )
            out.append(
                Allocation(
                    barra_baseline=line.barra,
                    desc_baseline=line.descripcion,
                    qty_baseline=line.cantidad,
                    barra_propuesto=line.barra,
                    desc_propuesto=line.descripcion,
                    qty_propuesto=line.cantidad,
                    proveedor="",
                    justificacion_delta=resumen,
                    justificacion_factores=facts,
                )
            )
            continue

        split = _try_split_lead_time(line, row, candidates, knobs)
        if split is not None:
            out.append(split)
            continue

        scored = _score_offers(candidates, knobs, baseline_elasticidad=_elasticidad(row))
        chosen = scored.iloc[0]
        qty_baseline = int(line.cantidad)

        barra_p = str(chosen["barra"])
        # Same BARRA → keep Baseline/catalog description (Mercado_Vivo text often differs).
        if barra_p == str(line.barra):
            desc_p = line.descripcion
        else:
            desc_p = line.descripcion
            if "descripcion" in chosen.index and pd.notna(chosen.get("descripcion")):
                desc_p = str(chosen["descripcion"])
            elif barra_p in by_barra:
                desc_p = str(by_barra[barra_p]["descripcion"])

        kappa_alloc = _apply_kappa_split_if_needed(
            line=line,
            row=row,
            chosen=chosen,
            barra_p=barra_p,
            desc_p=desc_p,
            qty_baseline=qty_baseline,
            knobs=knobs,
        )
        if kappa_alloc is not None:
            out.append(kappa_alloc)
            continue

        factors: List[JustificacionFactor] = []
        if barra_p != str(line.barra):
            herm = competencia_payload(
                scored,
                baseline_barra=str(line.barra),
                elegida_barra=barra_p,
                elegida_proveedor=str(chosen.get("proveedor") or ""),
                rivales_n=int(getattr(knobs, "rivales_top_n", 3) or 3),
                hermanos_n=int(getattr(knobs, "hermanos_top_n", 3) or 3),
            )
            factors.append(
                factor(
                    "sucedaneo",
                    f"{line.barra}→{barra_p} (sucedáneo del Grupo)",
                    datos={
                        "barra_baseline": line.barra,
                        "barra_propuesto": barra_p,
                        "hermanos_reemplazables": herm.get("hermanos_reemplazables") or [],
                        "top_n_hermanos": herm.get("top_n_hermanos"),
                    },
                )
            )
        prov = str(chosen["proveedor"])
        precio = _offer_precio(chosen)
        oferta_f = _oferta_factor_from_chosen(
            chosen,
            scored=scored,
            baseline_barra=str(line.barra),
            knobs=knobs,
        )
        if oferta_f is not None:
            factors.append(oferta_f)

        qty = qty_baseline
        qty, amp_f = _amplifier_factor(qty, chosen, knobs)
        if amp_f is not None:
            factors.append(amp_f)
        stock = chosen.get("stock_proveedor")
        if pd.notna(stock):
            qty = min(qty, int(stock))

        if qty != qty_baseline:
            factors.append(
                factor(
                    "delta_qty",
                    f"{qty_baseline}→{qty}",
                    datos={"qty_baseline": qty_baseline, "qty_propuesto": qty},
                )
            )

        resumen, facts = finalize(factors)
        out.append(
            Allocation(
                barra_baseline=line.barra,
                desc_baseline=line.descripcion,
                qty_baseline=line.cantidad,
                barra_propuesto=barra_p,
                desc_propuesto=desc_p,
                qty_propuesto=qty,
                proveedor=prov,
                justificacion_delta=resumen,
                precio=precio,
                justificacion_factores=facts,
            )
        )
    if knobs.ext_max_dias_extra > 0:
        out = _apply_f5_extension(
            out, baseline, cat, offers, criterios, by_barra, knobs.f5_umbral
        )
    out = _resolve_unmet_via_grupo(
        out, cat, offers, criterios, by_barra, knobs
    )
    return out


def _allocation_is_unmet(a: Allocation) -> bool:
    """Only true sin_oferta / sin_catalogo — not kappa-forced baseline (empty proveedor)."""
    codes = {f.codigo for f in a.justificacion_factores}
    return "sin_oferta" in codes or "sin_catalogo" in codes


def _resolve_unmet_via_grupo(
    allocations: List[Allocation],
    catalog: pd.DataFrame,
    offers: pd.DataFrame,
    criterios: Sequence[str],
    by_barra: dict,
    knobs: PresetKnobs,
) -> List[Allocation]:
    """Sin oferta → sucedáneo de mercado del Grupo, o compensación a hermano ya en pedido.

    Elasticidad (0–5) acota cuánto del gap de la línea sin oferta se traslada al hermano.
    """
    out = list(allocations)
    for i, a in enumerate(out):
        if not _allocation_is_unmet(a):
            continue
        row = by_barra.get(a.barra_baseline)
        if row is None:
            continue
        gk = _group_key(row, criterios)
        if not gk or gk[0] == "__sku__":
            continue  # sin attrs MDM → no Grupo que sustituya

        candidates = _offers_for_group(offers, gk, criterios)
        if candidates is not None and not candidates.empty:
            rewritten = _allocation_sucedaneo_from_offers(
                line_baseline=a,
                catalog_row=row,
                candidates=candidates,
                knobs=knobs,
                by_barra=by_barra,
            )
            if rewritten is not None:
                out[i] = rewritten
                continue

        sib_idxs = [
            j
            for j, o in enumerate(out)
            if j != i
            and not _allocation_is_unmet(o)
            and by_barra.get(o.barra_baseline) is not None
            and _group_key(by_barra[o.barra_baseline], criterios) == gk
        ]
        if not sib_idxs:
            continue

        j = max(sib_idxs, key=lambda idx: out[idx].qty_propuesto)
        sib = out[j]
        e = _elasticidad(row)
        frac = min(1.0, max(0.0, e / 5.0))
        if frac <= 0:
            # e=0: no capacidad de cesión; deja sin_oferta visible
            continue
        qty_comp = max(1, int(round(int(a.qty_baseline) * frac)))

        factors = [
            factor(
                "sucedaneo",
                f"{a.barra_baseline}→{sib.barra_propuesto} (hermano grupal en pedido)",
                datos={
                    "barra_baseline": a.barra_baseline,
                    "barra_propuesto": sib.barra_propuesto,
                },
            ),
            factor(
                "compensacion_grupo",
                f"elasticidad={e:g} → +{qty_comp} u al hermano",
                datos={
                    "elasticidad": e,
                    "frac": frac,
                    "qty_compensada": qty_comp,
                    "hermano_baseline": sib.barra_baseline,
                },
            ),
        ]
        resumen, facts = finalize(factors)
        out[i] = Allocation(
            barra_baseline=a.barra_baseline,
            desc_baseline=a.desc_baseline,
            qty_baseline=a.qty_baseline,
            barra_propuesto=sib.barra_propuesto,
            desc_propuesto=sib.desc_propuesto,
            qty_propuesto=qty_comp,
            proveedor=sib.proveedor,
            justificacion_delta=resumen,
            precio=sib.precio,
            justificacion_factores=facts,
        )
        # Compensar qty en el hermano (Propuesto agrega ambas líneas / o suma aquí)
        sib_facts = append_factor(
            sib.justificacion_factores,
            factor(
                "compensacion_grupo",
                f"+{qty_comp} u desde {a.barra_baseline} (e={e:g})",
                datos={
                    "from_barra": a.barra_baseline,
                    "qty": qty_comp,
                    "elasticidad": e,
                },
            ),
        )
        sib_resumen, sib_facts = finalize(sib_facts)
        out[j] = Allocation(
            barra_baseline=sib.barra_baseline,
            desc_baseline=sib.desc_baseline,
            qty_baseline=sib.qty_baseline,
            barra_propuesto=sib.barra_propuesto,
            desc_propuesto=sib.desc_propuesto,
            qty_propuesto=sib.qty_propuesto + qty_comp,
            proveedor=sib.proveedor,
            justificacion_delta=sib_resumen,
            extra_legs=sib.extra_legs,
            precio=sib.precio,
            justificacion_factores=sib_facts,
        )
    return out


def _allocation_sucedaneo_from_offers(
    *,
    line_baseline: Allocation,
    catalog_row,
    candidates: pd.DataFrame,
    knobs: PresetKnobs,
    by_barra: dict,
) -> Optional[Allocation]:
    """Build a buyable Allocation from group market offers (sucedáneo)."""
    line = BaselineLine(
        barra=line_baseline.barra_baseline,
        descripcion=line_baseline.desc_baseline,
        cantidad=line_baseline.qty_baseline,
    )
    scored = _score_offers(
        candidates, knobs, baseline_elasticidad=_elasticidad(catalog_row)
    )
    if scored.empty:
        return None
    chosen = scored.iloc[0]
    barra_p = str(chosen["barra"])
    if barra_p == str(line.barra):
        desc_p = line.descripcion
    else:
        desc_p = line.descripcion
        if "descripcion" in chosen.index and pd.notna(chosen.get("descripcion")):
            desc_p = str(chosen["descripcion"])
        elif barra_p in by_barra:
            desc_p = str(by_barra[barra_p]["descripcion"])

    factors: List[JustificacionFactor] = []
    if barra_p != str(line.barra):
        herm = competencia_payload(
            scored,
            baseline_barra=str(line.barra),
            elegida_barra=barra_p,
            elegida_proveedor=str(chosen.get("proveedor") or ""),
            rivales_n=int(getattr(knobs, "rivales_top_n", 3) or 3),
            hermanos_n=int(getattr(knobs, "hermanos_top_n", 3) or 3),
        )
        factors.append(
            factor(
                "sucedaneo",
                f"{line.barra}→{barra_p} (sucedáneo del Grupo)",
                datos={
                    "barra_baseline": line.barra,
                    "barra_propuesto": barra_p,
                    "hermanos_reemplazables": herm.get("hermanos_reemplazables") or [],
                    "top_n_hermanos": herm.get("top_n_hermanos"),
                },
            )
        )
    prov = str(chosen["proveedor"])
    if not prov.strip():
        return None
    precio = _offer_precio(chosen)
    oferta_f = _oferta_factor_from_chosen(
        chosen,
        scored=scored,
        baseline_barra=str(line.barra),
        knobs=knobs,
    )
    if oferta_f is not None:
        factors.append(oferta_f)
    qty = int(line.cantidad)
    qty, amp_f = _amplifier_factor(qty, chosen, knobs)
    if amp_f is not None:
        factors.append(amp_f)
    stock = chosen.get("stock_proveedor")
    if pd.notna(stock):
        qty = min(qty, int(stock))
    if qty != int(line.cantidad):
        factors.append(
            factor(
                "delta_qty",
                f"{line.cantidad}→{qty}",
                datos={"qty_baseline": line.cantidad, "qty_propuesto": qty},
            )
        )
    resumen, facts = finalize(factors)
    return Allocation(
        barra_baseline=line.barra,
        desc_baseline=line.descripcion,
        qty_baseline=line.cantidad,
        barra_propuesto=barra_p,
        desc_propuesto=desc_p,
        qty_propuesto=qty,
        proveedor=prov,
        justificacion_delta=resumen,
        precio=precio,
        justificacion_factores=facts,
    )


def _apply_kappa_split_if_needed(
    *,
    line: BaselineLine,
    row,
    chosen: pd.Series,
    barra_p: str,
    desc_p: str,
    qty_baseline: int,
    knobs: PresetKnobs,
) -> Optional[Allocation]:
    """ADR-0017: when κ active and sucedáneo wins, cap substitute qty; rest on baseline BARRA.

    Returns None when kappa is off, same BARRA, techo≥1 (full path), or techo yields 0 sub.
    """
    kappa = knobs.sust_kappa
    if kappa is None:
        return None
    try:
        kappa_f = float(kappa)
    except (TypeError, ValueError):
        return None
    if barra_p == str(line.barra):
        return None

    if knobs.max_sustitucion_base is not None:
        try:
            base = float(knobs.max_sustitucion_base)
        except (TypeError, ValueError):
            base = max_sustitucion_base_from_elasticidad(_elasticidad(row))
    else:
        base = max_sustitucion_base_from_elasticidad(_elasticidad(row))

    desvio = 0.0
    if "desvio" in chosen.index and pd.notna(chosen.get("desvio")):
        try:
            desvio = float(chosen["desvio"])
        except (TypeError, ValueError):
            desvio = 0.0

    techo = quadratic_ceiling(
        max_sustitucion_base=base,
        desvio_sucedaneo=desvio,
        kappa=kappa_f,
        amplificador_sucedaneo=1.0,
    )
    if techo >= 1.0 - 1e-12:
        return None  # full substitute path (caller)

    factors: List[JustificacionFactor] = [
        factor(
            "sucedaneo",
            f"{line.barra}→{barra_p} (sucedáneo del Grupo)",
            datos={"barra_baseline": line.barra, "barra_propuesto": barra_p},
        ),
        factor(
            "kappa",
            f"κ={kappa_f:g} base={base:.2f} desvío={desvio:.3f} techo={techo:.2f}",
            datos={
                "kappa": kappa_f,
                "base": base,
                "desvio": desvio,
                "techo": techo,
            },
        ),
    ]

    qty_sub = int(qty_baseline * techo)  # floor via int trunc toward 0 for positive
    if qty_sub <= 0:
        factors.append(
            factor(
                "delta_qty",
                f"techo → 0% sucedáneo; queda {line.barra}",
                datos={"qty_baseline": qty_baseline, "qty_propuesto": qty_baseline},
            )
        )
        resumen, facts = finalize(factors)
        return Allocation(
            barra_baseline=line.barra,
            desc_baseline=line.descripcion,
            qty_baseline=line.cantidad,
            barra_propuesto=line.barra,
            desc_propuesto=line.descripcion,
            qty_propuesto=qty_baseline,
            proveedor="",
            justificacion_delta=resumen,
            justificacion_factores=facts,
        )

    qty_sub, amp_f = _amplifier_factor(qty_sub, chosen, knobs)
    if amp_f is not None:
        factors.append(amp_f)
    stock = chosen.get("stock_proveedor")
    if pd.notna(stock):
        qty_sub = min(qty_sub, int(stock))
    qty_sub = max(0, qty_sub)
    qty_rest = max(0, qty_baseline - int(qty_baseline * techo))
    pct = 100.0 * techo
    factors.append(
        factor(
            "delta_qty",
            f"{pct:.0f}% sucedáneo ({qty_sub}); resto {qty_rest} en {line.barra}",
            datos={
                "qty_sub": qty_sub,
                "qty_rest": qty_rest,
                "qty_baseline": qty_baseline,
                "pct_techo": pct,
            },
        )
    )
    precio = _offer_precio(chosen)
    if precio is not None:
        factors.append(
            factor(
                "oferta",
                f"{chosen['proveedor']} @ ${precio:g}",
                datos={
                    "proveedor": str(chosen["proveedor"]),
                    "precio": precio,
                },
            )
        )

    extras: Tuple[PropuestoLeg, ...] = ()
    if qty_rest > 0:
        extras = (
            PropuestoLeg(
                barra=line.barra,
                descripcion=line.descripcion,
                proveedor="",
                cantidad=qty_rest,
                precio=None,
            ),
        )

    resumen, facts = finalize(factors)
    return Allocation(
        barra_baseline=line.barra,
        desc_baseline=line.descripcion,
        qty_baseline=line.cantidad,
        barra_propuesto=barra_p,
        desc_propuesto=desc_p,
        qty_propuesto=qty_sub + qty_rest,
        proveedor=str(chosen["proveedor"]),
        justificacion_delta=resumen,
        extra_legs=extras,
        precio=precio,
        justificacion_factores=facts,
    )


def _apply_f5_extension(
    allocations: List[Allocation],
    baseline: Sequence[BaselineLine],
    catalog: pd.DataFrame,
    offers: pd.DataFrame,
    criterios: Sequence[str],
    by_barra: dict,
    f5_umbral: float = _F5_DESVIO_UMBRAL,
) -> List[Allocation]:
    """Reinforce only offer SKUs with Gap_ext; never boost non-offer members."""
    if "desvio" not in offers.columns:
        return allocations

    offer_barras = set(
        offers.loc[offers["desvio"] <= f5_umbral, "barra"].astype(str)
    )
    if not offer_barras:
        return allocations

    # Build miembros from baseline lines
    miembros: List[MiembroGrupo] = []
    for line in baseline:
        row = by_barra.get(line.barra)
        if row is None:
            continue
        rot = float(row.get("rotacion_mensual", 0.0) or 0.0)
        elast = _elasticidad(row)
        en_oferta = line.barra in offer_barras
        miembros.append(
            MiembroGrupo(
                barra=line.barra,
                rotacion=rot,
                elasticidad=elast,
                gap=float(line.cantidad),
                en_oferta=en_oferta,
            )
        )

    if not any(m.en_oferta for m in miembros):
        return allocations

    ext = compute_gap_extension_oferta(miembros)
    # Extra units beyond sum of offer baseline gaps, assigned only to offer lines
    offer_alloc_idxs = [
        i for i, a in enumerate(allocations) if a.barra_baseline in offer_barras
    ]
    if not offer_alloc_idxs:
        return allocations

    current_offer_qty = sum(allocations[i].qty_propuesto for i in offer_alloc_idxs)
    target = int(round(ext.gap_ext))
    extra = max(0, target - current_offer_qty)
    if extra <= 0:
        return allocations

    # Put all extra on first offer line (single-offer fixture); split later if needed
    i0 = offer_alloc_idxs[0]
    a = allocations[i0]
    new_qty = a.qty_propuesto + extra
    just = a.justificacion_delta
    f5_note = f"F5 GapExtensionOferta f={ext.f:.3f} gap_ext={ext.gap_ext:.1f}"
    just = f"{just}; {f5_note}" if just else f5_note
    f5_factor = factor(
        "f5",
        f"f={ext.f:.3f} gap_ext={ext.gap_ext:.1f} (+{extra} u)",
        datos={"f": ext.f, "gap_ext": ext.gap_ext, "extra_units": extra},
    )
    facts = append_factor(a.justificacion_factores, f5_factor)
    resumen, facts = finalize(facts)
    allocations = list(allocations)
    allocations[i0] = Allocation(
        barra_baseline=a.barra_baseline,
        desc_baseline=a.desc_baseline,
        qty_baseline=a.qty_baseline,
        barra_propuesto=a.barra_propuesto,
        desc_propuesto=a.desc_propuesto,
        qty_propuesto=new_qty,
        proveedor=a.proveedor,
        justificacion_delta=resumen,
        extra_legs=a.extra_legs,
        precio=a.precio,
        justificacion_factores=facts,
    )
    return allocations


def _try_split_lead_time(
    line: BaselineLine,
    catalog_row,
    candidates: pd.DataFrame,
    knobs: PresetKnobs,
) -> Allocation | None:
    """Return Allocation with 2+ Propuesto legs when SplitLeadTime fires."""
    if not knobs.split_lead_time_enabled:
        return None
    if candidates is None or len(candidates) < 2:
        return None
    if "lead_time_dias" not in candidates.columns:
        return None

    existen = 0.0
    rot_mensual = 0.0
    if catalog_row is not None:
        try:
            existen = float(catalog_row.get("existen", 0.0) or 0.0)
        except (TypeError, ValueError):
            existen = 0.0
        try:
            rot_mensual = float(catalog_row.get("rotacion_mensual", 0.0) or 0.0)
        except (TypeError, ValueError):
            rot_mensual = 0.0
    rot_diaria = rot_mensual / 30.0

    offer_list: List[OfferCandidate] = []
    for _, o in candidates.iterrows():
        moq_val = o.get("moq") if "moq" in candidates.columns else None
        if moq_val is not None and pd.isna(moq_val):
            moq_val = None
        elif moq_val is not None:
            moq_val = float(moq_val)
        stock = o.get("stock_proveedor")
        if stock is not None and pd.isna(stock):
            stock = None
        elif stock is not None:
            stock = float(stock)
        desc = line.descripcion
        ob = str(o.get("barra") or "")
        if ob != str(line.barra):
            if "descripcion" in o.index and pd.notna(o.get("descripcion")):
                desc = str(o["descripcion"])
        offer_list.append(
            OfferCandidate(
                proveedor=str(o["proveedor"]),
                barra=ob,
                descripcion=desc,
                lead_time_dias=float(o.get("lead_time_dias") or 0.0),
                precio=float(o.get("precio") or 0.0),
                stock_proveedor=stock,
                moq=moq_val,
            )
        )

    # Need distinct LTs for a meaningful fast vs cheap split
    lts = {o.lead_time_dias for o in offer_list}
    if len(lts) < 2:
        return None

    result = compute_split_lead_time(
        existen=existen,
        rotacion_diaria=rot_diaria,
        demanda=int(line.cantidad),
        offers=offer_list,
    )
    if not result.fired or len(result.legs) < 2:
        return None

    primary = result.legs[0]
    precio_by_key = {(o.proveedor, o.barra): o.precio for o in offer_list}
    extras = tuple(
        PropuestoLeg(
            barra=leg.barra,
            descripcion=leg.descripcion,
            proveedor=leg.proveedor,
            cantidad=leg.cantidad,
            precio=precio_by_key.get((leg.proveedor, leg.barra)),
        )
        for leg in result.legs[1:]
        if leg.cantidad > 0
    )
    total_qty = sum(leg.cantidad for leg in result.legs)
    factors: List[JustificacionFactor] = [
        factor(
            "split_lead_time",
            result.justificacion,
            datos={
                "legs": [
                    {
                        "proveedor": leg.proveedor,
                        "barra": leg.barra,
                        "cantidad": leg.cantidad,
                        "rol": leg.rol,
                    }
                    for leg in result.legs
                ]
            },
        )
    ]
    if primary.barra != line.barra:
        factors.insert(
            0,
            factor(
                "sucedaneo",
                f"{line.barra}→{primary.barra} (sucedáneo del Grupo)",
                datos={
                    "barra_baseline": line.barra,
                    "barra_propuesto": primary.barra,
                },
            ),
        )
    if total_qty != int(line.cantidad):
        factors.append(
            factor(
                "delta_qty",
                f"{line.cantidad}→{total_qty}",
                datos={
                    "qty_baseline": int(line.cantidad),
                    "qty_propuesto": total_qty,
                },
            )
        )
    resumen, facts = finalize(factors)

    return Allocation(
        barra_baseline=line.barra,
        desc_baseline=line.descripcion,
        qty_baseline=line.cantidad,
        barra_propuesto=primary.barra,
        desc_propuesto=primary.descripcion,
        qty_propuesto=total_qty,
        proveedor=primary.proveedor,
        justificacion_delta=resumen,
        extra_legs=extras,
        precio=precio_by_key.get((primary.proveedor, primary.barra)),
        justificacion_factores=facts,
    )


def _oferta_factor_from_chosen(
    chosen,
    *,
    scored: pd.DataFrame,
    baseline_barra: str,
    knobs: PresetKnobs,
) -> Optional[JustificacionFactor]:
    """Oferta factor + rivales/hermanos top-N (ADR-0022)."""
    prov = str(chosen.get("proveedor") or "")
    barra_p = str(chosen.get("barra") or "")
    precio = _offer_precio(chosen)
    score = None
    if "_score" in chosen.index and pd.notna(chosen.get("_score")):
        try:
            score = float(chosen["_score"])
        except (TypeError, ValueError):
            score = None
    if precio is None and score is None and not prov.strip():
        return None
    det_bits = [prov] if prov.strip() else []
    if precio is not None:
        det_bits.append(f"${precio:g}")
    desvio_v = None
    if "desvio" in chosen.index and pd.notna(chosen.get("desvio")):
        try:
            desvio_v = float(chosen["desvio"])
        except (TypeError, ValueError):
            desvio_v = None
    if desvio_v is not None:
        det_bits.append(f"desvío={desvio_v:+.1%}")
    media = None
    if "media_de_mediana" in chosen.index and pd.notna(chosen.get("media_de_mediana")):
        try:
            media = float(chosen["media_de_mediana"])
        except (TypeError, ValueError):
            media = None
    delta_usd = None
    if precio is not None and media is not None:
        delta_usd = precio - media
        det_bits.append(f"media hist. ${media:.4f}")
        det_bits.append(f"Δ ${delta_usd:+.4f}")
    fuente_bl = None
    if "fuente_baseline" in chosen.index and pd.notna(chosen.get("fuente_baseline")):
        fuente_bl = str(chosen.get("fuente_baseline"))
        det_bits.append(f"[{fuente_bl}]")
    if score is not None:
        det_bits.append(f"score={score:.3f}")
    comp = competencia_payload(
        scored,
        baseline_barra=baseline_barra,
        elegida_barra=barra_p,
        elegida_proveedor=prov,
        rivales_n=int(getattr(knobs, "rivales_top_n", 3) or 3),
        hermanos_n=int(getattr(knobs, "hermanos_top_n", 3) or 3),
    )
    n_riv = len(comp.get("rivales") or [])
    n_herm = len(comp.get("hermanos_reemplazables") or [])
    if n_riv > 1 or n_herm:
        det_bits.append(f"rivales={n_riv} hermanos={n_herm}")
    media_min = None
    if "media_min_diario" in chosen.index and pd.notna(chosen.get("media_min_diario")):
        try:
            media_min = float(chosen["media_min_diario"])
        except (TypeError, ValueError):
            media_min = None
    return factor(
        "oferta",
        " · ".join(det_bits) if det_bits else prov,
        datos={
            "proveedor": prov,
            "precio": precio,
            "score": score,
            "desvio": desvio_v,
            "media_de_mediana": media,
            "media_min_diario": media_min,
            "delta_vs_media_usd": round(delta_usd, 6) if delta_usd is not None else None,
            "fuente_baseline": fuente_bl,
            **comp,
        },
    )


def _offer_precio(chosen) -> Optional[float]:
    """USD unit price from scored offer row; None if missing/invalid."""
    if chosen is None:
        return None
    if "precio" not in getattr(chosen, "index", []):
        return None
    raw = chosen.get("precio")
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _elasticidad(row) -> float:
    if row is None:
        return 0.0
    val = row.get("elasticidad_demanda", 0.0) if hasattr(row, "get") else getattr(row, "elasticidad_demanda", 0.0)
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _attr_str(val) -> str:
    """Normalize MDM attr for grouping (NULL/NaN/blank → '')."""
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except (TypeError, ValueError):
        pass
    s = str(val).strip()
    if s.lower() in ("nan", "none", "<na>", "nat"):
        return ""
    return s


def _group_key(row, criterios: Sequence[str]) -> tuple:
    """Grupo MDM key; blank attrs → per-SKU singleton (same contract as PedidoBaseline).

    Without this, all rows with empty CriteriosAgrupacion share ('','',…) and one
    offer barra can appear on every Comparativa line.
    """
    vals = tuple(_attr_str(row.get(c, "")) for c in criterios)
    if not any(vals):
        barra = _attr_str(row.get("barra", ""))
        return ("__sku__", barra)
    return vals


def _enrich_offers_with_grupo(
    market_offers: pd.DataFrame,
    catalog: pd.DataFrame,
    criterios: Sequence[str],
) -> pd.DataFrame:
    offers = market_offers.copy()
    offers["barra"] = offers["barra"].astype(str)
    # Pull grupo attrs from catalog when offer lacks them
    cols = [c for c in criterios if c in catalog.columns]
    if cols:
        meta = catalog[["barra"] + cols + ([c for c in ["descripcion"] if c in catalog.columns])].drop_duplicates(
            "barra"
        )
        offers = offers.merge(meta, on="barra", how="left", suffixes=("", "_cat"))
        for c in cols:
            cat_col = f"{c}_cat"
            if cat_col in offers.columns:
                offers[c] = offers[c].fillna(offers[cat_col]) if c in offers.columns else offers[cat_col]
                offers.drop(columns=[cat_col], inplace=True, errors="ignore")
        if "descripcion_cat" in offers.columns:
            if "descripcion" not in offers.columns:
                offers["descripcion"] = offers["descripcion_cat"]
            else:
                offers["descripcion"] = offers["descripcion"].fillna(offers["descripcion_cat"])
            offers.drop(columns=["descripcion_cat"], inplace=True, errors="ignore")
    offers["precio"] = pd.to_numeric(offers["precio"], errors="coerce")
    if "lead_time_dias" in offers.columns:
        offers["lead_time_dias"] = pd.to_numeric(offers["lead_time_dias"], errors="coerce").fillna(0.0)
    else:
        offers["lead_time_dias"] = 0.0
    if "stock_proveedor" in offers.columns:
        offers["stock_proveedor"] = pd.to_numeric(offers["stock_proveedor"], errors="coerce")
    return offers


def _offers_for_group(
    offers: pd.DataFrame, group_key: tuple, criterios: Sequence[str]
) -> pd.DataFrame:
    if offers.empty:
        return offers
    offers = offers.reset_index(drop=True)
    # Blank-MDM singleton: only offers for that exact barra (no mega-group).
    if group_key and group_key[0] == "__sku__":
        barra = str(group_key[1]) if len(group_key) > 1 else ""
        matched = offers.loc[offers["barra"].astype(str) == barra].copy()
    else:
        mask = pd.Series([True] * len(offers), index=offers.index)
        for c, val in zip(criterios, group_key):
            if c not in offers.columns:
                return offers.iloc[0:0].copy()
            mask &= offers[c].fillna("").astype(str).str.strip() == str(val)
        matched = offers.loc[mask].copy()
    # Exclude zero-stock offers when stock known
    if "stock_proveedor" in matched.columns and not matched.empty:
        matched = matched[
            matched["stock_proveedor"].isna() | (matched["stock_proveedor"] > 0)
        ].copy()
    return matched


def _apply_amplifier(qty: int, chosen: pd.Series, knobs: PresetKnobs) -> int:
    """Scale qty by exponential amplifier when preset enables it and desvío exists."""
    if not knobs.amplifier_enabled or qty <= 0:
        return qty
    if "desvio" not in chosen.index or pd.isna(chosen.get("desvio")):
        return qty
    desvio = float(chosen["desvio"])
    # Guard: desvío extremo suele ser precio basura en Mercado_Vivo (ej. $2 vs media $285).
    if desvio <= -0.85 or desvio >= 5.0:
        return qty
    from .nonlinear import exponential_amplifier

    mult = exponential_amplifier(
        desvio,
        knobs.amp_a,
        knobs.amp_b,
        knobs.amp_max_increment_pct,
        knobs.amp_floor_pct,
    )
    return max(0, int(round(qty * mult)))


def _amplifier_factor(
    qty: int, chosen: pd.Series, knobs: PresetKnobs
) -> Tuple[int, Optional[JustificacionFactor]]:
    before = int(qty)
    after = _apply_amplifier(before, chosen, knobs)
    if after == before:
        return after, None
    desvio = None
    if "desvio" in chosen.index and pd.notna(chosen.get("desvio")):
        try:
            desvio = float(chosen["desvio"])
        except (TypeError, ValueError):
            desvio = None
    return after, factor(
        "amplificador",
        f"{before}→{after}"
        + (f" (desvío={desvio:.3f})" if desvio is not None else ""),
        datos={"qty_antes": before, "qty_despues": after, "desvio": desvio},
    )


def _score_offers(
    candidates: pd.DataFrame, knobs: PresetKnobs, baseline_elasticidad: float
) -> pd.DataFrame:
    """Higher score is better. Price, opportunity (desvío), and LeadTime can outweigh elasticidad."""
    df = candidates.copy()
    precio = df["precio"].fillna(df["precio"].max() + 1)
    lt = df["lead_time_dias"].fillna(0.0)

    # Soft LT weight: Conservador low → small penalty
    lt_weight = {"low": 0.15, "medium": 0.4, "high": 0.8}.get(knobs.lead_time_soft, 0.15)

    # Normalize roughly within candidate set
    precio_n = (precio - precio.min()) / (precio.max() - precio.min() + 1e-9)
    lt_n = (lt - lt.min()) / (lt.max() - lt.min() + 1e-9)

    if "desvio" in df.columns:
        desvio = pd.to_numeric(df["desvio"], errors="coerce").fillna(0.0)
        # Negative desvío (cheap vs hist) → higher opportunity score
        opp = (-desvio).clip(lower=0.0)
        opp_n = opp / (opp.max() + 1e-9) if opp.max() > 0 else opp
    else:
        opp_n = 0.0

    # Elasticidad of the *baseline* line as mild preference for staying flexible —
    # NOT sole arbiter: price (w3) / opportunity (w4) dominate per preset.
    elast_boost = 0.05 * (baseline_elasticidad / 5.0)

    df["_score"] = (
        knobs.w3_posicionamiento * (1.0 - precio_n)
        + knobs.w4 * opp_n
        + knobs.w5 * opp_n * knobs.opp_lambda * 0.1
        + lt_weight * (1.0 - lt_n)
        + elast_boost
        + knobs.w1 * 0.0
        + knobs.w2 * 0.0
    )
    return df.sort_values("_score", ascending=False)


def _justificacion(line: BaselineLine, barra_propuesto: str, qty_base: int, qty_prop: int) -> str:
    """Legacy one-liner; prefer structured factors + finalize()."""
    parts: List[str] = []
    if barra_propuesto != line.barra:
        parts.append(
            f"cambio de código {line.barra}→{barra_propuesto} (sucedáneo del Grupo)"
        )
    if qty_prop != qty_base:
        parts.append(f"delta cantidad {qty_base}→{qty_prop}")
    return "; ".join(parts)
