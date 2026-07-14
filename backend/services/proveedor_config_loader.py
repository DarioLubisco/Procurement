"""Load ProveedorConfig.MontoMinimoPedidoUSD (ADR-0015/0016)."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional


_SQL = """
SELECT CodProv, MontoMinimoPedidoUSD
FROM Procurement.ProveedorConfig
WHERE Activo = 1
"""


def fetch_minimos_usd(
    conn: Any,
    *,
    execute: Optional[Callable[..., Any]] = None,
) -> Dict[str, Optional[float]]:
    """Map CodProv → MontoMinimoPedidoUSD (None if NULL)."""
    if execute is not None:
        rows = execute(_SQL)
    else:
        cur = conn.cursor()
        cur.execute(_SQL)
        rows = cur.fetchall()

    out: Dict[str, Optional[float]] = {}
    for row in rows:
        cod = str(row[0] or "").strip()
        if not cod:
            continue
        raw = row[1]
        if raw is None:
            out[cod] = None
        else:
            out[cod] = float(raw)
    return out


def load_minimos_usd_from_db() -> Dict[str, Optional[float]]:
    import database

    conn = database.get_db_connection()
    try:
        return fetch_minimos_usd(conn)
    finally:
        try:
            conn.close()
        except Exception:
            pass
