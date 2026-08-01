"""PDR helpers for Generar offer selection (ADR-0025, ADR-0026)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

from .justificacion_factores import JustificacionFactor, factor

SEMAFORO_NO_CONFIABLE = "NO_CONFIABLE"
SEMAFORO_BAJA = "BAJA"
SEMAFORO_MODERADA = "MODERADA"
SEMAFORO_ALTA = "ALTA"

_PDR_SCORE_FLOOR = 0.5
_GATE_ACTIONS = frozenset({SEMAFORO_NO_CONFIABLE, SEMAFORO_BAJA})


def normalize_semaforo(raw: Any) -> Optional[str]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip().upper()
    if not s or s in ("NAN", "NONE", "<NA>"):
        return None
    return s


def parse_pdr(raw: Any) -> Optional[float]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if v < 0 or v > 1:
        return max(0.0, min(1.0, v))
    return v


def is_no_confiable(semaforo: Optional[str]) -> bool:
    return normalize_semaforo(semaforo) == SEMAFORO_NO_CONFIABLE


def is_baja(semaforo: Optional[str]) -> bool:
    return normalize_semaforo(semaforo) == SEMAFORO_BAJA


def baja_score_multiplier(pdr: Optional[float]) -> float:
    """BAJA: score × max(0.5, pdr). Missing pdr → floor only."""
    if pdr is None:
        return _PDR_SCORE_FLOOR
    return max(_PDR_SCORE_FLOOR, float(pdr))


def should_clamp_stock(semaforo: Optional[str]) -> bool:
    """False for BAJA (stock not trusted). Fail-open when semaforo missing."""
    return not is_baja(semaforo)


def _parse_ppp(raw: Any) -> Optional[float]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _parse_stock(raw: Any) -> Optional[int]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def apply_pdr_gate(candidates: pd.DataFrame, knobs: Any) -> pd.DataFrame:
    """ADR-0026: stock≤max AND ppp<umbral → force semáforo (NO_CONFIABLE|BAJA).

    Fail-open if gate disabled, or missing ppp/stock columns/values.
    """
    if candidates is None or candidates.empty:
        return candidates
    enabled = bool(getattr(knobs, "pdr_gate_enabled", True))
    if not enabled:
        return candidates

    out = candidates.copy()
    if "ppp" not in out.columns and "peso_producto_en_proveedor" in out.columns:
        out["ppp"] = out["peso_producto_en_proveedor"]
    if "ppp" not in out.columns:
        return out

    stock_col = (
        "stock_proveedor"
        if "stock_proveedor" in out.columns
        else ("stock_disponible" if "stock_disponible" in out.columns else None)
    )
    if stock_col is None:
        return out

    try:
        stock_max = int(getattr(knobs, "pdr_gate_stock_max", 2))
    except (TypeError, ValueError):
        stock_max = 2
    try:
        umbral = float(getattr(knobs, "pdr_gate_umbral_ppp", 0.001))
    except (TypeError, ValueError):
        umbral = 0.001
    action = str(getattr(knobs, "pdr_gate_action", SEMAFORO_NO_CONFIABLE) or "").strip().upper()
    if action not in _GATE_ACTIONS:
        action = SEMAFORO_NO_CONFIABLE

    if "pdr_semaforo" not in out.columns:
        out["pdr_semaforo"] = None

    for idx in out.index:
        stock = _parse_stock(out.at[idx, stock_col])
        ppp = _parse_ppp(out.at[idx, "ppp"])
        if stock is None or ppp is None:
            continue
        if stock <= stock_max and ppp < umbral:
            cur = normalize_semaforo(out.at[idx, "pdr_semaforo"])
            if action == SEMAFORO_NO_CONFIABLE:
                out.at[idx, "pdr_semaforo"] = SEMAFORO_NO_CONFIABLE
            elif cur != SEMAFORO_NO_CONFIABLE:
                # BAJA techo: never upgrade out of NO_CONFIABLE from the view
                out.at[idx, "pdr_semaforo"] = SEMAFORO_BAJA
            out.at[idx, "pdr_gate_hit"] = True
    return out


def partition_by_pdr(
    candidates: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split offers into (eligible, excluded NO_CONFIABLE). Fail-open if no column."""
    if candidates is None or candidates.empty:
        empty = candidates.iloc[0:0].copy() if candidates is not None else pd.DataFrame()
        return empty, empty
    if "pdr_semaforo" not in candidates.columns:
        return candidates.copy(), candidates.iloc[0:0].copy()
    sem = candidates["pdr_semaforo"].map(normalize_semaforo)
    excluded_mask = sem == SEMAFORO_NO_CONFIABLE
    return candidates.loc[~excluded_mask].copy(), candidates.loc[excluded_mask].copy()


def prepare_pdr_candidates(
    candidates: pd.DataFrame,
    knobs: Any,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Apply ADR-0026 gate then ADR-0025 partition."""
    return partition_by_pdr(apply_pdr_gate(candidates, knobs))


def excluded_pdr_rows(excluded: pd.DataFrame) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if excluded is None or excluded.empty:
        return out
    for _, row in excluded.iterrows():
        prov = str(row.get("proveedor") or "").strip()
        barra = str(row.get("barra") or "").strip()
        if not prov and not barra:
            continue
        out.append(
            {
                "barra": barra,
                "proveedor": prov,
                "precio": float(row["precio"])
                if "precio" in row.index and pd.notna(row.get("precio"))
                else None,
                "pdr": parse_pdr(row.get("pdr")) if "pdr" in row.index else None,
                "pdr_semaforo": normalize_semaforo(row.get("pdr_semaforo")),
                "excluida_pdr": True,
            }
        )
    return out


def pdr_factor_for_chosen(chosen: Any) -> Optional[JustificacionFactor]:
    """Chip when elegida is BAJA (penalized / stock ignored)."""
    if chosen is None:
        return None
    get = chosen.get if hasattr(chosen, "get") else lambda k, d=None: chosen[k] if k in chosen.index else d
    sem = normalize_semaforo(get("pdr_semaforo"))
    if not is_baja(sem):
        return None
    pdr = parse_pdr(get("pdr"))
    mult = baja_score_multiplier(pdr)
    pdr_s = f"{pdr:.4f}" if pdr is not None else "—"
    detalle = (
        f"{sem} · pdr={pdr_s} · score×{mult:.2f} · stock no usado como tope"
    )
    return factor(
        "pdr",
        detalle,
        datos={
            "pdr": pdr,
            "pdr_semaforo": sem,
            "score_multiplier": mult,
            "stock_clamp": False,
            "accion": "penalizar",
        },
    )


def pdr_factor_all_excluded(
    excluded: Sequence[Dict[str, Any]],
) -> JustificacionFactor:
    n = len(excluded)
    bits = []
    for row in list(excluded)[:5]:
        prov = row.get("proveedor") or "?"
        sem = row.get("pdr_semaforo") or "NO_CONFIABLE"
        pdr = row.get("pdr")
        pdr_s = f"{pdr:.2f}" if isinstance(pdr, (int, float)) else "—"
        bits.append(f"{prov}[{sem} pdr={pdr_s}]")
    extra = f" +{n - 5}" if n > 5 else ""
    detalle = (
        f"{n} oferta(s) NO_CONFIABLE excluida(s): " + ", ".join(bits) + extra
        if bits
        else f"{n} oferta(s) NO_CONFIABLE excluida(s)"
    )
    return factor(
        "pdr",
        detalle,
        datos={
            "accion": "excluir",
            "excluidas": list(excluded),
            "n_excluidas": n,
        },
    )
