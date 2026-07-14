"""PedidoBaseline — offline fixtures (ticket 01).

Seam under test: compute_pedido_baseline (legacy rot×cobertura−stock, no motor).
"""
from __future__ import annotations

import pandas as pd
import pytest

from analytics_engine.core.pedido_baseline import (
    FiltrosOperativos,
    compute_pedido_baseline,
)


def _catalog(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_baseline_qty_matches_legacy_formula_for_cobertura():
    # Independently computed: round(100 * 30 / 30 - 40) = 60
    catalog = _catalog(
        [
            {
                "barra": "111",
                "descripcion": "Paracetamol 500mg",
                "rotacion_mensual": 100.0,
                "existen": 40.0,
                "categoria": "ANALGESICOS",
                "es_generico": True,
            }
        ]
    )
    lines = compute_pedido_baseline(
        catalog,
        cobertura_dias=30.0,
        filtros=FiltrosOperativos(),
    )
    assert len(lines) == 1
    assert lines[0].barra == "111"
    assert lines[0].descripcion == "Paracetamol 500mg"
    assert lines[0].cantidad == 60
    assert not hasattr(lines[0], "proveedor") or getattr(lines[0], "proveedor", None) is None


def test_baseline_excludes_non_positive_cantidad():
    catalog = _catalog(
        [
            {
                "barra": "1",
                "descripcion": "Overstocked",
                "rotacion_mensual": 10.0,
                "existen": 100.0,
                "es_generico": True,
            },
            {
                "barra": "2",
                "descripcion": "Need",
                "rotacion_mensual": 30.0,
                "existen": 0.0,
                "es_generico": True,
            },
        ]
    )
    # round(30*15/30 - 0) = 15
    lines = compute_pedido_baseline(catalog, 15.0, FiltrosOperativos())
    assert [line.barra for line in lines] == ["2"]
    assert lines[0].cantidad == 15


def test_filtros_umbral_rotacion_and_num_rows():
    catalog = _catalog(
        [
            {
                "barra": str(i),
                "descripcion": f"P{i}",
                "rotacion_mensual": float(i),
                "existen": 0.0,
                "es_generico": True,
            }
            for i in range(1, 6)
        ]
    )
    lines = compute_pedido_baseline(
        catalog,
        cobertura_dias=30.0,
        filtros=FiltrosOperativos(umbral_rotacion=3.0, num_rows=2),
    )
    # umbral keeps rot>=3 → barras 3,4,5; num_rows keeps first 2
    assert [line.barra for line in lines] == ["3", "4"]


def test_filtros_categoria_and_genericos_only():
    catalog = _catalog(
        [
            {
                "barra": "G",
                "descripcion": "Gen",
                "rotacion_mensual": 20.0,
                "existen": 0.0,
                "categoria": "A",
                "es_generico": True,
            },
            {
                "barra": "B",
                "descripcion": "Brand",
                "rotacion_mensual": 20.0,
                "existen": 0.0,
                "categoria": "A",
                "es_generico": False,
            },
            {
                "barra": "X",
                "descripcion": "Other cat",
                "rotacion_mensual": 20.0,
                "existen": 0.0,
                "categoria": "Z",
                "es_generico": True,
            },
        ]
    )
    lines = compute_pedido_baseline(
        catalog,
        cobertura_dias=30.0,
        filtros=FiltrosOperativos(
            categorias=["A"],
            include_generics=True,
            include_brands=False,
        ),
    )
    assert [line.barra for line in lines] == ["G"]


def test_criterios_agrupacion_aggregate_rotacion_and_stock():
    # Two SKUs same grupo: rot 10+20=30, stock 5+1=6 → qty round(30*30/30 - 6)=24 each
    catalog = _catalog(
        [
            {
                "barra": "A1",
                "descripcion": "A1",
                "rotacion_mensual": 10.0,
                "existen": 5.0,
                "principio_activo": "PA1",
                "forma_farmaceutica": "TAB",
                "es_generico": True,
            },
            {
                "barra": "A2",
                "descripcion": "A2",
                "rotacion_mensual": 20.0,
                "existen": 1.0,
                "principio_activo": "PA1",
                "forma_farmaceutica": "TAB",
                "es_generico": True,
            },
        ]
    )
    lines = compute_pedido_baseline(
        catalog,
        cobertura_dias=30.0,
        filtros=FiltrosOperativos(),
        criterios_agrupacion=["principio_activo", "forma_farmaceutica"],
    )
    by_barra = {line.barra: line.cantidad for line in lines}
    assert by_barra == {"A1": 24, "A2": 24}


def test_criterios_agrupacion_missing_columns_fail_closed():
    catalog = _catalog(
        [
            {
                "barra": "1",
                "descripcion": "X",
                "rotacion_mensual": 10.0,
                "existen": 0.0,
                "es_generico": True,
            }
        ]
    )
    with pytest.raises(ValueError, match="CriteriosAgrupacion"):
        compute_pedido_baseline(
            catalog,
            30.0,
            FiltrosOperativos(),
            criterios_agrupacion=["principio_activo"],
        )


def test_blank_mdm_attrs_fall_back_to_sku_level_need():
    """Empty CriteriosAgrupacion values must not mega-group the catalog."""
    catalog = _catalog(
        [
            {
                "barra": "LOW",
                "descripcion": "Low need",
                "rotacion_mensual": 10.0,
                "existen": 0.0,
                "principio_activo": "",
                "forma_farmaceutica": "",
                "es_generico": True,
            },
            {
                "barra": "HIGH_STOCK",
                "descripcion": "Stock kills mega-group",
                "rotacion_mensual": 5.0,
                "existen": 100.0,
                "principio_activo": "",
                "forma_farmaceutica": "",
                "es_generico": True,
            },
        ]
    )
    lines = compute_pedido_baseline(
        catalog,
        cobertura_dias=30.0,
        filtros=FiltrosOperativos(),
        criterios_agrupacion=["principio_activo", "forma_farmaceutica"],
    )
    by_barra = {line.barra: line.cantidad for line in lines}
    assert by_barra == {"LOW": 10}
    assert "HIGH_STOCK" not in by_barra


def test_partial_mdm_coverage_blank_rows_stay_sku_level():
    """Products with MDM group together; unmatched blanks stay per-SKU."""
    catalog = _catalog(
        [
            {
                "barra": "A1",
                "descripcion": "A1",
                "rotacion_mensual": 10.0,
                "existen": 0.0,
                "principio_activo": "PA1",
                "forma_farmaceutica": "TAB",
                "es_generico": True,
            },
            {
                "barra": "A2",
                "descripcion": "A2",
                "rotacion_mensual": 10.0,
                "existen": 0.0,
                "principio_activo": "PA1",
                "forma_farmaceutica": "TAB",
                "es_generico": True,
            },
            {
                "barra": "ORPHAN",
                "descripcion": "No MDM",
                "rotacion_mensual": 7.0,
                "existen": 0.0,
                "principio_activo": "",
                "forma_farmaceutica": "",
                "es_generico": True,
            },
        ]
    )
    lines = compute_pedido_baseline(
        catalog,
        cobertura_dias=30.0,
        filtros=FiltrosOperativos(),
        criterios_agrupacion=["principio_activo", "forma_farmaceutica"],
    )
    by_barra = {line.barra: line.cantidad for line in lines}
    # A1+A2 group: rot 20, stock 0 → qty 20 each
    assert by_barra["A1"] == 20
    assert by_barra["A2"] == 20
    assert by_barra["ORPHAN"] == 7


def test_baseline_has_no_motor_side_effects_on_output_shape():

    catalog = _catalog(
        [
            {
                "barra": "9",
                "descripcion": "Only shape",
                "rotacion_mensual": 12.0,
                "existen": 0.0,
                "es_generico": True,
            }
        ]
    )
    lines = compute_pedido_baseline(catalog, 30.0, FiltrosOperativos())
    assert lines[0].__dataclass_fields__.keys() == {"barra", "descripcion", "cantidad"}
