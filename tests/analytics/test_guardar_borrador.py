"""prepare_borradores — ADR-0018 pure logic."""
from __future__ import annotations

from analytics_engine.core.guardar_borrador import prepare_borradores, plan_to_meta


def _groups():
    return [
        {
            "proveedor_id": 7,
            "cod_prov": "Insuaminca",
            "nombre_corto": "Insuaminca",
            "monto_minimo_pedido_usd": 50.0,
            "aliases": ["Insuaminca", "INSUAMINCA_G"],
        },
        {
            "proveedor_id": 1,
            "cod_prov": "DROCERCA",
            "nombre_corto": "Drocerca",
            "monto_minimo_pedido_usd": 100.0,
            "aliases": ["DROCERCA"],
        },
    ]


def test_prepare_groups_by_canonical_and_aggregates_dup_codprod():
    plan = prepare_borradores(
        [
            {
                "barra": "A",
                "descripcion": "Prod A",
                "proveedor": "INSUAMINCA_G",
                "cantidad": 2,
                "precio": 10.0,
            },
            {
                "barra": "A",
                "descripcion": "Prod A",
                "proveedor": "Insuaminca",
                "cantidad": 3,
                "precio": 20.0,
            },
            {
                "barra": "B",
                "descripcion": "Prod B",
                "proveedor": "DROCERCA",
                "cantidad": 1,
                "precio": 5.0,
            },
        ],
        groups=_groups(),
        saprod_codprods={"A", "B"},
    )
    assert len(plan.cabeceras) == 2
    ins = next(c for c in plan.cabeceras if c.cod_prov == "Insuaminca")
    assert ins.total_lineas == 1
    assert ins.lineas[0].cantidad_propuesta == 5
    # weighted: (10*2 + 20*3) / 5 = 16
    assert ins.lineas[0].costo_calculado_usd == 16.0
    assert ins.monto_total_usd == 80.0  # 16 * 5
    dro = next(c for c in plan.cabeceras if c.cod_prov == "DROCERCA")
    assert dro.monto_total_usd == 5.0


def test_prepare_omits_unresolved_proveedor_and_missing_saprod():
    plan = prepare_borradores(
        [
            {
                "barra": "A",
                "descripcion": "A",
                "proveedor": "FANTASMA",
                "cantidad": 1,
                "precio": 1.0,
            },
            {
                "barra": "Z",
                "descripcion": "Z",
                "proveedor": "DROCERCA",
                "cantidad": 2,
                "precio": 3.0,
            },
            {
                "barra": "A",
                "descripcion": "A",
                "proveedor": "DROCERCA",
                "cantidad": 1,
                "precio": 2.0,
            },
        ],
        groups=_groups(),
        saprod_codprods={"A"},  # Z missing
    )
    assert len(plan.cabeceras) == 1
    assert plan.cabeceras[0].cod_prov == "DROCERCA"
    assert plan.cabeceras[0].total_lineas == 1
    assert any(o["motivo"] == "proveedor_no_canonico" for o in plan.proveedores_omitidos)
    assert any(o["motivo"] == "no_en_saprod" for o in plan.lineas_omitidas_saprod)


def test_prepare_attaches_parametros_json_to_each_cabecera():
    plan = prepare_borradores(
        [
            {
                "barra": "A",
                "descripcion": "A",
                "proveedor": "DROCERCA",
                "cantidad": 1,
                "precio": 2.0,
            }
        ],
        groups=_groups(),
        saprod_codprods={"A"},
        parametros={"nivel": "Intermedio", "overrides": {"sust_kappa": 5.0}},
    )
    assert plan.cabeceras[0].parametros_json
    assert '"sust_kappa": 5.0' in plan.cabeceras[0].parametros_json or '"sust_kappa":5.0' in plan.cabeceras[0].parametros_json
    assert plan.parametros["nivel"] == "Intermedio"


def test_prepare_empty_after_filters_yields_no_cabeceras():
    plan = prepare_borradores(
        [
            {
                "barra": "X",
                "descripcion": "X",
                "proveedor": "UNKNOWN",
                "cantidad": 1,
                "precio": 1.0,
            }
        ],
        groups=_groups(),
        saprod_codprods={"X"},
    )
    assert plan.cabeceras == []
    meta = plan_to_meta(plan)
    assert meta["cabeceras"] == 0
