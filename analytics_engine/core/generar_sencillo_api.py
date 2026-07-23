"""API adapter for Generar Sencillo — serializes generar_pedido for HTTP/FE."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

from .criterios_agrupacion import CRITERIOS_AGRUPACION_DEFAULT
from .generar_pedido import (
    NivelPerfil,
    PerfilPedido,
    generar_pedido,
)
from .justificacion_factores import factors_to_dicts
from .pedido_baseline import FiltrosOperativos
from .presets import (
    PresetSencillo,
    apply_living_overrides,
    living_override_schema,
    resolve_preset_knobs,
)


def _rows_to_frame(rows: Optional[Sequence[Dict[str, Any]]]) -> Optional[pd.DataFrame]:
    if rows is None:
        return None
    if len(rows) == 0:
        return pd.DataFrame()
    return pd.DataFrame(list(rows))


def attach_input_observability_meta(
    payload: Dict[str, Any],
    *,
    catalog_rows: Sequence[Dict[str, Any]],
    market_offers_rows: Sequence[Dict[str, Any]],
    backorder_rows: Optional[Sequence[Dict[str, Any]]] = None,
    load_ms: Optional[int] = None,
    data_source: Optional[str] = None,
) -> Dict[str, Any]:
    """Enrich response meta with input sizes / load timing (ops observability)."""
    meta = payload.setdefault("meta", {})
    offers = list(market_offers_rows or [])
    barras = {
        str(r.get("barra")).strip()
        for r in offers
        if r.get("barra") is not None and str(r.get("barra")).strip()
    }
    meta["catalog_rows"] = len(catalog_rows or [])
    meta["offers_rows"] = len(offers)
    meta["offers_unique"] = len(barras)
    meta["backorder_rows"] = len(backorder_rows or [])
    if load_ms is not None:
        meta["load_ms"] = int(load_ms)
    if data_source is not None:
        meta["data_source"] = data_source
    return payload


def build_perfil_sencillo(
    *,
    cobertura: int,
    criterios_agrupacion: Optional[Sequence[str]] = None,
    categorias: Optional[Sequence[str]] = None,
    include_generics: bool = True,
    include_brands: bool = True,
    umbral_rotacion: float = 0.0,
    num_rows: int = 5000,
    preset: str = "Conservador",
    presupuesto_maximo: Optional[float] = None,
) -> PerfilPedido:
    """Map HTTP/FE Sencillo controls → PerfilPedido (nivel always Sencillo)."""
    try:
        preset_enum = PresetSencillo(preset)
    except ValueError as exc:
        raise ValueError(
            f"preset inválido: {preset!r}; use Conservador|Normal|Agresivo"
        ) from exc

    criterios = list(criterios_agrupacion) if criterios_agrupacion else []
    return PerfilPedido(
        cobertura=int(cobertura),
        criterios_agrupacion=criterios,
        filtros_operativos=FiltrosOperativos(
            categorias=list(categorias) if categorias else None,
            include_generics=bool(include_generics),
            include_brands=bool(include_brands),
            umbral_rotacion=float(umbral_rotacion),
            num_rows=int(num_rows),
        ),
        nivel=NivelPerfil.SENCILLO,
        preset=preset_enum,
        presupuesto_maximo=presupuesto_maximo,
    )


def serialize_generar_result(result) -> Dict[str, Any]:
    """JSON-friendly GenerarResult for Comparativa + Propuesto UI."""
    return {
        "pedido_baseline": [
            {
                "barra": line.barra,
                "descripcion": line.descripcion,
                "cantidad": line.cantidad,
            }
            for line in result.pedido_baseline
        ],
        "pedido_propuesto": [
            {
                "barra": line.barra,
                "descripcion": line.descripcion,
                "proveedor": line.proveedor,
                "cantidad": line.cantidad,
                "precio": line.precio,
            }
            for line in result.pedido_propuesto
        ],
        "comparativa_cantidades": [
            {
                "barra_baseline": row.barra_baseline,
                "desc_baseline": row.desc_baseline,
                "qty_baseline": row.qty_baseline,
                "barra_propuesto": row.barra_propuesto,
                "desc_propuesto": row.desc_propuesto,
                "qty_propuesto": row.qty_propuesto,
                "justificacion_delta": row.justificacion_delta,
                "justificacion_factores": factors_to_dicts(
                    getattr(row, "justificacion_factores", ()) or ()
                ),
                # ADR-0027 drawer / override key
                "proveedor": getattr(row, "proveedor", "") or "",
                "existen": float(getattr(row, "existen", 0.0) or 0.0),
                "backorder_qty": int(getattr(row, "backorder_qty", 0) or 0),
                "stock_oferta": getattr(row, "stock_oferta", None),
                "grupo_key": getattr(row, "grupo_key", "") or "",
                "grupo_sum_baseline": int(
                    getattr(row, "grupo_sum_baseline", 0) or 0
                ),
                "grupo_sum_propuesto": int(
                    getattr(row, "grupo_sum_propuesto", 0) or 0
                ),
                "extra_legs_qty": int(getattr(row, "extra_legs_qty", 0) or 0),
            }
            for row in result.comparativa_cantidades
        ],
        "meta": {
            "nivel": "Sencillo",
            "criterios_agrupacion_default": list(CRITERIOS_AGRUPACION_DEFAULT),
            "artifact_primary": "comparativa_propuesto",
            "excel_barra_cantidad": "secondary_export_only",
            "forced_includes": "deprecated_not_required",
            "subtraction_files": "contingency_only",
        },
    }


def run_generar_sencillo(
    *,
    cobertura: int,
    catalog_rows: Sequence[Dict[str, Any]],
    market_offers_rows: Sequence[Dict[str, Any]],
    criterios_agrupacion: Optional[Sequence[str]] = None,
    categorias: Optional[Sequence[str]] = None,
    include_generics: bool = True,
    include_brands: bool = True,
    umbral_rotacion: float = 0.0,
    num_rows: int = 5000,
    preset: str = "Conservador",
    presupuesto_maximo: Optional[float] = None,
    backorder_rows: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Unified Generar Sencillo path (offline-injectable catalog/offers)."""
    perfil = build_perfil_sencillo(
        cobertura=cobertura,
        criterios_agrupacion=criterios_agrupacion,
        categorias=categorias,
        include_generics=include_generics,
        include_brands=include_brands,
        umbral_rotacion=umbral_rotacion,
        num_rows=num_rows,
        preset=preset,
        presupuesto_maximo=presupuesto_maximo,
    )
    catalog = _rows_to_frame(catalog_rows)
    offers = _rows_to_frame(market_offers_rows)
    backorder = _rows_to_frame(backorder_rows)
    result = generar_pedido(
        perfil,
        catalog=catalog if catalog is not None else pd.DataFrame(),
        market_offers=offers,
        backorder=backorder,
    )
    payload = serialize_generar_result(result)
    payload["meta"]["preset"] = preset
    payload["meta"]["cobertura"] = cobertura
    payload["meta"]["criterios_agrupacion_efectivos"] = list(
        criterios_agrupacion
        if criterios_agrupacion
        else CRITERIOS_AGRUPACION_DEFAULT
    )
    return attach_input_observability_meta(
        payload,
        catalog_rows=catalog_rows,
        market_offers_rows=market_offers_rows,
        backorder_rows=backorder_rows,
    )


