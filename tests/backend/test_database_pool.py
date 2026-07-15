"""PyODBC pool: rollback on release before reuse."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

# database.py imports heavy deps at module load; keep unit tests driver-free.
sys.modules.setdefault("pyodbc", MagicMock())
sys.modules.setdefault("dotenv", MagicMock())

from backend.database import PyODBCPool  # noqa: E402


def test_release_connection_rollbacks_before_returning_to_pool():
    pool = PyODBCPool(max_connections=2)
    pool.current_connections = 1
    conn = MagicMock()

    pool.release_connection(conn)

    conn.rollback.assert_called_once_with()
    assert pool.pool.get_nowait() is conn
    conn.close.assert_not_called()


def test_release_connection_discards_when_rollback_fails():
    pool = PyODBCPool(max_connections=2)
    pool.current_connections = 1
    conn = MagicMock()
    conn.rollback.side_effect = Exception("connection dead")

    pool.release_connection(conn)

    conn.rollback.assert_called_once_with()
    conn.close.assert_called_once_with()
    assert pool.current_connections == 0
    assert pool.pool.empty()


def test_release_connection_decrements_when_pool_full():
    pool = PyODBCPool(max_connections=1)
    pool.current_connections = 1
    pool.pool.put_nowait(MagicMock())  # fill queue
    conn = MagicMock()

    pool.release_connection(conn)

    conn.rollback.assert_called_once_with()
    conn.close.assert_called_once_with()
    assert pool.current_connections == 0
