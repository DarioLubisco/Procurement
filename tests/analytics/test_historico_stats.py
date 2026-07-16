"""Unit tests — historico_stats (Fase 0 / semanal)."""
from __future__ import annotations

import pandas as pd

from analytics_engine.historico_stats.currency import (
    classify_precio_moneda,
    to_usd_candidate,
)
from analytics_engine.historico_stats.weekly_aggregate import aggregate_weekly_box
from analytics_engine.historico_stats.outliers import flag_mad_outliers


def test_classify_explicita_and_proveedor():
    m, f = classify_precio_moneda(precio=100.0, moneda_explicita="VES")
    assert m == "VES" and f == "explicita"
    m, f = classify_precio_moneda(precio=2.0, moneda_proveedor="USD")
    assert m == "USD" and f == "proveedor_config"


def test_classify_heuristica_magnitud():
    m, f = classify_precio_moneda(precio=500.0, mediana_usd_barra=2.0, factor=20.0)
    assert m == "VES" and f == "heuristica_magnitud"
    m, f = classify_precio_moneda(precio=3.0, mediana_usd_barra=2.0, factor=20.0)
    assert m == "USD" and f == "default_usd"


def test_to_usd_ves():
    assert abs(to_usd_candidate(725.0, moneda="VES", dolarbcv=725.0) - 1.0) < 1e-9


def test_aggregate_weekly_box_media_precio_min():
    df = pd.DataFrame(
        [
            {
                "codigo_barras": "X",
                "fecha": "2024-06-03",
                "precio_usd": 2.0,
                "precio_min_diario": 1.5,
            },
            {
                "codigo_barras": "X",
                "fecha": "2024-06-04",
                "precio_usd": 2.4,
                "precio_min_diario": 1.7,
            },
        ]
    )
    w = aggregate_weekly_box(df)
    assert len(w) == 1
    assert w.iloc[0]["n_obs"] == 2
    assert abs(w.iloc[0]["media_precio_min"] - 1.6) < 1e-9
    assert w.iloc[0]["precio_min"] == 2.0


def test_mad_flags_extreme():
    rows = [{"codigo_barras": "A", "precio_usd": 2.0 + i * 0.01} for i in range(10)]
    rows.append({"codigo_barras": "A", "precio_usd": 200.0})
    df = flag_mad_outliers(pd.DataFrame(rows), min_n=5)
    assert bool(df.loc[df["precio_usd"] == 200.0, "es_outlier_mad"].iloc[0])


def test_lotes_filter_drops_junk_keeps_usd():
    from analytics_engine.historico_stats.lotes_usd import (
        filter_lotes_observations,
        is_clean_barcode,
    )

    assert is_clean_barcode("7591821801929")
    assert not is_clean_barcode("None")
    assert not is_clean_barcode("BLI_ENTERO")
    assert not is_clean_barcode("123")  # too short

    df = pd.DataFrame(
        [
            {"codigo_barras": "7591821801929", "fecha": "2024-06-03", "precio_usd": 3.5},
            {"codigo_barras": "None", "fecha": "2024-06-03", "precio_usd": 99.0},
            {"codigo_barras": "BLI_X", "fecha": "2024-06-03", "precio_usd": 1.0},
            {"codigo_barras": "7591821801929", "fecha": "2020-01-01", "precio_usd": 2.0},
        ]
    )
    clean = filter_lotes_observations(df)
    assert len(clean) == 1
    assert clean.iloc[0]["precio_usd"] == 3.5
    w = aggregate_weekly_box(clean)
    assert len(w) == 1
    assert abs(w.iloc[0]["precio_mediana"] - 3.5) < 1e-9
