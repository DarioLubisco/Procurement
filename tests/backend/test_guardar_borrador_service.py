"""persist_borradores replace-all semantics with fake cursor — ADR-0018."""
from __future__ import annotations

from unittest.mock import MagicMock

from analytics_engine.core.guardar_borrador import (
    BorradorCabeceraPlan,
    BorradorLineaPlan,
    GuardarBorradorPlan,
)
from backend.services.guardar_borrador_service import persist_borradores


def test_persist_deletes_all_borrador_then_inserts():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    # OUTPUT INSERTED.PropuestaID
    cur.fetchone.return_value = (42,)

    plan = GuardarBorradorPlan(
        cabeceras=[
            BorradorCabeceraPlan(
                cod_prov="DROCERCA",
                proveedor_id=1,
                nombre_corto="Drocerca",
                lineas=[
                    BorradorLineaPlan(
                        cod_prod="A",
                        descrip="Prod A",
                        cantidad_propuesta=4,
                        costo_calculado_usd=2.5,
                    )
                ],
                parametros_json='{"nivel":"Intermedio"}',
            )
        ]
    )
    written = persist_borradores(conn, plan)
    assert written[0]["propuesta_id"] == 42
    sqls = [str(c.args[0]) for c in cur.execute.call_args_list]
    assert any("DELETE FROM Procurement.BorradorPedidosLineas" in s for s in sqls)
    assert any("DELETE FROM Procurement.BorradorPedidosCabecera" in s for s in sqls)
    assert any("INSERT INTO Procurement.BorradorPedidosCabecera" in s for s in sqls)
    assert any("INSERT INTO Procurement.BorradorPedidosLineas" in s for s in sqls)
    insert_cab = [
        c
        for c in cur.execute.call_args_list
        if "INSERT INTO Procurement.BorradorPedidosCabecera" in str(c.args[0])
    ]
    assert insert_cab[0].args[1][-1] == '{"nivel":"Intermedio"}'
    delete_cab_calls = [
        c
        for c in cur.execute.call_args_list
        if "DELETE FROM Procurement.BorradorPedidosCabecera" in str(c.args[0])
    ]
    assert delete_cab_calls[0].args[1] == ("DROCERCA",)
