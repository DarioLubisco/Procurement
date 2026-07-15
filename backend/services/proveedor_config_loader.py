"""Load ProveedorConfig + CodProv aliases (ProveedorID commercial groups) — ADR-0015/0016."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence


_SQL_ACTIVE = """
SELECT ProveedorID, CodProv, NombreCorto, MontoMinimoPedidoUSD
FROM Procurement.ProveedorConfig
WHERE Activo = 1
"""

_SQL_ACTIVE_LEGACY = """
SELECT CodProv, NombreCorto, MontoMinimoPedidoUSD
FROM Procurement.ProveedorConfig
WHERE Activo = 1
"""

_SQL_ALIASES = """
SELECT CodProv, ProveedorID
FROM Procurement.ProveedorCodProvAlias
"""


def _upper(s: str) -> str:
    return str(s or "").strip().upper()


def build_proveedor_groups(
    active_rows: Sequence[Dict[str, Any]],
    alias_rows: Optional[Sequence[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Build commercial groups: one entry per active ProveedorID with alias CodProvs.

    Each group:
      proveedor_id, cod_prov (canonical), nombre_corto, monto_minimo_pedido_usd, aliases[]
    """
    by_id: Dict[int, Dict[str, Any]] = {}
    for r in active_rows:
        pid = int(r["proveedor_id"])
        cod = str(r["cod_prov"]).strip()
        by_id[pid] = {
            "proveedor_id": pid,
            "cod_prov": cod,
            "nombre_corto": str(r.get("nombre_corto") or "").strip() or cod,
            "monto_minimo_pedido_usd": r.get("monto_minimo_pedido_usd"),
            "aliases": [cod],
        }

    if alias_rows:
        for a in alias_rows:
            pid = int(a["proveedor_id"])
            cod = str(a["cod_prov"]).strip()
            if not cod:
                continue
            g = by_id.get(pid)
            if g is None:
                continue
            if all(_upper(x) != _upper(cod) for x in g["aliases"]):
                g["aliases"].append(cod)

    # Stable alias order: canonical first, then sorted rest
    out: List[Dict[str, Any]] = []
    for g in sorted(by_id.values(), key=lambda x: int(x["proveedor_id"])):
        can = g["cod_prov"]
        rest = sorted(
            (a for a in g["aliases"] if _upper(a) != _upper(can)),
            key=lambda s: _upper(s),
        )
        g["aliases"] = [can] + rest
        out.append(g)
    return out


def alias_index_from_groups(
    groups: Sequence[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Map upper(CodProv) → group dict."""
    idx: Dict[str, Dict[str, Any]] = {}
    for g in groups:
        for a in g.get("aliases") or []:
            idx[_upper(a)] = g
        idx[_upper(g["cod_prov"])] = g
    return idx


def minimos_usd_from_groups(
    groups: Sequence[Dict[str, Any]],
) -> Dict[str, Optional[float]]:
    """Flat CodProv → minimo for every alias + canonical (exact seeded casing)."""
    out: Dict[str, Optional[float]] = {}
    for g in groups:
        m = g.get("monto_minimo_pedido_usd")
        for a in g.get("aliases") or [g["cod_prov"]]:
            out[str(a).strip()] = None if m is None else float(m)
        out[str(g["cod_prov"]).strip()] = None if m is None else float(m)
    return out


def groups_from_flat_minimos(
    minimos_usd: Dict[str, Optional[float]],
) -> List[Dict[str, Any]]:
    """Synthesize one group per CodProv (tests / inject without alias table)."""
    out: List[Dict[str, Any]] = []
    for i, (cod, minimo) in enumerate(sorted(minimos_usd.items()), start=1):
        c = str(cod).strip()
        if not c:
            continue
        out.append(
            {
                "proveedor_id": i,
                "cod_prov": c,
                "nombre_corto": c,
                "monto_minimo_pedido_usd": minimo,
                "aliases": [c],
            }
        )
    return out


def fetch_proveedor_config_rows(
    conn: Any,
    *,
    execute: Optional[Callable[..., Any]] = None,
) -> List[Dict[str, Any]]:
    """Active ProveedorConfig rows (canonical commercial entities when aliases seeded)."""

    def _run(sql: str):
        if execute is not None:
            return execute(sql)
        cur = conn.cursor()
        cur.execute(sql)
        return cur.fetchall()

    try:
        rows = _run(_SQL_ACTIVE)
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
        rows = _run(_SQL_ACTIVE_LEGACY)
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


def fetch_alias_rows(
    conn: Any,
    *,
    execute: Optional[Callable[..., Any]] = None,
) -> List[Dict[str, Any]]:
    """Rows from ProveedorCodProvAlias; empty if table missing."""

    def _run(sql: str):
        if execute is not None:
            return execute(sql)
        cur = conn.cursor()
        cur.execute(sql)
        return cur.fetchall()

    try:
        rows = _run(_SQL_ALIASES)
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for row in rows:
        cod = str(row[0] or "").strip()
        if not cod:
            continue
        out.append({"cod_prov": cod, "proveedor_id": int(row[1])})
    return out


def fetch_proveedor_groups(
    conn: Any,
    *,
    execute: Optional[Callable[..., Any]] = None,
    execute_aliases: Optional[Callable[..., Any]] = None,
) -> List[Dict[str, Any]]:
    active = fetch_proveedor_config_rows(conn, execute=execute)
    aliases = fetch_alias_rows(
        conn, execute=execute_aliases if execute_aliases is not None else execute
    )
    return build_proveedor_groups(active, aliases)


def fetch_minimos_usd(
    conn: Any,
    *,
    execute: Optional[Callable[..., Any]] = None,
) -> Dict[str, Optional[float]]:
    """Map CodProv (incl. aliases) → MontoMinimoPedidoUSD of the commercial group."""
    return minimos_usd_from_groups(fetch_proveedor_groups(conn, execute=execute))


def fetch_cod_prov_by_id(
    conn: Any,
    *,
    execute: Optional[Callable[..., Any]] = None,
) -> Dict[int, str]:
    """Map ProveedorID → canonical CodProv."""
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


def load_proveedor_groups_from_db() -> List[Dict[str, Any]]:
    import database

    conn = database.get_db_connection()
    try:
        return fetch_proveedor_groups(conn)
    finally:
        try:
            conn.close()
        except Exception:
            pass
