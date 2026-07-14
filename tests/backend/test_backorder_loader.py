"""Backorder DB loader — open Procurement.Backorder* pedidos."""
from __future__ import annotations

from backend.services.backorder_loader import fetch_open_backorder_rows


def test_fetch_open_backorder_aggregates_by_barra():
    rows = [
        ("7701", 5),
        ("7701", 3),
        ("7702", 1),
    ]
    # execute ignores SQL and returns pre-aggregated rows (SQL does GROUP BY)
    out = fetch_open_backorder_rows(conn=None, execute=lambda sql: rows)
    assert out == [
        {"barra": "7701", "cantidad": 5},
        {"barra": "7701", "cantidad": 3},
        {"barra": "7702", "cantidad": 1},
    ]


def test_fetch_open_backorder_skips_blank_and_non_positive():
    rows = [
        ("", 4),
        ("  ", 2),
        ("OK", 0),
        ("OK2", -1),
        ("GOOD", 7),
    ]
    out = fetch_open_backorder_rows(conn=None, execute=lambda sql: rows)
    assert out == [{"barra": "GOOD", "cantidad": 7}]
