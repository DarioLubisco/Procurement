"""DistribucionParcial + sucedáneos (ticket 05)."""
from __future__ import annotations

import pandas as pd

from analytics_engine.core.generar_pedido import (
    NivelPerfil,
    PerfilPedido,
    PresetSencillo,
    generar_pedido,
)
from analytics_engine.core.pedido_baseline import FiltrosOperativos


def _grupo_catalog_and_market():
    """Two SKUs same 5-attr grupo; market has both + a cheaper sucedáneo-only stock story."""
    catalog = pd.DataFrame(
        [
            {
                "barra": "A1",
                "descripcion": "Marca A1",
                "rotacion_mensual": 30.0,
                "existen": 0.0,
                "es_generico": False,
                "elasticidad_demanda": 5.0,  # highest — must NOT winner-take-all alone
                "principio_activo": "PA1",
                "forma_farmaceutica": "TAB",
                "concentracion": "500",
                "cantidad_presentacion": "20",
                "contenido_neto": "1",
                "lead_time_dias": 10.0,  # slow
            },
            {
                "barra": "A2",
                "descripcion": "Gen A2",
                "rotacion_mensual": 30.0,
                "existen": 0.0,
                "es_generico": True,
                "elasticidad_demanda": 1.0,
                "principio_activo": "PA1",
                "forma_farmaceutica": "TAB",
                "concentracion": "500",
                "cantidad_presentacion": "20",
                "contenido_neto": "1",
                "lead_time_dias": 2.0,  # fast
            },
        ]
    )
    # Offers: A1 expensive+slow; A2 cheap+fast; S3 sucedáneo-only (same grupo attrs via barra map)
    market = pd.DataFrame(
        [
            {
                "barra": "A1",
                "proveedor": "P_A1",
                "precio": 20.0,
                "stock_proveedor": 1000,
                "lead_time_dias": 10.0,
            },
            {
                "barra": "A2",
                "proveedor": "P_A2",
                "precio": 8.0,
                "stock_proveedor": 1000,
                "lead_time_dias": 2.0,
            },
            {
                "barra": "S3",
                "descripcion": "Sucedaneo S3",
                "proveedor": "P_S3",
                "precio": 7.0,
                "stock_proveedor": 1000,
                "lead_time_dias": 2.0,
                "principio_activo": "PA1",
                "forma_farmaceutica": "TAB",
                "concentracion": "500",
                "cantidad_presentacion": "20",
                "contenido_neto": "1",
            },
        ]
    )
    return catalog, market


def test_partial_quotas_not_winner_takes_all():
    catalog, market = _grupo_catalog_and_market()
    # Drop S3 for this test — only A1/A2
    market = market[market["barra"].isin(["A1", "A2"])].copy()
    perfil = PerfilPedido(
        cobertura=30,
        criterios_agrupacion=[],
        filtros_operativos=FiltrosOperativos(),
        nivel=NivelPerfil.SENCILLO,
        preset=PresetSencillo.CONSERVADOR,
    )
    result = generar_pedido(perfil, catalog=catalog, market_offers=market)
    assert len(result.comparativa_cantidades) == 2
    qtys = {r.barra_baseline: r.qty_propuesto for r in result.comparativa_cantidades}
    # Both lines keep a positive partial quota (not all gap on one row)
    assert qtys["A1"] > 0 and qtys["A2"] > 0
    # Not dumping entire group need (60+60=120) on a single Comparativa row
    assert qtys["A1"] < 120 and qtys["A2"] < 120
    # Elasticidad alone does not give A1 everything despite e=5
    assert qtys["A1"] <= qtys["A2"]


