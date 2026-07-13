"""SplitLeadTime + MOQ nullable — ADR-0014/0015 (ticket 07)."""
from __future__ import annotations

from analytics_engine.core.split_lead_time import (
    OfferCandidate,
    compute_split_lead_time,
)


def test_split_does_not_fire_when_existen_covers_rot_times_lt():
    """No forced fast minimum when Existen already covers rot×LT."""
    offers = [
        OfferCandidate(
            proveedor="FAST",
            barra="B1",
            descripcion="Prod",
            lead_time_dias=5.0,
            precio=20.0,
            stock_proveedor=100.0,
            moq=None,
        ),
        OfferCandidate(
            proveedor="CHEAP",
            barra="B1",
            descripcion="Prod",
            lead_time_dias=15.0,
            precio=10.0,
            stock_proveedor=500.0,
            moq=None,
        ),
    ]
    # rot_diaria=2, LT_fast=5 → need 10; existen=12 covers it
    result = compute_split_lead_time(
        existen=12.0,
        rotacion_diaria=2.0,
        demanda=40,
        offers=offers,
    )
    assert result.fired is False
    assert result.legs == ()


def test_split_fires_when_existen_below_rot_times_lt():
    offers = [
        OfferCandidate(
            proveedor="FAST",
            barra="B1",
            descripcion="Prod",
            lead_time_dias=5.0,
            precio=20.0,
            stock_proveedor=100.0,
            moq=None,
        ),
        OfferCandidate(
            proveedor="CHEAP",
            barra="B1",
            descripcion="Prod",
            lead_time_dias=15.0,
            precio=10.0,
            stock_proveedor=500.0,
            moq=None,
        ),
    ]
    # rot×LT = 2*5 = 10; existen=3 < 10 → fire
    result = compute_split_lead_time(
        existen=3.0,
        rotacion_diaria=2.0,
        demanda=40,
        offers=offers,
    )
    assert result.fired is True
    assert len(result.legs) == 2
    by_prov = {leg.proveedor: leg for leg in result.legs}
    assert by_prov["FAST"].cantidad == 10  # rot×LT, no MOQ
    assert by_prov["CHEAP"].cantidad == 30  # remainder
    assert "splitleadtime" in result.justificacion.lower().replace(" ", "") or (
        "split" in result.justificacion.lower() and "lead" in result.justificacion.lower()
    )


def test_fast_leg_uses_max_rot_lt_and_moq_capped_by_stock():
    offers = [
        OfferCandidate(
            proveedor="FAST",
            barra="B1",
            descripcion="Prod",
            lead_time_dias=5.0,
            precio=20.0,
            stock_proveedor=12.0,  # caps below max(rot×LT, MOQ)=15
            moq=15.0,
        ),
        OfferCandidate(
            proveedor="CHEAP",
            barra="B1",
            descripcion="Prod",
            lead_time_dias=15.0,
            precio=10.0,
            stock_proveedor=500.0,
            moq=None,
        ),
    ]
    # rot×LT=10; MOQ=15 → max=15; stock caps to 12; demanda=40 → remainder 28
    result = compute_split_lead_time(
        existen=0.0,
        rotacion_diaria=2.0,
        demanda=40,
        offers=offers,
    )
    assert result.fired is True
    by_prov = {leg.proveedor: leg for leg in result.legs}
    assert by_prov["FAST"].cantidad == 12
    assert by_prov["CHEAP"].cantidad == 28
    assert "MOQ=15" in result.justificacion
    assert "stock_proveedor" in result.justificacion.lower() or "12" in result.justificacion


def test_missing_moq_does_not_block_uses_rot_lt_only():
    offers = [
        OfferCandidate(
            proveedor="FAST",
            barra="B1",
            descripcion="Prod",
            lead_time_dias=4.0,
            precio=18.0,
            stock_proveedor=200.0,
            moq=None,
        ),
        OfferCandidate(
            proveedor="CHEAP",
            barra="B1",
            descripcion="Prod",
            lead_time_dias=20.0,
            precio=9.0,
            stock_proveedor=500.0,
            moq=None,
        ),
    ]
    result = compute_split_lead_time(
        existen=1.0,
        rotacion_diaria=3.0,
        demanda=50,
        offers=offers,
    )
    assert result.fired is True
    by_prov = {leg.proveedor: leg for leg in result.legs}
    assert by_prov["FAST"].cantidad == 12  # 3*4
    assert by_prov["CHEAP"].cantidad == 38


def test_saprod_minimo_is_never_used_as_moq():
    """Catalog ERP Minimo must not feed SplitLeadTime MOQ (ADR-0015)."""
    offers = [
        OfferCandidate(
            proveedor="FAST",
            barra="B1",
            descripcion="Prod",
            lead_time_dias=5.0,
            precio=20.0,
            stock_proveedor=100.0,
            moq=None,  # no offer MOQ
        ),
        OfferCandidate(
            proveedor="CHEAP",
            barra="B1",
            descripcion="Prod",
            lead_time_dias=15.0,
            precio=10.0,
            stock_proveedor=500.0,
            moq=None,
        ),
    ]
    result = compute_split_lead_time(
        existen=0.0,
        rotacion_diaria=2.0,
        demanda=40,
        offers=offers,
    )
    # Even if a caller had SAPROD.Minimo=99 elsewhere, OfferCandidate.moq=None → rot×LT only
    assert result.fired is True
    by_prov = {leg.proveedor: leg for leg in result.legs}
    assert by_prov["FAST"].cantidad == 10  # 2*5, not 99
    assert not hasattr(offers[0], "saprod_minimo")


def test_generar_pedido_emits_two_propuesto_lines_when_split_fires():
    """PedidoPropuesto can show 2+ lines same product / different proveedores."""
    import pandas as pd

    from analytics_engine.core.generar_pedido import (
        NivelPerfil,
        PerfilPedido,
        PresetSencillo,
        generar_pedido,
    )
    from analytics_engine.core.pedido_baseline import FiltrosOperativos

    # rot_mensual=90 → rot_diaria=3; LT_fast=5 → cover_need=15; existen=0 → fire
    # Baseline qty = 90*30/30 - 0 = 90
    catalog = pd.DataFrame(
        [
            {
                "barra": "B1",
                "descripcion": "Prod B1",
                "rotacion_mensual": 90.0,
                "existen": 0.0,
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
                "barra": "B1",
                "proveedor": "FAST",
                "precio": 20.0,
                "stock_proveedor": 1000,
                "lead_time_dias": 5.0,
            },
            {
                "barra": "B1",
                "proveedor": "CHEAP",
                "precio": 8.0,
                "stock_proveedor": 1000,
                "lead_time_dias": 20.0,
            },
        ]
    )
    perfil = PerfilPedido(
        cobertura=30,
        criterios_agrupacion=[],
        filtros_operativos=FiltrosOperativos(),
        nivel=NivelPerfil.SENCILLO,
        preset=PresetSencillo.AGRESIVO,
    )
    result = generar_pedido(perfil, catalog=catalog, market_offers=market)
    assert len(result.pedido_propuesto) >= 2
    proveedores = {p.proveedor for p in result.pedido_propuesto}
    assert "FAST" in proveedores and "CHEAP" in proveedores
    assert len(result.comparativa_cantidades) == 1
    row = result.comparativa_cantidades[0]
    assert "splitleadtime" in row.justificacion_delta.lower().replace(" ", "") or (
        "split" in row.justificacion_delta.lower()
    )
    # Comparativa qty = sum of Propuesto legs (not one-sided)
    assert row.qty_propuesto == sum(p.cantidad for p in result.pedido_propuesto)
