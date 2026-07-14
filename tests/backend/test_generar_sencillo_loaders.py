"""Mercado_Vivo loader — chunked IN lists (no hard 200-barcode truncation)."""
from __future__ import annotations

import pandas as pd

from backend.services.generar_sencillo_loaders import (
    fetch_mercado_vivo_offers,
    prioritize_barras_for_offers,
)


def test_prioritize_barras_positive_need_and_mdm_siblings():
    rows = [
        {
            "barra": "NEED",
            "rotacion_mensual": 20.0,
            "existen": 0.0,
            "principio_activo": "PA1",
            "forma_farmaceutica": "TAB",
            "concentracion": "10",
            "cantidad_presentacion": "10",
            "contenido_neto": "1",
        },
        {
            "barra": "SIBLING",
            "rotacion_mensual": 1.0,
            "existen": 100.0,  # no own need, but same MDM group
            "principio_activo": "PA1",
            "forma_farmaceutica": "TAB",
            "concentracion": "10",
            "cantidad_presentacion": "10",
            "contenido_neto": "1",
        },
        {
            "barra": "STOCKED",
            "rotacion_mensual": 5.0,
            "existen": 50.0,  # qty <= 0
            "principio_activo": "PA2",
            "forma_farmaceutica": "TAB",
            "concentracion": "5",
            "cantidad_presentacion": "10",
            "contenido_neto": "1",
        },
    ]
    assert prioritize_barras_for_offers(rows) == ["NEED", "SIBLING"]


def test_prioritize_barras_unique_highest_rotacion_first_when_all_need():
    rows = [
        {"barra": "A", "rotacion_mensual": 1.0, "existen": 0.0},
        {"barra": "B", "rotacion_mensual": 50.0, "existen": 0.0},
        {"barra": "A", "rotacion_mensual": 1.0, "existen": 0.0},
        {"barra": "C", "rotacion_mensual": 10.0, "existen": 0.0},
    ]
    assert prioritize_barras_for_offers(rows) == ["B", "C", "A"]


def test_fetch_mercado_vivo_offers_chunks_all_barras_not_just_first_n():
    calls: list[list[str]] = []

    def fake_read_sql(sql, conn, params=None):
        calls.append(list(params or []))
        return pd.DataFrame(
            {
                "codigo_barras": list(params or []),
                "proveedor": ["P"] * len(params or []),
                "precio_unitario_final": [1.0] * len(params or []),
                "stock_disponible": [5] * len(params or []),
                "descripcion_producto": ["x"] * len(params or []),
            }
        )

    barras = [f"SKU{i}" for i in range(450)]
    out = fetch_mercado_vivo_offers(
        conn=object(),
        barras=barras,
        chunk_size=200,
        read_sql=fake_read_sql,
    )

    assert len(calls) == 3
    assert [len(c) for c in calls] == [200, 200, 50]
    assert set(calls[0] + calls[1] + calls[2]) == set(barras)
    assert len(out) == 450


def test_fetch_mercado_vivo_offers_continues_after_chunk_failure():
    def flaky_read_sql(sql, conn, params=None):
        if params and params[0] == "A1":
            raise TimeoutError("ODBC timeout")
        return pd.DataFrame(
            {
                "codigo_barras": list(params or []),
                "proveedor": ["P"] * len(params or []),
                "precio_unitario_final": [2.0] * len(params or []),
                "stock_disponible": [1] * len(params or []),
                "descripcion_producto": ["ok"] * len(params or []),
            }
        )

    out = fetch_mercado_vivo_offers(
        conn=object(),
        barras=["A1", "A2", "B1"],
        chunk_size=2,
        read_sql=flaky_read_sql,
    )
    assert out["codigo_barras"].tolist() == ["B1"]
