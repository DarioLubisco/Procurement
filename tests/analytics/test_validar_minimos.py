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
    assert "Validar mínimos" in new.comparativa_cantidades[0]["justificacion_delta"]
    facts = new.comparativa_cantidades[0].get("justificacion_factores") or []
    vm = next(f for f in facts if f["codigo"] == "validar_minimos")
    assert "ValidarMinimos" in vm["detalle"]
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
    assert "Validar mínimos" in new.comparativa_cantidades[0]["justificacion_delta"]
    facts = new.comparativa_cantidades[0].get("justificacion_factores") or []
    vm = next(f for f in facts if f["codigo"] == "validar_minimos")
    assert "CHEAP" in vm["detalle"]
    assert "EXPENSIVE" in vm["detalle"] or "redistribuyó" in vm["detalle"] or "rechazó" in vm["detalle"]


def test_redistribuir_parcial_deja_no_marcadas_con_lab():
    """Unchecked lines stay with lab; only barras_redistribuir move."""
    state = ValidarMinimosState(
        pedido_propuesto=[
            {"barra": "A", "descripcion": "Prod A", "proveedor": "CHEAP", "cantidad": 10},
            {"barra": "B", "descripcion": "Prod B sibling", "proveedor": "CHEAP", "cantidad": 5},
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
            },
            {
                "barra_baseline": "B",
                "desc_baseline": "Prod B sibling",
                "qty_baseline": 5,
                "barra_propuesto": "B",
                "desc_propuesto": "Prod B sibling",
                "qty_propuesto": 5,
                "justificacion_delta": "",
            },
        ],
        criterios_agrupacion=[
            "principio_activo",
            "forma_farmaceutica",
            "concentracion",
            "cantidad_presentacion",
            "contenido_neto",
        ],
    )
    # B needs its own offer for second best — use same catalog sibling group or separate
    offers = [
        {"barra": "A", "proveedor": "CHEAP", "precio": 1.0, "stock_proveedor": 100},
        {"barra": "A", "proveedor": "EXPENSIVE", "precio": 2.0, "stock_proveedor": 100},
        {"barra": "B", "proveedor": "CHEAP", "precio": 1.0, "stock_proveedor": 100},
        {"barra": "B", "proveedor": "EXPENSIVE", "precio": 2.0, "stock_proveedor": 100},
    ]
    new, orphans = reject_proveedor(
        state,
        proveedor="CHEAP",
        catalog_rows=_catalog(),
        market_offers=offers,
        barras_redistribuir=["A"],
    )
    by = {r["barra"]: r for r in new.pedido_propuesto}
    assert by["A"]["proveedor"] == "EXPENSIVE"
    assert by["B"]["proveedor"] == "CHEAP"
    assert orphans == []


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
    assert panel["reemplazos"][0]["proveedor_actual"] == "CHEAP"
    assert panel["reemplazos"][0]["delta_pct"] == -100.0  # 1→2: (1-2)/1 = -100%
    # CHEAP is cheaper than EXPENSIVE → ahorro vs segundo is negative
    assert panel["ahorro_vs_segundo_usd"] == -10.0


def test_panel_skips_bogus_ahorro_when_precio_actual_missing():
    """Regression: prices.get(..., 0.0) made ahorro ≈ -qty*alt (looked like FX bug)."""
    state = ValidarMinimosState(
        pedido_propuesto=[
            {
                "barra": "A",
                "descripcion": "Prod A",
                "proveedor": "UNKNOWN_PROV",
                "cantidad": 1000,
            }
        ],
        comparativa_cantidades=[],
        cobertura=30.0,
        criterios_agrupacion=[
            "principio_activo",
            "forma_farmaceutica",
            "concentracion",
            "cantidad_presentacion",
            "contenido_neto",
        ],
    )
    # Only EXPENSIVE has an offer for A — UNKNOWN has no price
    offers = [
        {"barra": "A", "proveedor": "EXPENSIVE", "precio": 2.9, "stock_proveedor": 5000},
    ]
    panel = build_decision_panel(
        proveedor="UNKNOWN_PROV",
        state=state,
        catalog_rows=_catalog(),
        market_offers=offers,
        minimo_usd=50.0,
    )
    assert panel["reemplazos"]
    r0 = panel["reemplazos"][0]
    assert r0["precio_actual_missing"] is True
    assert r0["ahorro_usd"] is None
    assert r0["proveedor_actual"] == "UNKNOWN_PROV"
    assert panel["ahorro_vs_segundo_usd"] == 0.0


