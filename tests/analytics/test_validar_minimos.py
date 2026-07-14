"""ValidarMinimosProveedor — ADR-0016 unit tests."""
from __future__ import annotations

from analytics_engine.core.validar_minimos import (
    ValidarMinimosState,
    accept_subminimo,
    apply_qty_boost,
    boost_qtys_for_barras,
    build_decision_panel,
    build_deficit_queue,
    reject_proveedor,
    totals_by_proveedor,
)


def _catalog():
    return [
        {
            "barra": "A",
            "descripcion": "Prod A",
            "rotacion_mensual": 30.0,
            "existen": 0.0,
            "principio_activo": "PA",
            "forma_farmaceutica": "TAB",
            "concentracion": "1",
            "cantidad_presentacion": "1",
            "contenido_neto": "1",
        },
        {
            "barra": "B",
            "descripcion": "Prod B sibling",
            "rotacion_mensual": 30.0,
            "existen": 0.0,
            "principio_activo": "PA",
            "forma_farmaceutica": "TAB",
            "concentracion": "1",
            "cantidad_presentacion": "1",
            "contenido_neto": "1",
        },
    ]


def _offers():
    return [
        {"barra": "A", "proveedor": "CHEAP", "precio": 1.0, "stock_proveedor": 100},
        {"barra": "A", "proveedor": "EXPENSIVE", "precio": 2.0, "stock_proveedor": 100},
        {"barra": "B", "proveedor": "ALT", "precio": 1.2, "stock_proveedor": 100},
    ]


def test_queue_orders_by_largest_deficit():
    propuesto = [
        {"barra": "A", "proveedor": "CHEAP", "cantidad": 10},  # $10
        {"barra": "A", "proveedor": "EXPENSIVE", "cantidad": 5},  # $10
    ]
    minimos = {"CHEAP": 50.0, "EXPENSIVE": 15.0}
    q = build_deficit_queue(propuesto, _offers(), minimos)
    assert [d.proveedor for d in q] == ["CHEAP", "EXPENSIVE"]
    assert q[0].deficit_usd == 40.0
    assert q[1].deficit_usd == 5.0


def test_null_minimo_skipped():
    propuesto = [{"barra": "A", "proveedor": "CHEAP", "cantidad": 1}]
    q = build_deficit_queue(propuesto, _offers(), {"CHEAP": None})
    assert q == []


def test_boost_qty_only_selected_barras():
    boost = boost_qtys_for_barras(
        _catalog(), ["A"], cobertura=30.0, pct_extra=50.0
    )
    # rot 30, cov 45 → qty = 30*45/30 - 0 = 45
    assert boost["A"] == 45
    assert "B" not in boost


def test_apply_boost_updates_propuesto_and_comparativa():
    state = ValidarMinimosState(
        pedido_propuesto=[
            {"barra": "A", "descripcion": "Prod A", "proveedor": "CHEAP", "cantidad": 30}
        ],
        comparativa_cantidades=[
            {
                "barra_baseline": "A",
                "desc_baseline": "Prod A",
                "qty_baseline": 30,
                "barra_propuesto": "A",
                "desc_propuesto": "Prod A",
                "qty_propuesto": 30,
                "justificacion_delta": "base",
            }
        ],
        cobertura=30.0,
    )
    boost = boost_qtys_for_barras(_catalog(), ["A"], cobertura=30.0, pct_extra=50.0)
    new = apply_qty_boost(state, proveedor="CHEAP", boost_qtys=boost, pct_extra=50.0)
    assert new.pedido_propuesto[0]["cantidad"] == 45
    assert new.comparativa_cantidades[0]["qty_propuesto"] == 45
    assert "ValidarMinimos" in new.comparativa_cantidades[0]["justificacion_delta"]
    assert new.intentos_recalc["CHEAP"] == 1


