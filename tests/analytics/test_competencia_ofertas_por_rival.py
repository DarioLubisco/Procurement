"""competencia_payload honors hermanos/rivales/ofertas-por-rival knobs — ticket 05."""
from __future__ import annotations

import pandas as pd

from analytics_engine.core.competencia_top_n import competencia_payload
from analytics_engine.core.distribucion_parcial import distribute_parcial
from analytics_engine.core.pedido_baseline import BaselineLine
from analytics_engine.core.presets import (
    PresetSencillo,
    apply_living_overrides,
    resolve_preset_knobs,
)


def _scored_market() -> pd.DataFrame:
    """Several proveedores with multiple offers each (same Grupo)."""
    rows = []
    # Proveedor A: 3 offers
    for i, (barra, precio, score) in enumerate(
        [("B1", 5.0, 0.9), ("B2", 5.5, 0.8), ("B3", 6.0, 0.7)]
    ):
        rows.append(
            {
                "barra": barra,
                "proveedor": "PROV_A",
                "precio": precio,
                "descripcion": f"A-{barra}",
                "_score": score,
                "desvio": -0.1,
                "lead_time_dias": 3.0,
            }
        )
    # Proveedor B: 3 offers
    for barra, precio, score in [("B1", 4.5, 0.85), ("B4", 4.8, 0.75), ("B5", 5.1, 0.65)]:
        rows.append(
            {
                "barra": barra,
                "proveedor": "PROV_B",
                "precio": precio,
                "descripcion": f"B-{barra}",
                "_score": score,
                "desvio": -0.2,
                "lead_time_dias": 5.0,
            }
        )
    # Proveedor C: 2 offers
    for barra, precio, score in [("B6", 7.0, 0.5), ("B7", 7.2, 0.4)]:
        rows.append(
            {
                "barra": barra,
                "proveedor": "PROV_C",
                "precio": precio,
                "descripcion": f"C-{barra}",
                "_score": score,
                "desvio": 0.0,
                "lead_time_dias": 2.0,
            }
        )
    # Proveedor D (4th rival candidate)
    rows.append(
        {
            "barra": "B8",
            "proveedor": "PROV_D",
            "precio": 8.0,
            "descripcion": "D-B8",
            "_score": 0.3,
            "desvio": 0.1,
            "lead_time_dias": 4.0,
        }
    )
    return pd.DataFrame(rows)


def test_competencia_payload_caps_rivales_and_ofertas_por_rival():
    scored = _scored_market()
    payload = competencia_payload(
        scored,
        baseline_barra="BASE",
        elegida_barra="B1",
        elegida_proveedor="PROV_A",
        rivales_n=2,
        hermanos_n=3,
        ofertas_por_rival=2,
    )
    assert payload["top_n_rivales"] == 2
    assert payload["ofertas_por_rival"] == 2
    assert len(payload["rivales"]) == 2
    for rival in payload["rivales"]:
        assert "ofertas" in rival
        assert len(rival["ofertas"]) <= 2
        for o in rival["ofertas"]:
            assert "descripcion" in o
            assert "proveedor" in o
            assert "precio" in o
    # PROV_A has 3 offers in market but only 2 in payload
    prov_a = next(r for r in payload["rivales"] if r["proveedor"] == "PROV_A")
    assert len(prov_a["ofertas"]) == 2


def test_competencia_payload_cardinality_changes_with_knobs():
    scored = _scored_market()
    tight = competencia_payload(
        scored,
        baseline_barra="BASE",
        elegida_barra="B1",
        elegida_proveedor="PROV_A",
        rivales_n=1,
        hermanos_n=1,
        ofertas_por_rival=1,
    )
    wide = competencia_payload(
        scored,
        baseline_barra="BASE",
        elegida_barra="B1",
        elegida_proveedor="PROV_A",
        rivales_n=3,
        hermanos_n=3,
        ofertas_por_rival=3,
    )
    assert len(tight["rivales"]) == 1
    assert len(tight["rivales"][0]["ofertas"]) == 1
    assert len(wide["rivales"]) == 3
    assert max(len(r["ofertas"]) for r in wide["rivales"]) == 3


