"""DistribucionParcial multi-factor within Grupo (ADR-0006)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

import pandas as pd

from .pedido_baseline import BaselineLine
from .presets import PresetKnobs


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


def distribute_parcial(
    baseline: Sequence[BaselineLine],
    catalog: pd.DataFrame,
    market_offers: pd.DataFrame,
    knobs: PresetKnobs,
    criterios: Sequence[str],
) -> List[Allocation]:
    """Allocate each Baseline line a partial Propuesto quota using multi-factor scores.

    Not winner-takes-all: each Baseline BARRA keeps its own qty as the quota ceiling.
    Elasticidad is one soft signal; price and LeadTime can outweigh it.
    Offers from other BARRAs in the same Grupo are allowed (sucedáneos).
    """
    cat = catalog.copy()
    cat["barra"] = cat["barra"].astype(str)
    offers = _enrich_offers_with_grupo(market_offers, cat, criterios)

    by_barra = {str(r.barra): r for _, r in cat.iterrows()}
    out: List[Allocation] = []

    for line in baseline:
        row = by_barra.get(line.barra)
        group_key = _group_key(row, criterios) if row is not None else None
        candidates = _offers_for_group(offers, group_key, criterios) if group_key else pd.DataFrame()

        if candidates.empty:
            out.append(
                Allocation(
                    barra_baseline=line.barra,
                    desc_baseline=line.descripcion,
                    qty_baseline=line.cantidad,
                    barra_propuesto=line.barra,
                    desc_propuesto=line.descripcion,
                    qty_propuesto=line.cantidad,
                    proveedor="",
                    justificacion_delta="",
                )
            )
            continue

        scored = _score_offers(candidates, knobs, baseline_elasticidad=_elasticidad(row))
        chosen = scored.iloc[0]
        qty = int(line.cantidad)
        stock = chosen.get("stock_proveedor")
        if pd.notna(stock):
            qty = min(qty, int(stock))

        barra_p = str(chosen["barra"])
        desc_p = line.descripcion
        if "descripcion" in chosen.index and pd.notna(chosen.get("descripcion")):
            desc_p = str(chosen["descripcion"])
        elif barra_p in by_barra:
            desc_p = str(by_barra[barra_p]["descripcion"])

        justificacion = _justificacion(line, barra_p, line.cantidad, qty)
        out.append(
            Allocation(
                barra_baseline=line.barra,
                desc_baseline=line.descripcion,
                qty_baseline=line.cantidad,
                barra_propuesto=barra_p,
                desc_propuesto=desc_p,
                qty_propuesto=qty,
                proveedor=str(chosen["proveedor"]),
                justificacion_delta=justificacion,
            )
        )
    return out


def _elasticidad(row) -> float:
    if row is None:
        return 0.0
    val = row.get("elasticidad_demanda", 0.0) if hasattr(row, "get") else getattr(row, "elasticidad_demanda", 0.0)
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _group_key(row, criterios: Sequence[str]) -> tuple:
    return tuple(str(row.get(c, "")) for c in criterios)


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
    mask = pd.Series([True] * len(offers))
    for c, val in zip(criterios, group_key):
        if c not in offers.columns:
            return offers.iloc[0:0]
        mask &= offers[c].astype(str) == val
    matched = offers[mask].copy()
    # Exclude zero-stock offers when stock known
    if "stock_proveedor" in matched.columns:
        matched = matched[matched["stock_proveedor"].isna() | (matched["stock_proveedor"] > 0)]
    return matched


def _score_offers(
    candidates: pd.DataFrame, knobs: PresetKnobs, baseline_elasticidad: float
) -> pd.DataFrame:
    """Higher score is better. Price and LeadTime can outweigh elasticidad."""
    df = candidates.copy()
    precio = df["precio"].fillna(df["precio"].max() + 1)
    lt = df["lead_time_dias"].fillna(0.0)

    # Soft LT weight: Conservador low → small penalty
    lt_weight = {"low": 0.15, "medium": 0.4, "high": 0.8}.get(knobs.lead_time_soft, 0.15)

    # Normalize roughly within candidate set
    precio_n = (precio - precio.min()) / (precio.max() - precio.min() + 1e-9)
    lt_n = (lt - lt.min()) / (lt.max() - lt.min() + 1e-9)

    # Elasticidad of the *baseline* line as mild preference for staying flexible —
    # NOT sole arbiter: price (w3) dominates under Conservador.
    elast_boost = 0.05 * (baseline_elasticidad / 5.0)

    df["_score"] = (
        knobs.w3_posicionamiento * (1.0 - precio_n)
        + lt_weight * (1.0 - lt_n)
        + elast_boost
        + knobs.w1 * 0.0
        + knobs.w2 * 0.0
        + knobs.w4 * 0.0
        + knobs.w5 * 0.0
    )
    return df.sort_values("_score", ascending=False)


def _justificacion(line: BaselineLine, barra_propuesto: str, qty_base: int, qty_prop: int) -> str:
    parts: List[str] = []
    if barra_propuesto != line.barra:
        parts.append(
            f"cambio de código {line.barra}→{barra_propuesto} (sucedáneo del Grupo)"
        )
    if qty_prop != qty_base:
        parts.append(f"delta cantidad {qty_base}→{qty_prop}")
    return "; ".join(parts)
