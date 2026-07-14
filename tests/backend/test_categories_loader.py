"""Categories loader — cursor path (no pandas Gaps-in-blk)."""
from __future__ import annotations

import pytest

from backend.services.categories_loader import (
    fetch_sainsta_categories,
    load_categories_with_retry,
)


def test_fetch_sainsta_categories_maps_rows_and_skips_blank():
    rows = [
        (1, "Medicinas", 0),
        (2, "  ", 0),
        (3, None, 0),
        (4, "Ampollas", 1),
        (5, "OTC", None),
    ]
    out = fetch_sainsta_categories(conn=None, execute=lambda sql: rows)
    assert out == [
        {"id": "1", "name": "Medicinas", "parentId": "0"},
        {"id": "4", "name": "Ampollas", "parentId": "1"},
        {"id": "5", "name": "OTC", "parentId": "0"},
    ]


def test_load_categories_retries_transient_timeout_then_succeeds():
    calls = {"n": 0}

    def get_conn():
        calls["n"] += 1
        if calls["n"] == 1:
            raise Exception("HYT00 Login timeout expired")

        class _Conn:
            def cursor(self):
                return self

            def execute(self, sql):
                return None

            def fetchall(self):
                return [(10, "General", 0)]

            def close(self):
                return None

        return _Conn()

    out = load_categories_with_retry(get_conn, retries=2, retry_delay_s=0.01)
    assert out == [{"id": "10", "name": "General", "parentId": "0"}]
    assert calls["n"] == 2


def test_load_categories_raises_after_exhausted_retries():
    def get_conn():
        raise Exception("HYT00 Login timeout expired")

    with pytest.raises(Exception, match="Login timeout"):
        load_categories_with_retry(get_conn, retries=2, retry_delay_s=0.01)
