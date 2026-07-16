"""Unit tests for PedidoPresets service (in-memory fake cursor)."""
from __future__ import annotations

import json
from typing import Any, List, Optional, Tuple

from backend.services import pedido_presets_service as svc


class FakeCursor:
    def __init__(self, store: dict):
        self.store = store
        self.rowcount = 0
        self._result: List[Tuple] = []
        self._next_id = store.setdefault("_next_id", 1)

    def execute(self, sql: str, params: Optional[Tuple] = None):
        params = params or ()
        sql_n = " ".join(sql.split())
        if "FROM Procurement.PedidoPresets ORDER BY Nombre" in sql_n:
            rows = sorted(self.store["rows"].values(), key=lambda r: r[1])
            self._result = list(rows)
            return
        if "WHERE PresetId = ?" in sql_n and "SELECT" in sql_n:
            pid = int(params[0])
            row = self.store["rows"].get(pid)
            self._result = [row] if row else []
            return
        if "WHERE Nombre = ?" in sql_n and "SELECT" in sql_n:
            name = params[0]
            for row in self.store["rows"].values():
                if row[1] == name:
                    self._result = [row]
                    return
            self._result = []
            return
        if sql_n.startswith("INSERT INTO Procurement.PedidoPresets"):
            pid = self.store["_next_id"]
            self.store["_next_id"] = pid + 1
            row = (pid, params[0], params[1], params[2], params[3], None, None)
            self.store["rows"][pid] = row
            self._result = [(pid,)]
            self.rowcount = 1
            return
        if sql_n.startswith("UPDATE Procurement.PedidoPresets") and "WHERE PresetId = ?" in sql_n:
            pid = int(params[4])
            if pid not in self.store["rows"]:
                self.rowcount = 0
                self._result = []
                return
            self.store["rows"][pid] = (
                pid, params[0], params[1], params[2], params[3], None, None
            )
            self.rowcount = 1
            return
        if sql_n.startswith("UPDATE Procurement.PedidoPresets") and "WHERE Nombre = ?" in sql_n:
            name = params[3]
            for pid, row in list(self.store["rows"].items()):
                if row[1] == name:
                    self.store["rows"][pid] = (
                        pid, name, params[0], params[1], params[2], None, None
                    )
                    self.rowcount = 1
                    return
            self.rowcount = 0
            return
        if sql_n.startswith("DELETE FROM Procurement.PedidoPresets"):
            pid = int(params[0])
            if pid in self.store["rows"]:
                del self.store["rows"][pid]
                self.rowcount = 1
            else:
                self.rowcount = 0
            return
        raise AssertionError(f"unexpected SQL: {sql_n}")

    def fetchall(self):
        return list(self._result)

    def fetchone(self):
        return self._result[0] if self._result else None


class FakeConn:
    def __init__(self):
        self.store: dict = {"rows": {}, "_next_id": 1}

    def cursor(self):
        return FakeCursor(self.store)

    def commit(self):
        pass


def test_upsert_list_delete_preset_roundtrip():
    conn = FakeConn()
    saved = svc.upsert_preset(
        conn,
        nombre="Mi Agresivo Soft",
        nivel="Avanzado",
        base_preset="Agresivo",
        overrides={"opp_lambda": 1.2, "split_lead_time_enabled": True},
    )
    assert saved["preset_id"] == 1
    assert saved["nombre"] == "Mi Agresivo Soft"
    assert saved["overrides"]["opp_lambda"] == 1.2

    listed = svc.list_presets(conn)
    assert len(listed) == 1
    assert listed[0]["base_preset"] == "Agresivo"

    again = svc.upsert_preset(
        conn,
        nombre="Mi Agresivo Soft",
        nivel="Intermedio",
        base_preset="Normal",
        overrides={"w1": 0.5},
    )
    assert again["preset_id"] == 1
    assert again["nivel"] == "Intermedio"
    assert again["overrides"] == {"w1": 0.5}

    assert svc.delete_preset(conn, 1) is True
    assert svc.list_presets(conn) == []
    assert svc.delete_preset(conn, 1) is False


def test_upsert_rejects_bad_nivel():
    conn = FakeConn()
    try:
        svc.upsert_preset(
            conn, nombre="x", nivel="Basico", base_preset="Normal", overrides={}
        )
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "nivel" in str(exc)