def build_perfil_definitivo(
    *,
    cobertura: int,
    nivel: str,
    criterios_agrupacion: Optional[Sequence[str]] = None,
    categorias: Optional[Sequence[str]] = None,
    include_generics: bool = True,
    include_brands: bool = True,
    umbral_rotacion: float = 0.0,
    num_rows: int = 5000,
    base_preset: str = "Normal",
    presupuesto_maximo: Optional[float] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> PerfilPedido:
    """Map Regenerar Definitivo controls → PerfilPedido (Intermedio|Avanzado)."""
    try:
        nivel_enum = NivelPerfil(nivel)
    except ValueError as exc:
        raise ValueError(
            f"nivel inválido para Definitivo: {nivel!r}; use Intermedio|Avanzado"
        ) from exc
    if nivel_enum is NivelPerfil.SENCILLO:
        raise ValueError(
            "Regenerar Definitivo no usa nivel Sencillo; use Generar (Sencillo) primero"
        )
    try:
        preset_enum = PresetSencillo(base_preset)
    except ValueError as exc:
        raise ValueError(
            f"base_preset inválido: {base_preset!r}; use Conservador|Normal|Agresivo"
        ) from exc

    # Validate overrides early (reject dead knobs)
    apply_living_overrides(
        resolve_preset_knobs(preset_enum),
        overrides,
        nivel=nivel_enum.value,
    )

    return PerfilPedido(
        cobertura=int(cobertura),
        criterios_agrupacion=list(criterios_agrupacion) if criterios_agrupacion else [],
        filtros_operativos=FiltrosOperativos(
            categorias=list(categorias) if categorias else None,
            include_generics=bool(include_generics),
            include_brands=bool(include_brands),
            umbral_rotacion=float(umbral_rotacion),
            num_rows=int(num_rows),
        ),
        nivel=nivel_enum,
        preset=preset_enum,
        presupuesto_maximo=presupuesto_maximo,
        overrides=dict(overrides) if overrides else None,
    )


def run_regenerar_definitivo(
    *,
    cobertura: int,
    nivel: str,
    catalog_rows: Sequence[Dict[str, Any]],
    market_offers_rows: Sequence[Dict[str, Any]],
    criterios_agrupacion: Optional[Sequence[str]] = None,
    categorias: Optional[Sequence[str]] = None,
    include_generics: bool = True,
    include_brands: bool = True,
    umbral_rotacion: float = 0.0,
    num_rows: int = 5000,
    base_preset: str = "Normal",
    presupuesto_maximo: Optional[float] = None,
    overrides: Optional[Dict[str, Any]] = None,
    backorder_rows: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Regenerar PedidoDefinitivo after Comparativa (Intermedio/Avanzado)."""
    perfil = build_perfil_definitivo(
        cobertura=cobertura,
        nivel=nivel,
        criterios_agrupacion=criterios_agrupacion,
        categorias=categorias,
        include_generics=include_generics,
        include_brands=include_brands,
        umbral_rotacion=umbral_rotacion,
        num_rows=num_rows,
        base_preset=base_preset,
        presupuesto_maximo=presupuesto_maximo,
        overrides=overrides,
    )
    catalog = _rows_to_frame(catalog_rows)
    offers = _rows_to_frame(market_offers_rows)
    backorder = _rows_to_frame(backorder_rows)
    result = generar_pedido(
        perfil,
        catalog=catalog if catalog is not None else pd.DataFrame(),
        market_offers=offers,
        backorder=backorder,
    )
    payload = serialize_generar_result(result)
    payload["meta"]["nivel"] = nivel
    payload["meta"]["phase"] = "PedidoDefinitivo"
    payload["meta"]["ux_label"] = "Regenerar Definitivo"
    payload["meta"]["base_preset"] = base_preset
    payload["meta"]["overrides_applied"] = list((overrides or {}).keys())
    payload["meta"]["living_override_schema"] = living_override_schema(nivel=nivel)
    payload["meta"]["cobertura"] = cobertura
    payload["meta"]["criterios_agrupacion_efectivos"] = list(
        criterios_agrupacion
        if criterios_agrupacion
        else CRITERIOS_AGRUPACION_DEFAULT
    )
    return attach_input_observability_meta(
        payload,
        catalog_rows=catalog_rows,
        market_offers_rows=market_offers_rows,
        backorder_rows=backorder_rows,
    )
