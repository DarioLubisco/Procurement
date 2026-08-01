"""Top-N rivales (same-group offers) and hermanos reemplazables — ADR-0022."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import pandas as pd


def _f(row, key: str, default: Optional[float] = None) -> Optional[float]:
    if key not in row.index or pd.isna(row.get(key)):
        return default
    try:
        return float(row[key])
    except (TypeError, ValueError):
        return default


def clamp_top_n(n: Any, *, default: int = 3, lo: int = 1, hi: int = 10) -> int:
    try:
        v = int(n)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def rivales_top_n(
    scored: pd.DataFrame,
    *,
    top_n: int = 3,
    elegida_barra: str = "",
    elegida_proveedor: str = "",
    ofertas_por_rival: int = 2,
) -> List[Dict[str, Any]]:
    """Top-N rivales by best offer score. Rival key = proveedor.

    Each rival includes up to `ofertas_por_rival` offers (desc, proveedor, precio)
    for the replacement modal without a second Mercado fetch. Primary flat fields
    (barra, precio, …) mirror the best offer for backward-compatible FE.
    """
    n = clamp_top_n(top_n)
    m = clamp_top_n(ofertas_por_rival, default=2)
    if scored is None or scored.empty:
        return []
    df = scored
    if "_score" in df.columns:
        df = df.sort_values("_score", ascending=False, kind="mergesort")

    elegida_b = str(elegida_barra or "").strip()
    elegida_p = str(elegida_proveedor or "").strip().upper()

    # Collect offers per proveedor (score-sorted)
    by_prov: Dict[str, List[Dict[str, Any]]] = {}
    best_score_by_prov: Dict[str, float] = {}
    for _, row in df.iterrows():
        barra = str(row.get("barra") or "").strip()
        prov = str(row.get("proveedor") or "").strip()
        if not barra or not prov:
            continue
        score = _f(row, "_score", default=float("-inf"))
        if score is None:
            score = float("-inf")
        precio = _f(row, "precio")
        offer = {
            "barra": barra,
            "proveedor": prov,
            "precio": round(precio, 4) if precio is not None else None,
            "score": round(score, 4) if score != float("-inf") else None,
            "desvio": (
                round(_f(row, "desvio"), 6) if _f(row, "desvio") is not None else None
            ),
            "lead_time_dias": (
                round(_f(row, "lead_time_dias"), 1)
                if _f(row, "lead_time_dias") is not None
                else None
            ),
            "descripcion": (
                str(row.get("descripcion"))
                if "descripcion" in row.index and pd.notna(row.get("descripcion"))
                else None
            ),
            "pdr": _f(row, "pdr"),
            "pdr_semaforo": str(row.get("pdr_semaforo")).strip().upper()
            if "pdr_semaforo" in row.index and pd.notna(row.get("pdr_semaforo"))
            else None,
            "_score": score,
        }
        bucket = by_prov.setdefault(prov, [])
        # Dedupe identical (barra, precio) within proveedor; keep score order
        key = (barra, offer["precio"])
        if any((o["barra"], o["precio"]) == key for o in bucket):
            continue
        bucket.append(offer)
        prev_best = best_score_by_prov.get(prov)
        if prev_best is None or score > prev_best:
            best_score_by_prov[prov] = score

    ranked_provs = sorted(
        by_prov.keys(),
        key=lambda p: best_score_by_prov.get(p, float("-inf")),
        reverse=True,
    )[:n]

    out: List[Dict[str, Any]] = []
    for i, prov in enumerate(ranked_provs, start=1):
        offers_full = by_prov[prov]
        offers = []
        for o in offers_full[:m]:
            offers.append(
                {
                    "barra": o["barra"],
                    "proveedor": o["proveedor"],
                    "precio": o["precio"],
                    "score": o["score"],
                    "desvio": o["desvio"],
                    "lead_time_dias": o["lead_time_dias"],
                    "descripcion": o["descripcion"],
                }
            )
        best = offers_full[0]
        out.append(
            {
                "rank": i,
                "barra": best["barra"],
                "proveedor": prov,
                "precio": best["precio"],
                "score": best["score"],
                "desvio": best["desvio"],
                "lead_time_dias": best["lead_time_dias"],
                "elegida": bool(prov.upper() == elegida_p),
                "pdr": best.get("pdr"),
                "pdr_semaforo": best.get("pdr_semaforo"),
                "ofertas": offers,
            }
        )
    return out


def hermanos_reemplazables_top_n(
    scored: pd.DataFrame,
    *,
    baseline_barra: str,
    top_n: int = 3,
) -> List[Dict[str, Any]]:
    """Best offer per sibling BARRA (≠ baseline), ranked by score, capped at top_n."""
    n = clamp_top_n(top_n)
    base = str(baseline_barra or "").strip()
    if scored is None or scored.empty or not base:
        return []
    # First pass: best row per other barra
    best_by_barra: Dict[str, Any] = {}
    for _, row in scored.iterrows():
        barra = str(row.get("barra") or "").strip()
        if not barra or barra == base:
            continue
        score = _f(row, "_score", default=float("-inf"))
        prev = best_by_barra.get(barra)
        if prev is None or (score is not None and score > prev["_score"]):
            best_by_barra[barra] = {
                "barra": barra,
                "proveedor": str(row.get("proveedor") or "").strip(),
                "precio": _f(row, "precio"),
                "score": score if score != float("-inf") else None,
                "desvio": _f(row, "desvio"),
                "lead_time_dias": _f(row, "lead_time_dias"),
                "descripcion": (
                    str(row.get("descripcion"))
                    if "descripcion" in row.index and pd.notna(row.get("descripcion"))
                    else None
                ),
                "_score": score if score is not None else float("-inf"),
            }
    ranked = sorted(
        best_by_barra.values(),
        key=lambda x: x.get("_score", float("-inf")),
        reverse=True,
    )[:n]
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(ranked, start=1):
        out.append(
            {
                "rank": i,
                "barra": item["barra"],
                "proveedor": item["proveedor"],
                "precio": round(item["precio"], 4) if item["precio"] is not None else None,
                "score": round(item["score"], 4) if item["score"] is not None else None,
                "desvio": round(item["desvio"], 6) if item["desvio"] is not None else None,
                "lead_time_dias": (
                    round(item["lead_time_dias"], 1)
                    if item["lead_time_dias"] is not None
                    else None
                ),
                "descripcion": item.get("descripcion"),
            }
        )
    return out


def best_offer_for_barra(
    scored: pd.DataFrame,
    *,
    barra: str,
) -> Optional[Dict[str, Any]]:
    """Best scored offer for a specific BARRA (used to show precio del producto reemplazado)."""
    target = str(barra or "").strip()
    if scored is None or scored.empty or not target:
        return None
    best: Optional[Dict[str, Any]] = None
    best_score = float("-inf")
    for _, row in scored.iterrows():
        b = str(row.get("barra") or "").strip()
        if b != target:
            continue
        score = _f(row, "_score", default=float("-inf"))
        if score is None:
            score = float("-inf")
        if best is not None and score <= best_score:
            continue
        best_score = score
        precio = _f(row, "precio")
        best = {
            "barra": b,
            "proveedor": str(row.get("proveedor") or "").strip(),
            "precio": round(precio, 4) if precio is not None else None,
            "score": round(score, 4) if score != float("-inf") else None,
            "desvio": (
                round(_f(row, "desvio"), 6) if _f(row, "desvio") is not None else None
            ),
            "lead_time_dias": (
                round(_f(row, "lead_time_dias"), 1)
                if _f(row, "lead_time_dias") is not None
                else None
            ),
            "descripcion": (
                str(row.get("descripcion"))
                if "descripcion" in row.index and pd.notna(row.get("descripcion"))
                else None
            ),
            "media_de_mediana": _f(row, "media_de_mediana"),
            "pdr_semaforo": str(row.get("pdr_semaforo")).strip().upper()
            if "pdr_semaforo" in row.index and pd.notna(row.get("pdr_semaforo"))
            else None,
        }
    return best


def competencia_payload(
    scored: pd.DataFrame,
    *,
    baseline_barra: str,
    elegida_barra: str,
    elegida_proveedor: str,
    rivales_n: int = 3,
    hermanos_n: int = 3,
    ofertas_por_rival: int = 2,
) -> Dict[str, Any]:
    """Compact JSON for justificacion_factores datos (Comparativa accordion / modal)."""
    ofertas_n = clamp_top_n(ofertas_por_rival, default=2)
    rivales = rivales_top_n(
        scored,
        top_n=rivales_n,
        elegida_barra=elegida_barra,
        elegida_proveedor=elegida_proveedor,
        ofertas_por_rival=ofertas_n,
    )
    hermanos = hermanos_reemplazables_top_n(
        scored, baseline_barra=baseline_barra, top_n=hermanos_n
    )
    oferta_baseline = best_offer_for_barra(scored, barra=baseline_barra)
    return {
        "top_n_rivales": clamp_top_n(rivales_n),
        "top_n_hermanos": clamp_top_n(hermanos_n),
        "ofertas_por_rival": ofertas_n,
        "rivales": rivales,
        "hermanos_reemplazables": hermanos,
        "oferta_baseline": oferta_baseline,
        "n_candidatos": int(len(scored)) if scored is not None else 0,
    }