def test_reject_reasigns_same_barra_second_best():
    state = ValidarMinimosState(
        pedido_propuesto=[
            {"barra": "A", "descripcion": "Prod A", "proveedor": "CHEAP", "cantidad": 10}
        ],
        comparativa_cantidades=[
            {
                "barra_baseline": "A",
                "desc_baseline": "Prod A",
                "qty_baseline": 10,
                "barra_propuesto": "A",
                "desc_propuesto": "Prod A",
                "qty_propuesto": 10,
                "justificacion_delta": "",
            }
        ],
        criterios_agrupacion=[
            "principio_activo",
            "forma_farmaceutica",
            "concentracion",
            "cantidad_presentacion",
            "contenido_neto",
        ],
    )
    new, orphans = reject_proveedor(
        state,
        proveedor="CHEAP",
        catalog_rows=_catalog(),
        market_offers=_offers(),
    )
    assert orphans == []
    assert new.pedido_propuesto[0]["proveedor"] == "EXPENSIVE"
    assert new.pedido_propuesto[0]["barra"] == "A"
    assert "rechazó CHEAP" in new.comparativa_cantidades[0]["justificacion_delta"]


def test_reject_orphan_when_no_alternative():
    offers = [{"barra": "A", "proveedor": "ONLY", "precio": 1.0, "stock_proveedor": 10}]
    state = ValidarMinimosState(
        pedido_propuesto=[
            {"barra": "A", "descripcion": "Prod A", "proveedor": "ONLY", "cantidad": 5}
        ],
        comparativa_cantidades=[
            {
                "barra_baseline": "A",
                "desc_baseline": "Prod A",
                "qty_baseline": 5,
                "barra_propuesto": "A",
                "desc_propuesto": "Prod A",
                "qty_propuesto": 5,
                "justificacion_delta": "",
            }
        ],
        criterios_agrupacion=["principio_activo"],
    )
    new, orphans = reject_proveedor(
        state, proveedor="ONLY", catalog_rows=_catalog(), market_offers=offers
    )
    assert orphans == ["A"]
    assert new.pedido_propuesto[0]["proveedor"] == ""


def test_panel_includes_replacements_and_savings():
    state = ValidarMinimosState(
        pedido_propuesto=[
            {"barra": "A", "descripcion": "Prod A", "proveedor": "CHEAP", "cantidad": 10}
        ],
        comparativa_cantidades=[],
        criterios_agrupacion=[
            "principio_activo",
            "forma_farmaceutica",
            "concentracion",
            "cantidad_presentacion",
            "contenido_neto",
        ],
        intentos_recalc={"CHEAP": 1},
    )
    panel = build_decision_panel(
        proveedor="CHEAP",
        state=state,
        catalog_rows=_catalog(),
        market_offers=_offers(),
        minimo_usd=50.0,
    )
    assert panel["deficit_usd"] == 40.0
    assert panel["reemplazos"]
    assert panel["reemplazos"][0]["proveedor_alt"] == "EXPENSIVE"
    # CHEAP is cheaper than EXPENSIVE → ahorro vs segundo is negative
    assert panel["ahorro_vs_segundo_usd"] == -10.0


def test_accept_subminimo_annotates_justificacion():
    state = ValidarMinimosState(
        pedido_propuesto=[
            {"barra": "A", "descripcion": "Prod A", "proveedor": "CHEAP", "cantidad": 10}
        ],
        comparativa_cantidades=[
            {
                "barra_baseline": "A",
                "desc_baseline": "Prod A",
                "qty_baseline": 10,
                "barra_propuesto": "A",
                "desc_propuesto": "Prod A",
                "qty_propuesto": 10,
                "justificacion_delta": "x",
            }
        ],
    )
    new = accept_subminimo(
        state, proveedor="CHEAP", minimo_usd=50.0, market_offers=_offers()
    )
    assert "aceptó submínimo" in new.comparativa_cantidades[0]["justificacion_delta"]


def test_totals_by_proveedor():
    t = totals_by_proveedor(
        [{"barra": "A", "proveedor": "CHEAP", "cantidad": 16}],
        _offers(),
    )
    assert t["CHEAP"] == 16.0