def test_panel_skips_ahorro_when_precio_absurd_vs_historico():
    """VITALCLINIC $2 vs media $285 → must not show Δ ≈ -$1452 vs NENA."""
    state = ValidarMinimosState(
        pedido_propuesto=[
            {
                "barra": "8904187826557",
                "descripcion": "X",
                "proveedor": "VITALCLINIC",
                "cantidad": 1,
            }
        ],
        comparativa_cantidades=[],
        cobertura=30.0,
        criterios_agrupacion=[
            "principio_activo",
            "forma_farmaceutica",
            "concentracion",
            "cantidad_presentacion",
            "contenido_neto",
        ],
    )
    offers = [
        {
            "barra": "8904187826557",
            "proveedor": "VITALCLINIC",
            "precio": 2.0,
            "desvio": -0.992991,
            "media_de_mediana": 285.337917,
            "stock_proveedor": 100,
        },
        {
            "barra": "8904187826557",
            "proveedor": "NENA",
            "precio": 1454.9,
            "desvio": 4.098867,
            "media_de_mediana": 285.337917,
            "stock_proveedor": 100,
        },
    ]
    catalog = [
        {
            "barra": "8904187826557",
            "descripcion": "X",
            "principio_activo": "x",
            "forma_farmaceutica": "tab",
            "concentracion": "1",
            "cantidad_presentacion": "1",
            "contenido_neto": "1",
        }
    ]
    panel = build_decision_panel(
        proveedor="VITALCLINIC",
        state=state,
        catalog_rows=catalog,
        market_offers=offers,
        minimo_usd=50.0,
    )
    assert panel["reemplazos"]
    r0 = panel["reemplazos"][0]
    assert r0["proveedor_alt"] == "NENA"
    assert r0["ahorro_usd"] is None
    assert r0["precio_actual_missing"] is True
    assert r0["precio_actual_invalido"] is True
    assert panel["ahorro_vs_segundo_usd"] == 0.0


def test_lookup_rejects_zero_precio():
    from analytics_engine.core.validar_minimos import _lookup_precio, _price_index

    prices = _price_index(
        [{"barra": "A", "proveedor": "P", "precio": 0.0}]
    )
    assert ("A", "P") not in prices
    assert _lookup_precio({}, "A", "P", {"precio": 0.0}) is None
    assert _lookup_precio({("A", "P"): 1.5}, "A", "P") == 1.5


def test_line_usd_case_insensitive_proveedor():
    from analytics_engine.core.validar_minimos import line_usd, _price_index

    prices = _price_index(
        [{"barra": "A", "proveedor": "Cheap", "precio": 1.0}]
    )
    assert line_usd({"barra": "A", "proveedor": "CHEAP", "cantidad": 10}, prices) == 10.0


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
    assert "Validar mínimos" in new.comparativa_cantidades[0]["justificacion_delta"]
    facts = new.comparativa_cantidades[0].get("justificacion_factores") or []
    vm = next(f for f in facts if f["codigo"] == "validar_minimos")
    assert "aceptó submínimo" in vm["detalle"]


def test_totals_by_proveedor():
    t = totals_by_proveedor(
        [{"barra": "A", "proveedor": "CHEAP", "cantidad": 16}],
        _offers(),
    )
    assert t["CHEAP"] == 16.0


def test_queue_aggregates_aliases_under_one_minimo():
    from analytics_engine.core.validar_minimos import build_deficit_queue

    groups = [
        {
            "proveedor_id": 11,
            "cod_prov": "MASTRANTO_B",
            "nombre_corto": "Mastranto",
            "monto_minimo_pedido_usd": 50.0,
            "aliases": ["MASTRANTO_B", "MASTRANTO_C"],
        }
    ]
    offers = [
        {"barra": "A", "proveedor": "MASTRANTO_B", "precio": 1.0, "stock_proveedor": 100},
        {"barra": "B", "proveedor": "MASTRANTO_C", "precio": 2.0, "stock_proveedor": 100},
    ]
    propuesto = [
        {"barra": "A", "proveedor": "MASTRANTO_B", "cantidad": 10},  # $10
        {"barra": "B", "proveedor": "MASTRANTO_C", "cantidad": 5},  # $10
    ]
    # Without aggregation would be two deficits; with aliases → one $30 deficit
    q = build_deficit_queue(
        propuesto,
        offers,
        {"MASTRANTO_B": 50.0, "MASTRANTO_C": 50.0},
        groups=groups,
    )
    assert len(q) == 1
    assert q[0].proveedor == "MASTRANTO_B"
    assert q[0].proveedor_id == 11
    assert q[0].nombre_corto == "Mastranto"
    assert q[0].total_usd == 20.0
    assert q[0].deficit_usd == 30.0