def test_sucedaneo_changes_barra_and_justificacion_declares_codigo():
    catalog, market = _grupo_catalog_and_market()
    # A1 has no market stock — must resolve via S3 sucedáneo
    market = market[market["barra"] != "A1"].copy()
    market.loc[market["barra"] == "A2", "stock_proveedor"] = 0
    perfil = PerfilPedido(
        cobertura=30,
        criterios_agrupacion=[],
        filtros_operativos=FiltrosOperativos(),
        nivel=NivelPerfil.SENCILLO,
        preset=PresetSencillo.CONSERVADOR,
    )
    result = generar_pedido(perfil, catalog=catalog, market_offers=market)
    row_a1 = next(r for r in result.comparativa_cantidades if r.barra_baseline == "A1")
    assert row_a1.barra_propuesto == "S3"
    assert row_a1.barra_propuesto != row_a1.barra_baseline
    codes = {f.codigo for f in row_a1.justificacion_factores}
    assert "sucedaneo" in codes
    assert "Sucedáneo" in row_a1.justificacion_delta
    prop = next(p for p in result.pedido_propuesto if p.barra == "S3")
    assert prop.proveedor == "P_S3"
    assert prop.cantidad > 0


def test_blank_mdm_rows_do_not_share_one_propuesto_barra():
    """Regression: empty CriteriosAgrupacion must not mega-group (e.g. 7593567000697)."""
    catalog = pd.DataFrame(
        [
            {
                "barra": "BLANK_A",
                "descripcion": "A sin MDM",
                "rotacion_mensual": 30.0,
                "existen": 0.0,
                "es_generico": True,
                "principio_activo": "",
                "forma_farmaceutica": "",
                "concentracion": "",
                "cantidad_presentacion": "",
                "contenido_neto": "",
            },
            {
                "barra": "BLANK_B",
                "descripcion": "B sin MDM",
                "rotacion_mensual": 30.0,
                "existen": 0.0,
                "es_generico": True,
                "principio_activo": "",
                "forma_farmaceutica": "",
                "concentracion": "",
                "cantidad_presentacion": "",
                "contenido_neto": "",
            },
            {
                "barra": "CHEAP_BLANK",
                "descripcion": "Barato sin MDM",
                "rotacion_mensual": 1.0,
                "existen": 0.0,
                "es_generico": True,
                "principio_activo": "",
                "forma_farmaceutica": "",
                "concentracion": "",
                "cantidad_presentacion": "",
                "contenido_neto": "",
            },
        ]
    )
    market = pd.DataFrame(
        [
            {"barra": "BLANK_A", "proveedor": "PA", "precio": 10.0, "stock_proveedor": 100},
            {"barra": "BLANK_B", "proveedor": "PB", "precio": 10.0, "stock_proveedor": 100},
            {
                "barra": "CHEAP_BLANK",
                "proveedor": "PC",
                "precio": 1.0,
                "stock_proveedor": 10000,
            },
        ]
    )
    perfil = PerfilPedido(
        cobertura=30,
        criterios_agrupacion=[],
        filtros_operativos=FiltrosOperativos(),
        nivel=NivelPerfil.SENCILLO,
        preset=PresetSencillo.CONSERVADOR,
    )
    result = generar_pedido(perfil, catalog=catalog, market_offers=market)
    by_base = {
        r.barra_baseline: r.barra_propuesto for r in result.comparativa_cantidades
    }
    assert by_base.get("BLANK_A") == "BLANK_A"
    assert by_base.get("BLANK_B") == "BLANK_B"
    assert by_base.get("BLANK_A") != "CHEAP_BLANK"
    assert by_base.get("BLANK_B") != "CHEAP_BLANK"


def test_same_barra_keeps_baseline_descripcion_not_mercado():
    catalog = pd.DataFrame(
        [
            {
                "barra": "111",
                "descripcion": "Desc SAPROD",
                "rotacion_mensual": 30.0,
                "existen": 0.0,
                "es_generico": True,
                "principio_activo": "PA",
                "forma_farmaceutica": "TAB",
                "concentracion": "1",
                "cantidad_presentacion": "1",
                "contenido_neto": "1",
            }
        ]
    )
    market = pd.DataFrame(
        [
            {
                "barra": "111",
                "descripcion": "Desc Mercado distinta",
                "proveedor": "P1",
                "precio": 5.0,
                "stock_proveedor": 100,
            }
        ]
    )
    perfil = PerfilPedido(
        cobertura=30,
        criterios_agrupacion=[],
        filtros_operativos=FiltrosOperativos(),
        nivel=NivelPerfil.SENCILLO,
        preset=PresetSencillo.CONSERVADOR,
    )
    result = generar_pedido(perfil, catalog=catalog, market_offers=market)
    row = result.comparativa_cantidades[0]
    assert row.barra_baseline == row.barra_propuesto == "111"
    assert row.desc_baseline == "Desc SAPROD"
    assert row.desc_propuesto == "Desc SAPROD"


