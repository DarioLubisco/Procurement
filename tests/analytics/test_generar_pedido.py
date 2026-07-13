"""generar_pedido seam — Baseline real + Propuesto/Comparativa stubs (ticket 02)."""
from __future__ import annotations

import pandas as pd

from analytics_engine.core.pedido_baseline import (
    FiltrosOperativos,
    compute_pedido_baseline,
)
from analytics_engine.core.generar_pedido import (
    NivelPerfil,
    PerfilPedido,
    PresetSencillo,
    generar_pedido,
)


def _catalog() -> pd.DataFrame:
    return pd.DataFrame(
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


def test_generar_pedido_returns_baseline_matching_calculator():
    catalog = _catalog()
    filtros = FiltrosOperativos()
    perfil = PerfilPedido(
        cobertura=30,
        criterios_agrupacion=[],
        filtros_operativos=filtros,
        nivel=NivelPerfil.SENCILLO,
        preset=PresetSencillo.CONSERVADOR,
        presupuesto_maximo=None,
    )
    expected = compute_pedido_baseline(catalog, 30.0, filtros, criterios_agrupacion=[])
    result = generar_pedido(perfil, catalog=catalog)

    assert [line.barra for line in result.pedido_baseline] == [line.barra for line in expected]
    assert [line.cantidad for line in result.pedido_baseline] == [line.cantidad for line in expected]
    assert result.pedido_baseline[0].descripcion == "Paracetamol 500mg"


def test_generar_pedido_exposes_propuesto_and_comparativa_identity_stubs():
    catalog = _catalog()
    perfil = PerfilPedido(
        cobertura=30,
        criterios_agrupacion=[],
        filtros_operativos=FiltrosOperativos(),
        nivel=NivelPerfil.SENCILLO,
        preset=PresetSencillo.CONSERVADOR,
    )
    result = generar_pedido(perfil, catalog=catalog)

    assert len(result.pedido_propuesto) == 1
    prop = result.pedido_propuesto[0]
    assert prop.barra == "111"
    assert prop.descripcion == "Paracetamol 500mg"
    assert prop.cantidad == 60
    assert prop.proveedor == ""  # stub until Conservador ticket

    assert len(result.comparativa_cantidades) == 1
    row = result.comparativa_cantidades[0]
    assert row.barra_baseline == "111"
    assert row.desc_baseline == "Paracetamol 500mg"
    assert row.qty_baseline == 60
    assert row.barra_propuesto == "111"
    assert row.desc_propuesto == "Paracetamol 500mg"
    assert row.qty_propuesto == 60
    assert row.justificacion_delta == ""


def test_perfil_pedido_accepts_sencillo_fields():
    perfil = PerfilPedido(
        cobertura=21,
        criterios_agrupacion=["principio_activo", "forma_farmaceutica"],
        filtros_operativos=FiltrosOperativos(umbral_rotacion=1.0, num_rows=100),
        nivel=NivelPerfil.SENCILLO,
        preset=PresetSencillo.NORMAL,
        presupuesto_maximo=5000.0,
    )
    assert perfil.cobertura == 21
    assert perfil.preset == PresetSencillo.NORMAL
    assert perfil.presupuesto_maximo == 5000.0
    assert perfil.nivel == NivelPerfil.SENCILLO