def test_reject_skips_sibling_alias_same_proveedor_id():
    from analytics_engine.core.validar_minimos import ValidarMinimosState, reject_proveedor

    groups = [
        {
            "proveedor_id": 11,
            "cod_prov": "MASTRANTO_B",
            "nombre_corto": "Mastranto",
            "monto_minimo_pedido_usd": 50.0,
            "aliases": ["MASTRANTO_B", "MASTRANTO_C"],
        }
    ]
    offers = [
        {"barra": "A", "proveedor": "MASTRANTO_B", "precio": 1.0, "stock_proveedor": 100},
        {"barra": "A", "proveedor": "MASTRANTO_C", "precio": 0.5, "stock_proveedor": 100},
        {"barra": "A", "proveedor": "OTHER", "precio": 2.0, "stock_proveedor": 100},
    ]
    state = ValidarMinimosState(
        pedido_propuesto=[
            {"barra": "A", "descripcion": "Prod A", "proveedor": "MASTRANTO_B", "cantidad": 10}
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
        proveedor="MASTRANTO_B",
        catalog_rows=_catalog(),
        market_offers=offers,
        groups=groups,
    )
    assert orphans == []
    # Must NOT pick MASTRANTO_C (sibling); next is OTHER
    assert new.pedido_propuesto[0]["proveedor"] == "OTHER"


def test_boost_touches_all_alias_cod_provs():
    from analytics_engine.core.validar_minimos import (
        ValidarMinimosState,
        apply_qty_boost,
        barras_of_proveedor,
        boost_qtys_for_barras,
    )

    groups = [
        {
            "proveedor_id": 7,
            "cod_prov": "Insuaminca",
            "nombre_corto": "Insuaminca",
            "monto_minimo_pedido_usd": 50.0,
            "aliases": ["Insuaminca", "INSUAMINCA_G"],
        }
    ]
    state = ValidarMinimosState(
        pedido_propuesto=[
            {"barra": "A", "descripcion": "A", "proveedor": "Insuaminca", "cantidad": 1},
            {"barra": "B", "descripcion": "B", "proveedor": "INSUAMINCA_G", "cantidad": 1},
        ],
        comparativa_cantidades=[],
        cobertura=30.0,
    )
    barras = barras_of_proveedor(state.pedido_propuesto, "Insuaminca", groups=groups)
    assert set(barras) == {"A", "B"}
    boost = boost_qtys_for_barras(_catalog(), barras, cobertura=30.0, pct_extra=50.0)
    new = apply_qty_boost(
        state, proveedor="Insuaminca", boost_qtys=boost, pct_extra=50.0, groups=groups
    )
    assert new.pedido_propuesto[0]["cantidad"] == 45
    assert new.pedido_propuesto[1]["cantidad"] == 45
    assert new.intentos_recalc["Insuaminca"] == 1


def test_case_insensitive_alias_resolution():
    from analytics_engine.core.validar_minimos import build_deficit_queue

    groups = [
        {
            "proveedor_id": 7,
            "cod_prov": "Insuaminca",
            "nombre_corto": "Insuaminca",
            "monto_minimo_pedido_usd": 50.0,
            "aliases": ["Insuaminca", "INSUAMINCA_G"],
        }
    ]
    offers = [
        {"barra": "A", "proveedor": "insuaminca_g", "precio": 1.0, "stock_proveedor": 10},
    ]
    propuesto = [{"barra": "A", "proveedor": "insuaminca_g", "cantidad": 5}]
    q = build_deficit_queue(propuesto, offers, {}, groups=groups)
    assert len(q) == 1
    assert q[0].proveedor == "Insuaminca"
    assert q[0].total_usd == 5.0