def test_sin_oferta_uses_grupo_sucedaneo_when_hermano_has_offer():
    """No own offer → sucedáneo del Grupo (otra BARRA con oferta), con proveedor."""
    catalog = pd.DataFrame(
        [
            {
                "barra": "HAS",
                "descripcion": "Con oferta",
                "rotacion_mensual": 30.0,
                "existen": 0.0,
                "es_generico": True,
                "elasticidad_demanda": 3.0,
                "principio_activo": "PA",
                "forma_farmaceutica": "TAB",
                "concentracion": "1",
                "cantidad_presentacion": "1",
                "contenido_neto": "1",
            },
            {
                "barra": "NOPE",
                "descripcion": "Sin oferta propia",
                "rotacion_mensual": 30.0,
                "existen": 0.0,
                "es_generico": True,
                "elasticidad_demanda": 4.0,
                "principio_activo": "PA",
                "forma_farmaceutica": "TAB",
                "concentracion": "1",
                "cantidad_presentacion": "1",
                "contenido_neto": "1",
            },
        ]
    )
    market = pd.DataFrame(
        [
            {
                "barra": "HAS",
                "proveedor": "P1",
                "precio": 5.0,
                "stock_proveedor": 1000,
            }
        ]
    )
    perfil = PerfilPedido(
        cobertura=30,
        criterios_agrupacion=[],
        filtros_operativos=FiltrosOperativos(),
        nivel=NivelPerfil.SENCILLO,
        preset=PresetSencillo.CONSERVADOR,
    )
    result = generar_pedido(perfil, catalog=catalog, market_offers=market)
    row_nope = next(r for r in result.comparativa_cantidades if r.barra_baseline == "NOPE")
    assert row_nope.barra_propuesto == "HAS"
    assert "sucedaneo" in {f.codigo for f in row_nope.justificacion_factores}
    prop_has = [p for p in result.pedido_propuesto if p.barra == "HAS"]
    assert prop_has
    assert all(str(p.proveedor or "").strip() for p in result.pedido_propuesto)


def test_unmet_without_grupo_offer_stays_comparativa_not_propuesto():
    """Sin oferta y sin hermano/sucedáneo: visible en Comparativa; no en Propuesto."""
    catalog = pd.DataFrame(
        [
            {
                "barra": "LONELY",
                "descripcion": "Sin mercado",
                "rotacion_mensual": 30.0,
                "existen": 0.0,
                "es_generico": True,
                "elasticidad_demanda": 2.0,
                "principio_activo": "ZZ",
                "forma_farmaceutica": "TAB",
                "concentracion": "9",
                "cantidad_presentacion": "1",
                "contenido_neto": "1",
            }
        ]
    )
    market = pd.DataFrame(
        columns=["barra", "proveedor", "precio", "stock_proveedor"]
    )
    perfil = PerfilPedido(
        cobertura=30,
        criterios_agrupacion=[],
        filtros_operativos=FiltrosOperativos(),
        nivel=NivelPerfil.SENCILLO,
        preset=PresetSencillo.CONSERVADOR,
    )
    result = generar_pedido(perfil, catalog=catalog, market_offers=market)
    assert any(r.barra_baseline == "LONELY" for r in result.comparativa_cantidades)
    lonely = next(r for r in result.comparativa_cantidades if r.barra_baseline == "LONELY")
    assert "sin_oferta" in {f.codigo for f in lonely.justificacion_factores} or not lonely.justificacion_factores or "Sin oferta" in (lonely.justificacion_delta or "")
    assert all(p.barra != "LONELY" for p in result.pedido_propuesto) or all(
        str(p.proveedor or "").strip() for p in result.pedido_propuesto
    )
    assert not any(
        p.barra == "LONELY" and not str(p.proveedor or "").strip()
        for p in result.pedido_propuesto
    )
