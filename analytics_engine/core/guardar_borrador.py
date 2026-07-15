"""Prepare BorradorPedidos from PedidoDefinitivo — ADR-0018 (pure, no DB)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set

from .validar_minimos import resolve_group


def _upper(s: str) -> str:
    return str(s or "").strip().upper()


def _as_int_qty(raw: Any) -> int:
    try:
        q = int(raw)
    except (TypeError, ValueError):
        return 0
    return q if q > 0 else 0


def _as_precio(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    try:
        p = float(raw)
    except (TypeError, ValueError):
        return None
    if p != p:  # NaN
        return None
    return p


@dataclass
class BorradorLineaPlan:
    cod_prod: str
    descrip: str
    cantidad_propuesta: int
    costo_calculado_usd: Optional[float]


@dataclass
class BorradorCabeceraPlan:
    cod_prov: str
    proveedor_id: Optional[int]
    nombre_corto: str
    lineas: List[BorradorLineaPlan] = field(default_factory=list)
    parametros_json: Optional[str] = None

    @property
    def total_lineas(self) -> int:
        return len(self.lineas)

    @property
    def total_unidades(self) -> int:
        return sum(l.cantidad_propuesta for l in self.lineas)

    @property
    def monto_total_usd(self) -> Optional[float]:
        parts = [
            (l.costo_calculado_usd * l.cantidad_propuesta)
            for l in self.lineas
            if l.costo_calculado_usd is not None
        ]
        if not parts:
            return None
        return float(sum(parts))


@dataclass
class GuardarBorradorPlan:
    cabeceras: List[BorradorCabeceraPlan]
    proveedores_omitidos: List[Dict[str, Any]] = field(default_factory=list)
    lineas_omitidas_saprod: List[Dict[str, Any]] = field(default_factory=list)
    lineas_entrada: int = 0
    parametros: Optional[Dict[str, Any]] = None


def prepare_borradores(
    pedido_propuesto: Sequence[Dict[str, Any]],
    *,
    groups: Sequence[Dict[str, Any]],
    saprod_codprods: Set[str],
    parametros: Optional[Dict[str, Any]] = None,
) -> GuardarBorradorPlan:
    """Group Definitivo lines into replaceable Borrador cabeceras (ADR-0018).

    - Resolve proveedor → canonical CodProv; omit if unresolved.
    - CodProd = barra; omit if not in saprod_codprods (case-insensitive set of CodProd).
    - Aggregate duplicate CodProd per cabecera (SUM qty; qty-weighted precio).
    - Drop cabeceras that end with 0 lines.
    - Attach the same Definitivo parametros/knobs JSON snapshot on every cabecera.
    """
    import json

    params_json: Optional[str] = None
    if parametros is not None:
        params_json = json.dumps(parametros, ensure_ascii=False, sort_keys=True)

    saprod_u = {_upper(x) for x in saprod_codprods if str(x).strip()}
    # canonical upper → first seen casing from SAPROD set (prefer exact from set)
    saprod_canon = {_upper(x): str(x).strip() for x in saprod_codprods if str(x).strip()}

    # Accumulator: cod_prov_key → {meta, lines: cod_prod_u → agg}
    buckets: Dict[str, Dict[str, Any]] = {}
    omit_prov: List[Dict[str, Any]] = []
    omit_saprod: List[Dict[str, Any]] = []
    n_in = 0

    for raw in pedido_propuesto or []:
        n_in += 1
        barra = str(raw.get("barra") or "").strip()
        proveedor = str(raw.get("proveedor") or "").strip()
        descrip = str(raw.get("descripcion") or raw.get("descrip") or "").strip()
        qty = _as_int_qty(raw.get("cantidad"))
        precio = _as_precio(raw.get("precio"))

        if not barra or qty <= 0:
            omit_saprod.append(
                {
                    "barra": barra,
                    "proveedor": proveedor,
                    "motivo": "barra_vacia_o_cantidad_invalida",
                }
            )
            continue

        group = resolve_group(proveedor, groups) if proveedor else None
        if group is None:
            omit_prov.append(
                {
                    "proveedor": proveedor or "(vacío)",
                    "barra": barra,
                    "motivo": "proveedor_no_canonico",
                }
            )
            continue

        cod_prov = str(group["cod_prov"]).strip()
        key = _upper(cod_prov)
        if key not in buckets:
            buckets[key] = {
                "cod_prov": cod_prov,
                "proveedor_id": group.get("proveedor_id"),
                "nombre_corto": str(group.get("nombre_corto") or cod_prov).strip(),
                "lines": {},  # cod_u → {cod_prod, descrip, qty, precio_w_num, precio_w_den}
            }

        barra_u = _upper(barra)
        if barra_u not in saprod_u:
            omit_saprod.append(
                {
                    "barra": barra,
                    "proveedor": proveedor,
                    "cod_prov": cod_prov,
                    "motivo": "no_en_saprod",
                }
            )
            continue

        cod_prod = saprod_canon.get(barra_u, barra)
        lines = buckets[key]["lines"]
        agg = lines.get(barra_u)
        if agg is None:
            lines[barra_u] = {
                "cod_prod": cod_prod,
                "descrip": descrip,
                "qty": qty,
                "precio_w_num": (precio * qty) if precio is not None else 0.0,
                "precio_w_den": qty if precio is not None else 0,
                "has_precio": precio is not None,
            }
        else:
            agg["qty"] += qty
            if descrip and not agg["descrip"]:
                agg["descrip"] = descrip
            if precio is not None:
                agg["precio_w_num"] += precio * qty
                agg["precio_w_den"] += qty
                agg["has_precio"] = True

    cabeceras: List[BorradorCabeceraPlan] = []
    for key in sorted(buckets.keys()):
        b = buckets[key]
        lineas: List[BorradorLineaPlan] = []
        for barra_u in sorted(b["lines"].keys()):
            agg = b["lines"][barra_u]
            costo: Optional[float] = None
            if agg["has_precio"] and agg["precio_w_den"] > 0:
                costo = float(agg["precio_w_num"] / agg["precio_w_den"])
            lineas.append(
                BorradorLineaPlan(
                    cod_prod=agg["cod_prod"],
                    descrip=agg["descrip"],
                    cantidad_propuesta=int(agg["qty"]),
                    costo_calculado_usd=costo,
                )
            )
        if not lineas:
            omit_prov.append(
                {
                    "proveedor": b["cod_prov"],
                    "motivo": "cabecera_vacia_tras_filtros",
                }
            )
            continue
        cabeceras.append(
            BorradorCabeceraPlan(
                cod_prov=b["cod_prov"],
                proveedor_id=b.get("proveedor_id"),
                nombre_corto=b["nombre_corto"],
                lineas=lineas,
                parametros_json=params_json,
            )
        )

    return GuardarBorradorPlan(
        cabeceras=cabeceras,
        proveedores_omitidos=omit_prov,
        lineas_omitidas_saprod=omit_saprod,
        lineas_entrada=n_in,
        parametros=dict(parametros) if isinstance(parametros, dict) else None,
    )


def plan_to_meta(plan: GuardarBorradorPlan) -> Dict[str, Any]:
    return {
        "cabeceras": len(plan.cabeceras),
        "lineas_entrada": plan.lineas_entrada,
        "lineas_escritas": sum(c.total_lineas for c in plan.cabeceras),
        "proveedores_omitidos": plan.proveedores_omitidos,
        "lineas_omitidas_saprod": plan.lineas_omitidas_saprod,
        "parametros": plan.parametros,
        "detalle": [
            {
                "cod_prov": c.cod_prov,
                "proveedor_id": c.proveedor_id,
                "total_lineas": c.total_lineas,
                "total_unidades": c.total_unidades,
                "monto_total_usd": c.monto_total_usd,
                "tiene_parametros": bool(c.parametros_json),
            }
            for c in plan.cabeceras
        ],
    }