def test_hermanos_capped_by_hermanos_top_n():
    scored = _scored_market()
    # Add sibling barras ≠ baseline with scores
    payload = competencia_payload(
        scored,
        baseline_barra="B1",
        elegida_barra="B2",
        elegida_proveedor="PROV_A",
        rivales_n=3,
        hermanos_n=2,
        ofertas_por_rival=2,
    )
    assert payload["top_n_hermanos"] == 2
    assert len(payload["hermanos_reemplazables"]) <= 2


def test_generar_pedido_embeds_ofertas_por_rival_in_comparativa_datos():
    """No second market fetch needed — ofertas live on justificacion_factores.datos."""
    catalog = pd.DataFrame(
        [
            {
                "barra": "X1",
                "descripcion": "X1",
                "rotacion_mensual": 30.0,
                "existen": 0.0,
                "elasticidad_demanda": 4.0,
                "principio_activo": "PA",
                "forma_farmaceutica": "TAB",
                "concentracion": "1",
                "cantidad_presentacion": "1",
                "contenido_neto": "1",
            },
            {
                "barra": "Y",
                "descripcion": "Y oferta",
                "rotacion_mensual": 30.0,
                "existen": 0.0,
                "elasticidad_demanda": 2.0,
                "principio_activo": "PA",
                "forma_farmaceutica": "TAB",
                "concentracion": "1",
                "cantidad_presentacion": "1",
                "contenido_neto": "1",
            },
        ]
    )
    # Multiple offers per proveedor (same LT so SplitLeadTime does not dominate)
    market = pd.DataFrame(
        [
            {
                "barra": "X1",
                "proveedor": "PX",
                "precio": 10.0,
                "stock_proveedor": 5000,
                "desvio": 0.0,
                "lead_time_dias": 5.0,
                "descripcion": "X1 PX",
            },
            {
                "barra": "Y",
                "proveedor": "PY",
                "precio": 5.0,
                "stock_proveedor": 5000,
                "desvio": -0.50,
                "lead_time_dias": 5.0,
                "descripcion": "Y PY best",
            },
            {
                "barra": "Y",
                "proveedor": "PY",
                "precio": 5.5,
                "stock_proveedor": 5000,
                "desvio": -0.40,
                "lead_time_dias": 5.0,
                "descripcion": "Y PY second",
            },
            {
                "barra": "Y",
                "proveedor": "PZ",
                "precio": 6.0,
                "stock_proveedor": 5000,
                "desvio": -0.30,
                "lead_time_dias": 5.0,
                "descripcion": "Y PZ",
            },
            {
                "barra": "Y",
                "proveedor": "PZ",
                "precio": 6.2,
                "stock_proveedor": 5000,
                "desvio": -0.25,
                "lead_time_dias": 5.0,
                "descripcion": "Y PZ2",
            },
        ]
    )
    knobs = apply_living_overrides(
        resolve_preset_knobs(PresetSencillo.NORMAL),
        {
            "rivales_top_n": 3,
            "hermanos_top_n": 3,
            "rivales_ofertas_por_rival": 2,
            "split_lead_time_enabled": False,
        },
        nivel="Avanzado",
    )
    baseline = [BaselineLine(barra="X1", descripcion="X1", cantidad=30)]
    allocs = distribute_parcial(
        baseline,
        catalog,
        market,
        knobs,
        [
            "principio_activo",
            "forma_farmaceutica",
            "concentracion",
            "cantidad_presentacion",
        ],
    )
    assert allocs
    found_ofertas = False
    for alloc in allocs:
        for f in alloc.justificacion_factores:
            rivales = (f.datos or {}).get("rivales") or []
            for r in rivales:
                if r.get("ofertas"):
                    found_ofertas = True
                    assert len(r["ofertas"]) <= 2
                    for o in r["ofertas"]:
                        assert "proveedor" in o and "precio" in o
    assert found_ofertas, "expected rivales[].ofertas on justificacion_factores.datos"
