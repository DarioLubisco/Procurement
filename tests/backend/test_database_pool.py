"""PyODBC pool release must rollback so uncommitted work cannot leak across requests."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

# database.py imports pyodbc at module load; unit tests do not need a real driver.
sys.modules.setdefault("pyodbc", MagicMock())
sys.modules.setdefault("dotenv", MagicMock(load_dotenv=MagicMock()))

from backend.database import PooledConnectionWrapper, PyODBCPool  # noqa: E402


def test_release_connection_rolls_back_before_returning_to_pool():
    pool = PyODBCPool(max_connections=2)
    conn = MagicMock()

    pool.release_connection(conn)

    conn.rollback.assert_called_once_with()
    assert pool.pool.get_nowait() is conn


def test_release_connection_discards_when_rollback_fails():
    pool = PyODBCPool(max_connections=2)
    pool.current_connections = 1
    conn = MagicMock()
    conn.rollback.side_effect = RuntimeError("connection dead")

    pool.release_connection(conn)

    conn.rollback.assert_called_once_with()
    conn.close.assert_called_once_with()
    assert pool.current_connections == 0
    with pytest.raises(Exception):
        pool.pool.get_nowait()


def test_wrapper_close_triggers_rollback_via_release():
    pool = PyODBCPool(max_connections=2)
    raw = MagicMock()
    wrapper = PooledConnectionWrapper(pool, raw)

    wrapper.close()
    wrapper.close()  # idempotent

    raw.rollback.assert_called_once_with()
    assert pool.pool.get_nowait() is raw
