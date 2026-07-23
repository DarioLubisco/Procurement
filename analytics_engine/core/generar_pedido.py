"""Unified Generar seam: PedidoBaseline + PedidoPropuesto + ComparativaCantidades."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import pandas as pd

from .backorder import normalize_backorder, subtract_backorder_from_baseline
from .criterios_agrupacion import resolve_criterios_agrupacion
from .distribucion_parcial import Allocation, distribute_parcial
from .justificacion_factores import JustificacionFactor
from .pedido_baseline import (
    BaselineLine,
    FiltrosOperativos,
    compute_pedido_baseline,
)
from .presets import PresetSencillo, apply_living_overrides, resolve_preset_knobs


class NivelPerfil(str, Enum):
    SENCILLO = "Sencillo"
    INTERMEDIO = "Intermedio"
    AVANZADO = "Avanzado"


@dataclass(frozen=True)
class PerfilPedido:
    cobertura: int
    criterios_agrupacion: Sequence[str]
    filtros_operativos: FiltrosOperativos
    nivel: NivelPerfil
    preset: Optional[PresetSencillo] = None
    presupuesto_maximo: Optional[float] = None
    # Intermedio/Avanzado: living OptimizerConfig overrides (no S4/kappa)
    overrides: Optional[dict] = None


@dataclass(frozen=True)
class PropuestoLine:
    barra: str
    descripcion: str
    proveedor: str
    cantidad: int
    precio: Optional[float] = None  # USD offer; ADR-0018 / Guardar borrador


@dataclass(frozen=True)
class ComparativaRow:
    barra_baseline: str
    desc_baseline: str
    qty_baseline: int
    barra_propuesto: str
    desc_propuesto: str
    qty_propuesto: int
    justificacion_delta: str
    justificacion_factores: Tuple[JustificacionFactor, ...] = ()
    # ADR-0027: contexto drawer / override key
    proveedor: str = ""
    existen: float = 0.0
    backorder_qty: int = 0
    stock_oferta: Optional[int] = None
    grupo_key: str = ""
    grupo_sum_baseline: int = 0
    grupo_sum_propuesto: int = 0
    extra_legs_qty: int = 0  # SplitLeadTime: piernas extra fijas (ADR-0027)


@dataclass(frozen=True)
class GenerarResult:
    pedido_baseline: List[BaselineLine]
    pedido_propuesto: List[PropuestoLine]
    comparativa_cantidades: List[ComparativaRow]


def generar_pedido(
    perfil: PerfilPedido,
    *,
    catalog: pd.DataFrame,
    market_offers: Optional[pd.DataFrame] = None,
    backorder: Optional[pd.DataFrame] = None,
) -> GenerarResult:
    """Orchestrate Generar offline via injected catalog/offers/backorder (no live DB/HTTP).

    `backorder` is BARRA×cantidad from dedicated backend tables (ADR-0009). Same
    subtraction applies to Baseline and (via Baseline ceiling) Propuesto.
    """
    criterios = resolve_criterios_agrupacion(perfil.criterios_agrupacion)
    baseline = compute_pedido_baseline(
        catalog,
        cobertura_dias=float(perfil.cobertura),
        filtros=perfil.filtros_operativos,
        criterios_agrupacion=criterios,
    )
    bo_map = normalize_backorder(backorder)
    baseline = subtract_backorder_from_baseline(baseline, bo_map)

    if market_offers is None:
        propuesto, comparativa = _identity_stubs(
            baseline, catalog=catalog, bo_map=bo_map, criterios=criterios
        )
    elif perfil.nivel is NivelPerfil.SENCILLO and perfil.preset is not None:
        propuesto, comparativa = _propuesto_desde_knobs(
            resolve_preset_knobs(perfil.preset),
            baseline,
            catalog,
            market_offers,
            criterios,
            bo_map=bo_map,
        )
    elif perfil.nivel in (NivelPerfil.INTERMEDIO, NivelPerfil.AVANZADO):
        # Definitivo: base = Normal (calibrado) or last Sencillo preset, then living overrides
        base_preset = perfil.preset or PresetSencillo.NORMAL
        knobs = apply_living_overrides(
            resolve_preset_knobs(base_preset),
            perfil.overrides,
            nivel=perfil.nivel.value,
        )
        propuesto, comparativa = _propuesto_desde_knobs(
            knobs,
            baseline,
            catalog,
            market_offers,
            criterios,
            bo_map=bo_map,
        )
    else:
        propuesto, comparativa = _identity_stubs(
            baseline, catalog=catalog, bo_map=bo_map, criterios=criterios
        )

    return GenerarResult(
        pedido_baseline=baseline,
        pedido_propuesto=propuesto,
        comparativa_cantidades=comparativa,
    )


def _propuesto_desde_knobs(
    knobs,
    baseline: Sequence[BaselineLine],
    catalog: pd.DataFrame,
    market_offers: pd.DataFrame,
    criterios: Sequence[str],
    *,
    bo_map: Optional[Mapping[str, int]] = None,
) -> tuple[List[PropuestoLine], List[ComparativaRow]]:
    """PedidoPropuesto via DistribucionParcial with resolved knobs.

    Comparativa includes all Baseline lines (incl. unmet sin_oferta if no hermano/
    sucedáneo). PedidoPropuesto only lines with proveedor (comprables).
    """
    allocations = distribute_parcial(
        baseline, catalog, market_offers, knobs, criterios
    )
    propuesto: List[PropuestoLine] = []
    for alloc in allocations:
        extra_qty = sum(leg.cantidad for leg in alloc.extra_legs)
        primary_qty = alloc.qty_propuesto - extra_qty
        if primary_qty > 0 and str(alloc.proveedor or "").strip():
            propuesto.append(
                PropuestoLine(
                    barra=alloc.barra_propuesto,
                    descripcion=alloc.desc_propuesto,
                    proveedor=alloc.proveedor,
                    cantidad=primary_qty,
                    precio=alloc.precio,
                )
            )
        for leg in alloc.extra_legs:
            if leg.cantidad <= 0 or not str(leg.proveedor or "").strip():
                continue
            propuesto.append(
                PropuestoLine(
                    barra=leg.barra,
                    descripcion=leg.descripcion,
                    proveedor=leg.proveedor,
                    cantidad=leg.cantidad,
                    precio=leg.precio,
                )
            )
    comparativa = _comparativa_from_allocations(
        allocations,
        catalog=catalog,
        market_offers=market_offers,
        criterios=criterios,
        bo_map=bo_map or {},
    )
    return propuesto, comparativa


def _identity_stubs(
    baseline: Sequence[BaselineLine],
    *,
    catalog: Optional[pd.DataFrame] = None,
    bo_map: Optional[Mapping[str, int]] = None,
    criterios: Optional[Sequence[str]] = None,
) -> tuple[List[PropuestoLine], List[ComparativaRow]]:
    propuesto: List[PropuestoLine] = []
    ctx = _contexto_lookups(
        catalog if catalog is not None else pd.DataFrame(),
        None,
        criterios or (),
        bo_map or {},
    )
    # Provisional rows for grupo sum pass
    provisional: List[dict] = []
    for line in baseline:
        propuesto.append(
            PropuestoLine(
                barra=line.barra,
                descripcion=line.descripcion,
                proveedor="",
                cantidad=line.cantidad,
            )
        )
        gk = ctx.grupo_key(line.barra)
        provisional.append(
            {
                "barra_baseline": line.barra,
                "desc_baseline": line.descripcion,
                "qty_baseline": line.cantidad,
                "barra_propuesto": line.barra,
                "desc_propuesto": line.descripcion,
                "qty_propuesto": line.cantidad,
                "justificacion_delta": "",
                "justificacion_factores": (),
                "proveedor": "",
                "existen": ctx.existen(line.barra),
                "backorder_qty": ctx.backorder_qty(line.barra),
                "stock_oferta": None,
                "grupo_key": gk,
                "extra_legs_qty": 0,
            }
        )
    return propuesto, _finalize_comparativa_rows(provisional)


def _comparativa_from_allocations(
    allocations: Sequence[Allocation],
    *,
    catalog: pd.DataFrame,
    market_offers: Optional[pd.DataFrame],
    criterios: Sequence[str],
    bo_map: Mapping[str, int],
) -> List[ComparativaRow]:
    ctx = _contexto_lookups(catalog, market_offers, criterios, bo_map)
    provisional: List[dict] = []
    for alloc in allocations:
        gk = ctx.grupo_key(alloc.barra_baseline)
        extra_qty = sum(int(leg.cantidad) for leg in alloc.extra_legs)
        provisional.append(
            {
                "barra_baseline": alloc.barra_baseline,
                "desc_baseline": alloc.desc_baseline,
                "qty_baseline": alloc.qty_baseline,
                "barra_propuesto": alloc.barra_propuesto,
                "desc_propuesto": alloc.desc_propuesto,
                "qty_propuesto": alloc.qty_propuesto,
                "justificacion_delta": alloc.justificacion_delta,
                "justificacion_factores": alloc.justificacion_factores,
                "proveedor": str(alloc.proveedor or ""),
                "existen": ctx.existen(alloc.barra_baseline),
                "backorder_qty": ctx.backorder_qty(alloc.barra_baseline),
                "stock_oferta": ctx.stock_oferta(
                    alloc.barra_propuesto, str(alloc.proveedor or "")
                ),
                "grupo_key": gk,
                "extra_legs_qty": extra_qty,
            }
        )
    return _finalize_comparativa_rows(provisional)


def _finalize_comparativa_rows(provisional: Sequence[dict]) -> List[ComparativaRow]:
    sum_base: Dict[str, int] = {}
    sum_prop: Dict[str, int] = {}
    for row in provisional:
        gk = str(row.get("grupo_key") or "")
        sum_base[gk] = sum_base.get(gk, 0) + int(row.get("qty_baseline") or 0)
        sum_prop[gk] = sum_prop.get(gk, 0) + int(row.get("qty_propuesto") or 0)
    out: List[ComparativaRow] = []
    for row in provisional:
        gk = str(row.get("grupo_key") or "")
        out.append(
            ComparativaRow(
                barra_baseline=row["barra_baseline"],
                desc_baseline=row["desc_baseline"],
                qty_baseline=int(row["qty_baseline"]),
                barra_propuesto=row["barra_propuesto"],
                desc_propuesto=row["desc_propuesto"],
                qty_propuesto=int(row["qty_propuesto"]),
                justificacion_delta=row.get("justificacion_delta") or "",
                justificacion_factores=row.get("justificacion_factores") or (),
                proveedor=str(row.get("proveedor") or ""),
                existen=float(row.get("existen") or 0.0),
                backorder_qty=int(row.get("backorder_qty") or 0),
                stock_oferta=row.get("stock_oferta"),
                grupo_key=gk,
                grupo_sum_baseline=sum_base.get(gk, 0),
                grupo_sum_propuesto=sum_prop.get(gk, 0),
                extra_legs_qty=int(row.get("extra_legs_qty") or 0),
            )
        )
    return out


@dataclass(frozen=True)
class _ContextoLookups:
    _existen: Mapping[str, float]
    _bo: Mapping[str, int]
    _grupo: Mapping[str, str]
    _stock: Mapping[Tuple[str, str], int]

    def existen(self, barra: str) -> float:
        return float(self._existen.get(str(barra), 0.0))

    def backorder_qty(self, barra: str) -> int:
        return int(self._bo.get(str(barra), 0))

    def grupo_key(self, barra: str) -> str:
        return self._grupo.get(str(barra), f"barra:{barra}")

    def stock_oferta(self, barra: str, proveedor: str) -> Optional[int]:
        key = (str(barra), str(proveedor or "").strip().upper())
        if key not in self._stock:
            return None
        return int(self._stock[key])


def _contexto_lookups(
    catalog: pd.DataFrame,
    market_offers: Optional[pd.DataFrame],
    criterios: Sequence[str],
    bo_map: Mapping[str, int],
) -> _ContextoLookups:
    existen: Dict[str, float] = {}
    grupo: Dict[str, str] = {}
    if catalog is not None and not catalog.empty and "barra" in catalog.columns:
        cat = catalog.copy()
        cat["barra"] = cat["barra"].astype(str)
        if "existen" in cat.columns:
            cat["existen"] = pd.to_numeric(cat["existen"], errors="coerce").fillna(0.0)
        attrs = [c for c in criterios if c in cat.columns]
        for _, row in cat.iterrows():
            b = str(row["barra"])
            if "existen" in cat.columns:
                existen[b] = float(row.get("existen") or 0.0)
            if attrs:
                grupo[b] = "|".join(str(row.get(a) or "") for a in attrs)
            else:
                grupo[b] = f"barra:{b}"

    stock: Dict[Tuple[str, str], int] = {}
    if (
        market_offers is not None
        and not market_offers.empty
        and "barra" in market_offers.columns
        and "proveedor" in market_offers.columns
    ):
        off = market_offers.copy()
        off["barra"] = off["barra"].astype(str)
        off["proveedor"] = off["proveedor"].astype(str)
        if "stock_proveedor" in off.columns:
            off["stock_proveedor"] = pd.to_numeric(
                off["stock_proveedor"], errors="coerce"
            )
            for _, row in off.iterrows():
                st = row.get("stock_proveedor")
                if st is None or (isinstance(st, float) and pd.isna(st)):
                    continue
                key = (str(row["barra"]), str(row["proveedor"]).strip().upper())
                # Prefer first non-null; keep min if duplicates (conservative)
                prev = stock.get(key)
                val = int(st)
                stock[key] = val if prev is None else min(prev, val)

    return _ContextoLookups(
        _existen=existen,
        _bo={str(k): int(v) for k, v in bo_map.items()},
        _grupo=grupo,
        _stock=stock,
    )


def refresh_grupo_sums(comparativa: Sequence[dict]) -> List[dict]:
    """Recompute grupo_sum_* after ValidarMinimos / FE-style qty mutations (dicts)."""
    sum_base: Dict[str, int] = {}
    sum_prop: Dict[str, int] = {}
    for row in comparativa:
        gk = str(row.get("grupo_key") or "")
        sum_base[gk] = sum_base.get(gk, 0) + int(row.get("qty_baseline") or 0)
        sum_prop[gk] = sum_prop.get(gk, 0) + int(row.get("qty_propuesto") or 0)
    out: List[dict] = []
    for row in comparativa:
        r = dict(row)
        gk = str(r.get("grupo_key") or "")
        r["grupo_sum_baseline"] = sum_base.get(gk, 0)
        r["grupo_sum_propuesto"] = sum_prop.get(gk, 0)
        out.append(r)
    return out
