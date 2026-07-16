"""CRUD for Procurement.PedidoPresets — custom Definitivo recipes (global)."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_SQL_LIST = """
SELECT PresetId, Nombre, Nivel, BasePreset, OverridesJson, CreatedAt, UpdatedAt
FROM Procurement.PedidoPresets
ORDER BY Nombre
"""

_SQL_GET = """
SELECT PresetId, Nombre, Nivel, BasePreset, OverridesJson, CreatedAt, UpdatedAt
FROM Procurement.PedidoPresets
WHERE PresetId = ?
"""

_SQL_GET_BY_NAME = """
SELECT PresetId, Nombre, Nivel, BasePreset, OverridesJson, CreatedAt, UpdatedAt
FROM Procurement.PedidoPresets
WHERE Nombre = ?
"""

_SQL_INSERT = """
INSERT INTO Procurement.PedidoPresets (Nombre, Nivel, BasePreset, OverridesJson)
OUTPUT INSERTED.PresetId
VALUES (?, ?, ?, ?)
"""

_SQL_UPDATE = """
UPDATE Procurement.PedidoPresets
SET Nombre = ?, Nivel = ?, BasePreset = ?, OverridesJson = ?, UpdatedAt = SYSUTCDATETIME()
WHERE PresetId = ?
"""

_SQL_UPDATE_BY_NAME = """
UPDATE Procurement.PedidoPresets
SET Nivel = ?, BasePreset = ?, OverridesJson = ?, UpdatedAt = SYSUTCDATETIME()
WHERE Nombre = ?
"""

_SQL_DELETE = """
DELETE FROM Procurement.PedidoPresets WHERE PresetId = ?
"""


def _row_to_dict(row: Any) -> Dict[str, Any]:
    overrides_raw = row[4]
    try:
        overrides = json.loads(overrides_raw) if overrides_raw else {}
    except (TypeError, ValueError):
        overrides = {}
    if not isinstance(overrides, dict):
        overrides = {}
    return {
        "preset_id": int(row[0]),
        "nombre": str(row[1] or "").strip(),
        "nivel": str(row[2] or "").strip(),
        "base_preset": str(row[3] or "").strip(),
        "overrides": overrides,
        "created_at": row[5].isoformat() if row[5] is not None else None,
        "updated_at": row[6].isoformat() if row[6] is not None else None,
    }


def list_presets(conn: Any) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(_SQL_LIST)
    return [_row_to_dict(r) for r in cur.fetchall()]


def get_preset(conn: Any, preset_id: int) -> Optional[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(_SQL_GET, (int(preset_id),))
    row = cur.fetchone()
    return _row_to_dict(row) if row else None


def upsert_preset(
    conn: Any,
    *,
    nombre: str,
    nivel: str,
    base_preset: str,
    overrides: Dict[str, Any],
    preset_id: Optional[int] = None,
) -> Dict[str, Any]:
    name = (nombre or "").strip()
    if not name:
        raise ValueError("nombre required")
    if nivel not in ("Intermedio", "Avanzado"):
        raise ValueError("nivel must be Intermedio|Avanzado")
    if base_preset not in ("Conservador", "Normal", "Agresivo"):
        raise ValueError("base_preset must be Conservador|Normal|Agresivo")
    payload = json.dumps(overrides or {}, ensure_ascii=False)
    cur = conn.cursor()

    if preset_id is not None:
        cur.execute(_SQL_UPDATE, (name, nivel, base_preset, payload, int(preset_id)))
        if cur.rowcount == 0:
            raise LookupError(f"preset_id {preset_id} not found")
        conn.commit()
        out = get_preset(conn, int(preset_id))
        assert out is not None
        return out

    cur.execute(_SQL_GET_BY_NAME, (name,))
    existing = cur.fetchone()
    if existing:
        pid = int(existing[0])
        cur.execute(_SQL_UPDATE_BY_NAME, (nivel, base_preset, payload, name))
        conn.commit()
        out = get_preset(conn, pid)
        assert out is not None
        return out

    cur.execute(_SQL_INSERT, (name, nivel, base_preset, payload))
    row = cur.fetchone()
    conn.commit()
    pid = int(row[0])
    out = get_preset(conn, pid)
    assert out is not None
    return out


def delete_preset(conn: Any, preset_id: int) -> bool:
    cur = conn.cursor()
    cur.execute(_SQL_DELETE, (int(preset_id),))
    conn.commit()
    return cur.rowcount > 0
