"""Load open Backorder quantities from Procurement tables (ADR-0009)."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

# Open cabeceras only — closed/cancelled pedidos do not reduce new Generar need.
_CLOSED_CABECERA = ("CERRADO", "CANCELADO")
_CLOSED_LINEA = ("COMPLETO", "REVERTIDO", "CANCELADO")

_SQL_OPEN_BACKORDER = """
SELECT
    x.barra,
    SUM(x.cantidad) AS cantidad
FROM (
    SELECT
        COALESCE(
            NULLIF(LTRIM(RTRIM(l.CodigoBarras)), ''),
            LTRIM(RTRIM(l.CodigoProducto))
        ) AS barra,
        CAST(l.CantidadPendiente AS INT) AS cantidad
    FROM Procurement.BackorderPedidosLineas AS l
    INNER JOIN Procurement.BackorderPedidosCabecera AS c
        ON c.PedidoID = l.PedidoID
    WHERE ISNULL(l.CantidadPendiente, 0) > 0
      AND UPPER(LTRIM(RTRIM(ISNULL(c.EstadoBackorder, '')))) NOT IN ({cab_excl})
      AND UPPER(LTRIM(RTRIM(ISNULL(l.EstadoLinea, '')))) NOT IN ({lin_excl})
) AS x
WHERE x.barra IS NOT NULL
  AND LTRIM(RTRIM(x.barra)) <> ''
GROUP BY x.barra
HAVING SUM(x.cantidad) > 0
"""


def _sql_in_literals(values: Sequence[str]) -> str:
    return ", ".join("'" + v.replace("'", "''") + "'" for v in values)


def fetch_open_backorder_rows(
    conn: Any,
    *,
    execute: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """Aggregate pending qty by barra from open Backorder pedidos."""
    sql = _SQL_OPEN_BACKORDER.format(
        cab_excl=_sql_in_literals(_CLOSED_CABECERA),
        lin_excl=_sql_in_literals(_CLOSED_LINEA),
    )
    if execute is not None:
        rows = execute(sql)
    else:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()

    out: List[Dict[str, Any]] = []
    for row in rows:
        barra = str(row[0] or "").strip()
        if not barra:
            continue
        try:
            qty = int(row[1] or 0)
        except (TypeError, ValueError):
            qty = 0
        if qty <= 0:
            continue
        out.append({"barra": barra, "cantidad": qty})
    return out


def load_backorder_from_db() -> List[Dict[str, Any]]:
    """Productive path: open Backorder lineas → [{barra, cantidad}, ...]."""
    import database

    conn = database.get_db_connection()
    try:
        rows = fetch_open_backorder_rows(conn)
        logger.info("Backorder open rows loaded: %s", len(rows))
        return rows
    except Exception as exc:
        logger.warning("Backorder tables unavailable: %s", exc)
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass
