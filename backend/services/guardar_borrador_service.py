"""Persist GuardarBorradorPlan into Procurement.BorradorPedidos* — ADR-0018 + ADR-0030."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Set

from analytics_engine.core.borrador_snapshot import (
    dumps_json,
    filter_comparativa_for_barras,
    filter_propuesto_for_cod_prov,
    snapshot_hash,
)
from analytics_engine.core.guardar_borrador import (
    BorradorCabeceraPlan,
    GuardarBorradorPlan,
)

logger = logging.getLogger(__name__)

_SQL_SAPROD_EXISTS = """
SELECT LTRIM(RTRIM(CodProd)) AS CodProd
FROM dbo.SAPROD
WHERE Activo = 1
  AND LTRIM(RTRIM(CodProd)) IN ({placeholders})
"""

_SQL_DELETE_LINEAS = """
DELETE FROM Procurement.BorradorPedidosLineas
WHERE PropuestaID IN (
    SELECT PropuestaID FROM Procurement.BorradorPedidosCabecera
    WHERE Estado = 'BORRADOR'
      AND UPPER(LTRIM(RTRIM(CodProv))) = UPPER(LTRIM(RTRIM(?)))
)
"""

_SQL_DELETE_CAB = """
DELETE FROM Procurement.BorradorPedidosCabecera
WHERE Estado = 'BORRADOR'
  AND UPPER(LTRIM(RTRIM(CodProv))) = UPPER(LTRIM(RTRIM(?)))
"""

_SQL_INSERT_CAB = """
INSERT INTO Procurement.BorradorPedidosCabecera
    (CodProv, FechaGeneracion, TotalLineas, TotalUnidades, MontoTotalUSD, TasaCambioBCV,
     Estado, ParametrosJson, Revision, SnapshotHash)
OUTPUT INSERTED.PropuestaID
VALUES (?, SYSUTCDATETIME(), ?, ?, ?, NULL, 'BORRADOR', ?, 1, ?)
"""

_SQL_INSERT_LINEA = """
INSERT INTO Procurement.BorradorPedidosLineas
    (PropuestaID, CodProd, Descrip, CantidadPropuesta, CostoBaseBs, CostoCalculadoUSD,
     InventarioActual, Minimo, Maximo)
VALUES (?, ?, ?, ?, NULL, ?, NULL, NULL, NULL)
"""

_SQL_UPSERT_COMPARATIVA = """
MERGE Procurement.BorradorPedidosComparativa AS t
USING (SELECT ? AS PropuestaID) AS s
ON t.PropuestaID = s.PropuestaID
WHEN MATCHED THEN UPDATE SET
    Revision = ?,
    SnapshotHash = ?,
    ComparativaJson = ?,
    PedidoPropuestoJson = ?,
    FechaActualizacion = SYSUTCDATETIME()
WHEN NOT MATCHED THEN INSERT
    (PropuestaID, Revision, SnapshotHash, ComparativaJson, PedidoPropuestoJson, FechaActualizacion)
