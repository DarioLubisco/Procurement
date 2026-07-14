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
    assert "código" in row_a1.justificacion_delta.lower() or "codigo" in row_a1.justificacion_delta.lower()
    prop = next(p for p in result.pedido_propuesto if p.barra == "S3")
    assert prop.proveedor == "P_S3"
    assert prop.cantidad > 0


def test_empty_catalog_dataframe_returns_empty_not_keyerror():
    """Column-less empty catalog (API inject / filtered category) must not 500."""
    perfil = PerfilPedido(
        cobertura=7,
        criterios_agrupacion=[],
        filtros_operativos=FiltrosOperativos(),
        nivel=NivelPerfil.SENCILLO,
        preset=PresetSencillo.CONSERVADOR,
    )
    result = generar_pedido(
        perfil,
        catalog=pd.DataFrame(),
        market_offers=pd.DataFrame(),
    )
    assert result.pedido_baseline == []
    assert result.pedido_propuesto == []
    assert result.comparativa_cantidades == []
