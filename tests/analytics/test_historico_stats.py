"""Unit tests — historico_stats (Fase 0 / semanal)."""
from __future__ import annotations

import pandas as pd
import pytest

from analytics_engine.historico_stats.currency import (
    classify_precio_moneda,
    to_usd_candidate,
)
from analytics_engine.historico_stats.lotes_usd import (
    filter_lotes_observations,
    is_clean_barcode,
)
from analytics_engine.historico_stats.outliers import flag_mad_outliers
from analytics_engine.historico_stats.weekly_aggregate import aggregate_weekly_box


def test_classify_explicita_and_proveedor():
    mon, fuente = classify_precio_moneda(precio=10.0, moneda_explicita="VES")
    assert mon == "VES" and fuente == "explicita"

    mon, fuente = classify_precio_moneda(
        precio=10.0, moneda_explicita=None, moneda_proveedor="USD"
    )
    assert mon == "USD" and fuente == "proveedor_config"


def test_classify_heuristica_magnitud():
    mon, fuente = classify_precio_moneda(
        precio=500.0,
        moneda_explicita=None,
        moneda_proveedor=None,
        mediana_usd_barra=5.0,  # 500 >= 20 * 5 → VES
    )
    assert mon == "VES" and fuente == "heuristica_magnitud"

    mon, fuente = classify_precio_moneda(
        precio=6.0,
        mediana_usd_barra=5.0,
    )
    assert mon == "USD" and fuente == "default_usd"


def test_to_usd_ves():
    assert to_usd_candidate(100.0, moneda="USD", dolarbcv=36.0) == 100.0
    assert to_usd_candidate(360.0, moneda="VES", dolarbcv=36.0) == pytest.approx(10.0)
    with pytest.raises(ValueError):
        to_usd_candidate(10.0, moneda="VES", dolarbcv=0.0)


def test_aggregate_weekly_box_media_precio_min():
    df = pd.DataFrame(
        {
            "codigo_barras": ["A", "A", "A", "A"],
            "fecha": ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"],
            "precio_usd": [10.0, 12.0, 14.0, 16.0],
            "precio_min_diario": [9.0, 11.0, 13.0, 15.0],
        }
    )
    out = aggregate_weekly_box(df)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["codigo_barras"] == "A"
    assert row["n_obs"] == 4
    assert row["precio_min"] == 10.0
    assert row["precio_mediana"] == pytest.approx(13.0)
    assert row["media_precio_min"] == pytest.approx(12.0)  # mean of daily mins
    assert row["anio_iso"] == 2026
    assert int(row["semana_iso"]) == 2  # ISO week of early Jan 2026


def test_mad_flags_extreme():
    # 6 near 10, one extreme 1000 → outlier
    precios = [9.5, 10.0, 10.2, 9.8, 10.1, 10.05, 1000.0]
    df = pd.DataFrame(
        {
            "codigo_barras": ["X"] * len(precios),
            "precio_usd": precios,
        }
    )
    out = flag_mad_outliers(df, min_n=5)
    assert bool(out.loc[out["precio_usd"] == 1000.0, "es_outlier_mad"].iloc[0])
    assert not bool(out.loc[out["precio_usd"] == 10.0, "es_outlier_mad"].iloc[0])


def test_lotes_filter_drops_junk_keeps_usd():
    assert is_clean_barcode("7598504265580")
    assert not is_clean_barcode("AMP_AMIKAC_500")
    assert not is_clean_barcode("bli_foo")
    assert not is_clean_barcode("none")

    raw = pd.DataFrame(
        {
            "codigo_barras": ["7598504265580", "AMP_X", "short", "7598504265580"],
            "fecha": ["2022-01-10", "2022-01-10", "2022-01-10", "2020-01-01"],
            "precio_usd": [1.5, 2.0, 3.0, 4.0],
        }
    )
    out = filter_lotes_observations(raw)
    assert list(out["codigo_barras"]) == ["7598504265580"]
    assert float(out.iloc[0]["precio_usd"]) == 1.5
