"""Load ProveedorConfig (ProveedorID + MontoMinimoPedidoUSD) — ADR-0015/0016."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


_SQL = """
SELECT ProveedorID, CodProv, NombreCorto, MontoMinimoPedidoUSD
FROM Procurement.ProveedorConfig
WHERE Activo = 1
"""

_SQL_LEGACY = """
SELECT CodProv, NombreCorto, MontoMinimoPedidoUSD
FROM Procurement.ProveedorConfig
WHERE Activo = 1
"""


def fetch_proveedor_config_rows(
    conn: Any,
    *,
    execute: Optional[Callable[..., Any]] = None,
) -> List[Dict[str, Any]]:
    """Return active ProveedorConfig rows with numeric ProveedorID when available."""
    def _run(sql: str):
        if execute is not None:
            return execute(sql)
        cur = conn.cursor()
        cur.execute(sql)
        return cur.fetchall()

    try:
        rows = _run(_SQL)
        out: List[Dict[str, Any]] = []
        for row in rows:
            cod = str(row[1] or "").strip()
            if not cod:
                continue
            raw = row[3]
            out.append(
                {
                    "proveedor_id": int(row[0]),
                    "cod_prov": cod,
                    "nombre_corto": str(row[2] or "").strip(),
                    "monto_minimo_pedido_usd": None if raw is None else float(raw),
                }
            )
        return out
    except Exception:
        # Pre-migration schema without ProveedorID
        rows = _run(_SQL_LEGACY)
        out = []
        for i, row in enumerate(rows, start=1):
            cod = str(row[0] or "").strip()
            if not cod:
                continue
            raw = row[2]
            out.append(
                {
                    "proveedor_id": i,
                    "cod_prov": cod,
                    "nombre_corto": str(row[1] or "").strip(),
                    "monto_minimo_pedido_usd": None if raw is None else float(raw),
                }
            )
        return out


def fetch_minimos_usd(
    conn: Any,
    *,
    execute: Optional[Callable[..., Any]] = None,
) -> Dict[str, Optional[float]]:
    """Map CodProv (Mercado_Vivo.proveedor) → MontoMinimoPedidoUSD."""
    return {
        r["cod_prov"]: r["monto_minimo_pedido_usd"]
        for r in fetch_proveedor_config_rows(conn, execute=execute)
    }


def fetch_cod_prov_by_id(
    conn: Any,
    *,
    execute: Optional[Callable[..., Any]] = None,
) -> Dict[int, str]:
    """Map ProveedorID → CodProv."""
    return {
        int(r["proveedor_id"]): r["cod_prov"]
        for r in fetch_proveedor_config_rows(conn, execute=execute)
    }


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


def load_proveedor_config_from_db() -> List[Dict[str, Any]]:
    import database

    conn = database.get_db_connection()
    try:
        return fetch_proveedor_config_rows(conn)
    finally:
        try:
            conn.close()
        except Exception:
            pass
