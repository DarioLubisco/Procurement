"""SAINSTA category tree loader (cursor-based — avoids pandas Gaps-in-blk 500s)."""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# In-process TTL cache — SAINSTA changes rarely; cuts ODBC chatter on FE reload.
CATEGORIES_CACHE_TTL_S = 45.0
_categories_cache: Dict[str, Any] = {"ts": 0.0, "data": None}

_SQL_SAINSTA = """
    SELECT CodInst, Descrip, InsPadre
    FROM dbo.SAINSTA
    ORDER BY Descrip
"""


def clear_categories_cache() -> None:
    """Test helper / admin: drop in-process categories cache."""
    _categories_cache["ts"] = 0.0
    _categories_cache["data"] = None


def fetch_sainsta_categories(
    conn: Any,
    *,
    execute: Optional[Callable[..., Any]] = None,
) -> List[Dict[str, str]]:
    """Return categories as {id, name, parentId} without pandas."""
    if execute is not None:
        rows = execute(_SQL_SAINSTA)
    else:
        cur = conn.cursor()
        cur.execute(_SQL_SAINSTA)
        rows = cur.fetchall()

    out: List[Dict[str, str]] = []
    for row in rows:
        # pyodbc.Row supports index access; also allow tuple/list
        cod = row[0]
        descrip = row[1]
        padre = row[2]
        if descrip is None:
            continue
        name = str(descrip).strip()
        if not name:
            continue
        parent_id = "0"
        if padre is not None and str(padre).strip() != "":
            try:
                parent_id = str(int(padre))
            except (TypeError, ValueError):
                parent_id = str(padre).strip() or "0"
        out.append(
            {
                "id": str(cod),
                "name": name,
                "parentId": parent_id,
            }
        )
    return out


def load_categories_with_retry(
    get_connection: Callable[[], Any],
    *,
    retries: int = 2,
    retry_delay_s: float = 0.4,
) -> List[Dict[str, str]]:
    """Open DB, fetch SAINSTA categories; retry on transient ODBC login timeouts."""
    last_exc: Optional[BaseException] = None
    attempts = max(1, int(retries))
    for attempt in range(attempts):
        conn = None
        try:
            conn = get_connection()
            return fetch_sainsta_categories(conn)
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            transient = (
                "login timeout" in msg
                or "hyt00" in msg
                or "gaps in blk" in msg
            )
            logger.warning(
                "categories load attempt %s/%s failed: %s",
                attempt + 1,
                attempts,
                exc,
            )
            if not transient or attempt + 1 >= attempts:
                raise
            time.sleep(retry_delay_s)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
    assert last_exc is not None
    raise last_exc


def load_categories_cached(
    get_connection: Callable[[], Any],
    *,
    ttl_s: float = CATEGORIES_CACHE_TTL_S,
    retries: int = 2,
    retry_delay_s: float = 0.4,
    now: Optional[Callable[[], float]] = None,
) -> Tuple[List[Dict[str, str]], str]:
    """Return (categories, cache_status) with 'hit' | 'miss'."""
    clock = now or time.time
    cached = _categories_cache.get("data")
    ts = float(_categories_cache.get("ts") or 0.0)
    if cached is not None and (clock() - ts) < float(ttl_s):
        return list(cached), "hit"
    data = load_categories_with_retry(
        get_connection, retries=retries, retry_delay_s=retry_delay_s
    )
    _categories_cache["data"] = list(data)
    _categories_cache["ts"] = clock()
    return list(data), "miss"
