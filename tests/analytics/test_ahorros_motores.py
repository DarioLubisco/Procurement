"""Tests for compute_ahorros_motores (grill 2026-07-24)."""
from __future__ import annotations

from analytics_engine.core.ahorros_motores import compute_ahorros_motores


def test_escenario1_misma_barra_delta_qty_vs_historico():
    # Q 10→15, hist 2.0, actual 1.5 → (5)*(2-1.5)=2.5
    comp = [
        {
            "barra_baseline": "A",
            "barra_propuesto": "A",
            "qty_baseline": 10,
            "qty_propuesto": 15,
            "extra_legs_qty": 0,
            "justificacion_factores": [
                {
                    "codigo": "oferta",
                    "titulo": "Oferta",
                    "detalle": "",
                    "datos": {"precio": 1.5, "media_de_mediana": 2.0, "proveedor": "P1"},
                }
            ],
        }
    ]
    out = compute_ahorros_motores(comp, [{"barra": "A", "precio": 1.5}])
    by = {m["codigo"]: m for m in out["ahorros_motores"]}
    assert by["cantidad_vs_historico"]["usd"] == 2.5
    assert by["cantidad_vs_historico"]["n_lineas"] == 1
    assert by["sucedaneo"]["usd"] == 0.0
    assert out["ahorro_total_usd"] == 2.5
    assert out["ahorro_parcial"] is False


def test_escenario2_cambio_barra_vs_baseline_offer():
    # Q_new=8, P_orig=5, P_new=3 → 8*(5-3)=16
    comp = [
        {
            "barra_baseline": "OLD",
            "barra_propuesto": "NEW",
            "qty_baseline": 10,
            "qty_propuesto": 8,
            "extra_legs_qty": 0,
            "justificacion_factores": [
                {
                    "codigo": "sucedaneo",
                    "titulo": "Sucedáneo",
                    "detalle": "",
                    "datos": {
                        "oferta_baseline": {"barra": "OLD", "precio": 5.0},
                    },
                },
                {
                    "codigo": "oferta",
                    "titulo": "Oferta",
                    "detalle": "",
                    "datos": {"precio": 3.0, "proveedor": "P2"},
                },
            ],
        }
    ]
    out = compute_ahorros_motores(comp, [{"barra": "NEW", "precio": 3.0}])
    by = {m["codigo"]: m for m in out["ahorros_motores"]}
    assert by["sucedaneo"]["usd"] == 16.0
    assert by["cantidad_vs_historico"]["usd"] == 0.0
    assert out["ahorro_total_usd"] == 16.0


def test_qty_nueva_incluye_extra_legs():
    # primary 4 + extra 2 = 6; orig 5, new 4 → 6*(5-4)=6
    comp = [
        {
            "barra_baseline": "OLD",
            "barra_propuesto": "NEW",
            "qty_baseline": 4,
            "qty_propuesto": 4,
            "extra_legs_qty": 2,
            "justificacion_factores": [
                {
                    "codigo": "sucedaneo",
                    "titulo": "Sucedáneo",
                    "detalle": "",
                    "datos": {"oferta_baseline": {"barra": "OLD", "precio": 5.0}},
                },
                {
                    "codigo": "oferta",
                    "titulo": "Oferta",
                    "detalle": "",
                    "datos": {"precio": 4.0},
                },
            ],
        }
    ]
    out = compute_ahorros_motores(comp)
    by = {m["codigo"]: m for m in out["ahorros_motores"]}
    assert by["sucedaneo"]["usd"] == 6.0


def test_negativo_y_parcial_sin_precios():
    comp = [
        {
            "barra_baseline": "A",
            "barra_propuesto": "A",
            "qty_baseline": 10,
            "qty_propuesto": 12,
            "justificacion_factores": [
                {
                    "codigo": "oferta",
                    "titulo": "Oferta",
                    "detalle": "",
                    "datos": {"precio": 3.0, "media_de_mediana": 2.0},
                }
            ],
        },
        {
            "barra_baseline": "B",
            "barra_propuesto": "C",
            "qty_baseline": 5,
            "qty_propuesto": 5,
            "justificacion_factores": [
                {"codigo": "sucedaneo", "titulo": "Sucedáneo", "detalle": "", "datos": {}}
            ],
        },
    ]
    out = compute_ahorros_motores(comp)
    by = {m["codigo"]: m for m in out["ahorros_motores"]}
    # (12-10)*(2-3) = 2*(-1) = -2
    assert by["cantidad_vs_historico"]["usd"] == -2.0
    assert by["sucedaneo"]["usd"] == 0.0
    assert out["ahorro_parcial"] is True
    assert out["ahorro_lineas_sin_valorizar"] == 1
    assert out["ahorro_total_usd"] == -2.0


def test_serialize_includes_ahorros_meta():
    from analytics_engine.core.generar_sencillo_api import serialize_generar_result
    from analytics_engine.core.generar_pedido import (
        ComparativaRow,
        GenerarResult,
        PropuestoLine,
    )
    from analytics_engine.core.pedido_baseline import BaselineLine
    from analytics_engine.core.justificacion_factores import factor

    result = GenerarResult(
        pedido_baseline=[BaselineLine(barra="A", descripcion="A", cantidad=10)],
        pedido_propuesto=[
            PropuestoLine(
                barra="A", descripcion="A", proveedor="P1", cantidad=12, precio=1.5
            )
        ],
        comparativa_cantidades=[
            ComparativaRow(
                barra_baseline="A",
                desc_baseline="A",
                qty_baseline=10,
                barra_propuesto="A",
                desc_propuesto="A",
                qty_propuesto=12,
                justificacion_delta="Oferta",
                justificacion_factores=(
                    factor(
                        "oferta",
                        "P1",
                        datos={"precio": 1.5, "media_de_mediana": 2.0, "proveedor": "P1"},
                    ),
                ),
                proveedor="P1",
            )
        ],
    )
    payload = serialize_generar_result(result)
    assert "ahorros_motores" in payload["meta"]
    assert payload["meta"]["ahorro_total_usd"] == 1.0  # (12-10)*(2-1.5)
