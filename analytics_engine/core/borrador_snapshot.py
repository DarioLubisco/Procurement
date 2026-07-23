"""Snapshot helpers for BorradorPedidos Comparativa — ADR-0030."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence, Tuple


def snapshot_hash(
    comparativa: Sequence[Dict[str, Any]],
    propuesto: Sequence[Dict[str, Any]],
) -> str:
    payload = {
        "comparativa_cantidades": list(comparativa or []),
        "pedido_propuesto": list(propuesto or []),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def filter_propuesto_for_cod_prov(
    propuesto: Sequence[Dict[str, Any]],
    cod_prov: str,
    *,
    proveedor_aliases: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    """Keep propuesto lines whose proveedor matches CodProv or known aliases."""
    keys = {str(cod_prov or "").strip().upper()}
    for a in proveedor_aliases or []:
        if str(a).strip():
            keys.add(str(a).strip().upper())
    out: List[Dict[str, Any]] = []
    for row in propuesto or []:
        prov = str(row.get("proveedor") or "").strip().upper()
        if prov and prov in keys:
            out.append(dict(row))
    return out


def filter_comparativa_for_barras(
    comparativa: Sequence[Dict[str, Any]],
    barras_propuesto: Sequence[str],
) -> List[Dict[str, Any]]:
    wanted = {str(b).strip() for b in barras_propuesto if str(b).strip()}
    if not wanted:
        return []
    out: List[Dict[str, Any]] = []
    for row in comparativa or []:
        bp = str(row.get("barra_propuesto") or row.get("barra") or "").strip()
        bb = str(row.get("barra_baseline") or "").strip()
        if bp in wanted or bb in wanted:
            out.append(dict(row))
    return out


def count_desviaciones(comparativa: Sequence[Dict[str, Any]]) -> int:
    """ADR-0030: Δqty same barra, product change, or alta/baja vs Sencillo."""
    n = 0
    for row in comparativa or []:
        bb = str(row.get("barra_baseline") or "").strip()
        bp = str(row.get("barra_propuesto") or "").strip()
        try:
            qb = int(row.get("qty_baseline") or 0)
        except (TypeError, ValueError):
            qb = 0
        try:
            qp = int(row.get("qty_propuesto") or 0)
        except (TypeError, ValueError):
            qp = 0
        if not bb and bp:
            n += 1
            continue
        if bb and not bp:
            n += 1
            continue
        if bb and bp and bb != bp:
            n += 1
            continue
        if qb != qp:
            n += 1
    return n


def build_desviacion_rows(
    comparativa: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Rows that belong in the exhaustive PDF section."""
    out: List[Dict[str, Any]] = []
    for row in comparativa or []:
        bb = str(row.get("barra_baseline") or "").strip()
        bp = str(row.get("barra_propuesto") or "").strip()
        try:
            qb = int(row.get("qty_baseline") or 0)
        except (TypeError, ValueError):
            qb = 0
        try:
            qp = int(row.get("qty_propuesto") or 0)
        except (TypeError, ValueError):
            qp = 0
        reasons: List[str] = []
        if not bb and bp:
            reasons.append("alta_propuesto")
        elif bb and not bp:
            reasons.append("baja_baseline")
        elif bb and bp and bb != bp:
            reasons.append("sucedaneo")
        if qb != qp:
            reasons.append("delta_qty")
        if reasons:
            item = dict(row)
            item["desviacion_motivos"] = reasons
            out.append(item)
    return out


def dumps_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def loads_json(raw: Optional[str], default: Any = None) -> Any:
    if raw is None or raw == "":
        return default if default is not None else None
    return json.loads(raw)