VALUES (?, ?, ?, ?, ?, SYSUTCDATETIME());
"""


def fetch_saprod_codprods(conn: Any, barras: Sequence[str]) -> Set[str]:
    """Return CodProd values that exist (Activo=1) among the requested barras."""
    clean = sorted({str(b).strip() for b in barras if str(b).strip()})
    if not clean:
        return set()
    out: Set[str] = set()
    # Chunk to stay under parameter limits
    size = 500
    cur = conn.cursor()
    for i in range(0, len(clean), size):
        chunk = clean[i : i + size]
        placeholders = ", ".join("?" for _ in chunk)
        sql = _SQL_SAPROD_EXISTS.format(placeholders=placeholders)
        cur.execute(sql, chunk)
        for row in cur.fetchall():
            cod = str(row[0] or "").strip()
            if cod:
                out.add(cod)
    return out


def _upsert_comparativa(
    cur: Any,
    propuesta_id: int,
    *,
    revision: int,
    snap_hash: str,
    comparativa: List[Dict[str, Any]],
    propuesto: List[Dict[str, Any]],
) -> None:
    cjson = dumps_json(comparativa)
    pjson = dumps_json(propuesto)
    cur.execute(
        _SQL_UPSERT_COMPARATIVA,
        (
            propuesta_id,
            revision,
            snap_hash,
            cjson,
            pjson,
            propuesta_id,
            revision,
            snap_hash,
            cjson,
            pjson,
        ),
    )


def _replace_one(
    cur: Any,
    cab: BorradorCabeceraPlan,
    *,
    comparativa_all: Optional[List[Dict[str, Any]]] = None,
    propuesto_all: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    cur.execute(_SQL_DELETE_LINEAS, (cab.cod_prov,))
    cur.execute(_SQL_DELETE_CAB, (cab.cod_prov,))
    propuesto_f = filter_propuesto_for_cod_prov(
        propuesto_all or [],
        cab.cod_prov,
        proveedor_aliases=[cab.cod_prov],
    )
    # Fallback: rebuild propuesto from plan lineas if FE filter empty
    if not propuesto_f:
        propuesto_f = [
            {
                "barra": lin.cod_prod,
                "descripcion": lin.descrip,
                "proveedor": cab.cod_prov,
                "cantidad": lin.cantidad_propuesta,
                "precio": lin.costo_calculado_usd,
            }
            for lin in cab.lineas
        ]
    barras = [str(r.get("barra") or "").strip() for r in propuesto_f]
    comparativa_f = filter_comparativa_for_barras(comparativa_all or [], barras)
    snap = snapshot_hash(comparativa_f, propuesto_f)
    monto = cab.monto_total_usd
    cur.execute(
        _SQL_INSERT_CAB,
        (
            cab.cod_prov,
            cab.total_lineas,
            cab.total_unidades,
            monto,
            cab.parametros_json,
            snap,
        ),
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"INSERT cabecera sin PropuestaID para {cab.cod_prov}")
    propuesta_id = int(row[0])
    for lin in cab.lineas:
        cur.execute(
            _SQL_INSERT_LINEA,
            (
                propuesta_id,
                lin.cod_prod,
                (lin.descrip or "")[:150],
                lin.cantidad_propuesta,
                lin.costo_calculado_usd,
            ),
        )
    try:
        _upsert_comparativa(
            cur,
            propuesta_id,
            revision=1,
            snap_hash=snap,
            comparativa=comparativa_f,
            propuesto=propuesto_f,
        )
    except Exception as exc:
        # Pre-migration environments: cabecera still saved
        logger.warning(
            "Comparativa snapshot skip PropuestaID=%s: %s", propuesta_id, exc
        )
    return {
        "propuesta_id": propuesta_id,
        "cod_prov": cab.cod_prov,
        "proveedor_id": cab.proveedor_id,
        "total_lineas": cab.total_lineas,
        "total_unidades": cab.total_unidades,
        "monto_total_usd": cab.monto_total_usd,
        "revision": 1,
        "snapshot_hash": snap,
        "desviaciones": None,
    }


def persist_borradores(
    conn: Any,
    plan: GuardarBorradorPlan,
    *,
    comparativa_cantidades: Optional[List[Dict[str, Any]]] = None,
    pedido_propuesto: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """All-or-nothing write of prepared cabeceras. Caller must commit/rollback."""
    if not plan.cabeceras:
        raise ValueError("no_cabeceras_utiles")
    from analytics_engine.core.borrador_snapshot import count_desviaciones

    cur = conn.cursor()
    written: List[Dict[str, Any]] = []
    for cab in plan.cabeceras:
        item = _replace_one(
            cur,
            cab,
            comparativa_all=comparativa_cantidades,
            propuesto_all=pedido_propuesto,
        )
        # recompute desvíos from stored filter
        prop_f = filter_propuesto_for_cod_prov(
            pedido_propuesto or [], cab.cod_prov, proveedor_aliases=[cab.cod_prov]
        )
        barras = [str(r.get("barra") or "").strip() for r in prop_f] or [
            lin.cod_prod for lin in cab.lineas
        ]
        comp_f = filter_comparativa_for_barras(comparativa_cantidades or [], barras)
        item["desviaciones"] = count_desviaciones(comp_f)
        written.append(item)
    return written


def guardar_borradores_from_db(
    plan: GuardarBorradorPlan,
    *,
    conn: Optional[Any] = None,
    comparativa_cantidades: Optional[List[Dict[str, Any]]] = None,
    pedido_propuesto: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Open pool connection if needed; commit on success, rollback on failure."""
    import database

    owns = conn is None
    if owns:
        conn = database.get_db_connection()
    try:
        written = persist_borradores(
            conn,
            plan,
            comparativa_cantidades=comparativa_cantidades,
            pedido_propuesto=pedido_propuesto,
        )
        conn.commit()
        logger.info(
            "Guardar borrador OK: %s cabeceras %s",
            len(written),
            [w["cod_prov"] for w in written],
        )
        return written
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        if owns:
            try:
                conn.close()
            except Exception:
                pass
