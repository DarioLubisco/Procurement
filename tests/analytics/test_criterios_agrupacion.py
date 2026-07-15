"""CriteriosAgrupacion — effective list + DemandaGrupal (ticket 03)."""
from __future__ import annotations

import pandas as pd

from analytics_engine.core.criterios_agrupacion import (
    ATRIBUTOS_VALIDOS,
    ATRIBUTOS_VALIDOS_ORDER,
    CRITERIOS_AGRUPACION_DEFAULT,
    CriteriosAgrupacionInvalid,
    compute_demanda_grupal,
    resolve_criterios_agrupacion,
)
from analytics_engine.core.generar_pedido import (
    NivelPerfil,
    PerfilPedido,
    PresetSencillo,
    generar_pedido,
)
from analytics_engine.core.pedido_baseline import FiltrosOperativos


def _catalog_two_skus_same_pa_different_presentation() -> pd.DataFrame:
    """Same PA+FF+conc; differ on cantidad_presentacion → 5-attr default splits groups."""
    return pd.DataFrame(
        [
            {
                "barra": "A1",
                "descripcion": "A 10comp",
                "rotacion_mensual": 10.0,
                "existen": 0.0,
                "es_generico": True,
                "principio_activo": "PA1",
                "forma_farmaceutica": "TAB",
                "concentracion": "500",
                "cantidad_presentacion": "10",
                "contenido_neto": "1",
            },
            {
                "barra": "A2",
                "descripcion": "A 20comp",
                "rotacion_mensual": 20.0,
                "existen": 0.0,
                "es_generico": True,
                "principio_activo": "PA1",
                "forma_farmaceutica": "TAB",
                "concentracion": "500",
                "cantidad_presentacion": "20",
                "contenido_neto": "1",
            },
        ]
    )


def test_resolve_criterios_default_is_five_attrs():
    assert resolve_criterios_agrupacion(None) == list(CRITERIOS_AGRUPACION_DEFAULT)
    assert resolve_criterios_agrupacion([]) == list(CRITERIOS_AGRUPACION_DEFAULT)
    assert len(CRITERIOS_AGRUPACION_DEFAULT) == 5
    assert CRITERIOS_AGRUPACION_DEFAULT == (
        "principio_activo",
        "forma_farmaceutica",
        "concentracion",
        "cantidad_presentacion",
        "contenido_neto",
    )


def test_resolve_criterios_override_wins():
    override = ["principio_activo", "forma_farmaceutica", "concentracion"]
    assert resolve_criterios_agrupacion(override) == override


def test_resolve_criterios_rejects_unknown_attrs():
    try:
        resolve_criterios_agrupacion(["principio_activo", "no_existe"])
        assert False, "expected CriteriosAgrupacionInvalid"
    except CriteriosAgrupacionInvalid as exc:
        assert "no_existe" in str(exc)


def test_atributos_validos_covers_default_and_extras():
    assert set(CRITERIOS_AGRUPACION_DEFAULT) <= ATRIBUTOS_VALIDOS
    assert ATRIBUTOS_VALIDOS == set(ATRIBUTOS_VALIDOS_ORDER)
    for extra in ("origen", "fabricante", "generico", "marca", "blister"):
        assert extra in ATRIBUTOS_VALIDOS


def test_generar_pedido_default_criterios_split_groups_by_presentation():
    catalog = _catalog_two_skus_same_pa_different_presentation()
    perfil = PerfilPedido(
        cobertura=30,
        criterios_agrupacion=[],  # no override → system default (5 attrs)
        filtros_operativos=FiltrosOperativos(),
        nivel=NivelPerfil.SENCILLO,
        preset=PresetSencillo.CONSERVADOR,
    )
    result = generar_pedido(perfil, catalog=catalog)
    by_barra = {line.barra: line.cantidad for line in result.pedido_baseline}
    # Separate groups under 5-attr default → each uses own rot (10 and 20)
    assert by_barra == {"A1": 10, "A2": 20}


def test_generar_pedido_three_attr_override_merges_presentation_variants():
    catalog = _catalog_two_skus_same_pa_different_presentation()
    perfil = PerfilPedido(
        cobertura=30,
        criterios_agrupacion=[
            "principio_activo",
            "forma_farmaceutica",
            "concentracion",
        ],
        filtros_operativos=FiltrosOperativos(),
        nivel=NivelPerfil.SENCILLO,
        preset=PresetSencillo.CONSERVADOR,
    )
    result = generar_pedido(perfil, catalog=catalog)
    by_barra = {line.barra: line.cantidad for line in result.pedido_baseline}
    # Merged group rot 30 → qty 30 each
    assert by_barra == {"A1": 30, "A2": 30}


def test_demanda_grupal_uses_same_effective_criterios_as_baseline():
    catalog = _catalog_two_skus_same_pa_different_presentation()
    criterios = resolve_criterios_agrupacion(None)
    demanda = compute_demanda_grupal(catalog, criterios, cobertura_dias=30.0)
    # Two groups under default 5 attrs
    assert len(demanda) == 2
    gaps = {(row["cantidad_presentacion"], int(row["gap"])) for _, row in demanda.iterrows()}
    assert gaps == {("10", 10), ("20", 20)}

    criterios3 = ["principio_activo", "forma_farmaceutica", "concentracion"]
    demanda3 = compute_demanda_grupal(catalog, criterios3, cobertura_dias=30.0)
    assert len(demanda3) == 1
    assert int(demanda3.iloc[0]["gap"]) == 30
