"""Mercado_Vivo loader — chunked IN lists (no hard 200-barcode truncation)."""
from __future__ import annotations

import pandas as pd

from backend.services.generar_sencillo_loaders import (
    enrich_offers_with_desvio,
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


def test_fetch_mercado_vivo_offers_openjson_primary_path():
    class _Cur:
        def __init__(self):
            self.sql = None
            self.params = None
            self.description = [
                ("codigo_barras",),
                ("proveedor",),
                ("precio_unitario_final",),
                ("stock_disponible",),
                ("descripcion_producto",),
            ]

        def execute(self, sql, params=None):
            self.sql = sql
            self.params = params

        def fetchall(self):
            return [("111", "P", 1.5, 10, "x")]

    class _Conn:
        def cursor(self):
            return _Cur()

    out = fetch_mercado_vivo_offers(conn=_Conn(), barras=["111", "111", "  "])
    assert len(out) == 1
    assert out.iloc[0]["codigo_barras"] == "111"


def test_fetch_mercado_vivo_offers_falls_back_to_full_scan():
    class _Cur:
        def __init__(self):
            self.description = [
                ("codigo_barras",),
                ("proveedor",),
                ("precio_unitario_final",),
                ("stock_disponible",),
                ("descripcion_producto",),
            ]

        def execute(self, sql, params=None):
            if "OPENJSON" in sql:
                raise Exception("OPENJSON not supported")
            self.sql = sql

        def fetchall(self):
            return [
                ("KEEP", "P", 1.0, 1, "a"),
                ("DROP", "P", 2.0, 1, "b"),
            ]

    class _Conn:
        def cursor(self):
            return _Cur()

    out = fetch_mercado_vivo_offers(conn=_Conn(), barras=["KEEP"])
    assert out["codigo_barras"].tolist() == ["KEEP"]


def test_enrich_offers_with_desvio_uses_media_de_mediana_not_min():
    offers = [
        {"barra": "A", "proveedor": "P1", "precio": 8.0},
        {"barra": "B", "proveedor": "P2", "precio": 10.0},  # no baseline
    ]
    baselines = {
        "A": {
            "media_de_mediana": 10.0,
            "media_min_diario": 5.0,  # must NOT be used for desvio
            "dias_hist": 12,
        }
    }
    out = enrich_offers_with_desvio(offers, baselines)
    assert out[0]["desvio"] == -0.2  # (8-10)/10
    assert out[0]["media_de_mediana"] == 10.0
    assert out[0]["media_min_diario"] == 5.0
    assert "desvio" not in out[1]


def test_enrich_offers_with_desvio_zero_when_at_media():
    out = enrich_offers_with_desvio(
        [{"barra": "X", "proveedor": "P", "precio": 12.5}],
        {"X": {"media_de_mediana": 12.5, "media_min_diario": 10.0, "dias_hist": 5}},
    )
    assert out[0]["desvio"] == 0.0
