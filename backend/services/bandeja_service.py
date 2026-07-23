"""Bandeja de pedidos — list / snapshot / patch / clone / approve / reject — ADR-0030."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from analytics_engine.core.borrador_snapshot import (
    build_desviacion_rows,
    count_desviaciones,
    dumps_json,
    loads_json,
    snapshot_hash,
)

logger = logging.getLogger(__name__)

TAB_ESTADOS = {
    "por_enviar": ("BORRADOR", "FALLIDO_ENVIO"),
    "por_aprobar": ("PENDIENTE_APROBACION",),
    "historial": ("ENVIADO", "RECHAZADO"),
}


def _row_cab(r: Any) -> Dict[str, Any]:
    # support both pyodbc Row and tuple with known order
    def g(name: str, idx: int, default=None):
        try:
            if hasattr(r, name):
                return getattr(r, name)
        except Exception:
            pass
        try:
            return r[idx]
        except Exception:
            return default

    estado = str(g("Estado", 2) or "")
    return {
        "propuesta_id": int(g("PropuestaID", 0)),
        "cod_prov": str(g("CodProv", 1) or "").strip(),
        "estado": estado,
        "fecha_generacion": str(g("FechaGeneracion", 3) or ""),
        "total_lineas": int(g("TotalLineas", 4) or 0),
        "total_unidades": int(g("TotalUnidades", 5) or 0),
        "monto_total_usd": float(g("MontoTotalUSD", 6)) if g("MontoTotalUSD", 6) is not None else None,
        "revision": int(g("Revision", 7) or 1),
        "snapshot_hash": g("SnapshotHash", 8),
        "motivo_rechazo": g("MotivoRechazo", 9),
        "desviaciones": int(g("Desviaciones", 10) or 0) if g("Desviaciones", 10) is not None else None,
    }


def list_bandeja(
    conn: Any,
    *,
    tab: str = "por_enviar",
    limit: int = 100,
) -> List[Dict[str, Any]]:
    estados = TAB_ESTADOS.get(tab) or TAB_ESTADOS["por_enviar"]
    placeholders = ", ".join("?" for _ in estados)
    sql = f"""
    SELECT TOP ({int(limit)})
        c.PropuestaID, c.CodProv, c.Estado, c.FechaGeneracion,
        c.TotalLineas, c.TotalUnidades, c.MontoTotalUSD,
        ISNULL(c.Revision, 1) AS Revision,
        c.SnapshotHash, c.MotivoRechazo,
        NULL AS Desviaciones
    FROM Procurement.BorradorPedidosCabecera c
    WHERE c.Estado IN ({placeholders})
    ORDER BY c.FechaGeneracion DESC
    """
    cur = conn.cursor()
    cur.execute(sql, tuple(estados))
    rows = cur.fetchall()
    out = []
    for r in rows:
        item = _row_cab(r)
        # enrich desviaciones from snapshot if present
        try:
            snap = get_comparativa(conn, item["propuesta_id"])
            if snap:
                item["desviaciones"] = count_desviaciones(
                    snap.get("comparativa_cantidades") or []
                )
                item["tiene_snapshot"] = True
            else:
                item["tiene_snapshot"] = False
                item["desviaciones"] = item["desviaciones"] if item["desviaciones"] is not None else 0
        except Exception:
            item["tiene_snapshot"] = False
            item["desviaciones"] = 0
        out.append(item)
    return out


def bandeja_counts(conn: Any) -> Dict[str, int]:
    sql = """
    SELECT Estado, COUNT(*) AS N
    FROM Procurement.BorradorPedidosCabecera
    WHERE Estado IN ('BORRADOR', 'FALLIDO_ENVIO', 'PENDIENTE_APROBACION')
    GROUP BY Estado
    """
    cur = conn.cursor()
    cur.execute(sql)
    by = {str(r[0]): int(r[1]) for r in cur.fetchall()}
    return {
        "por_enviar": by.get("BORRADOR", 0) + by.get("FALLIDO_ENVIO", 0),
        "por_aprobar": by.get("PENDIENTE_APROBACION", 0),
    }


def get_comparativa(conn: Any, propuesta_id: int) -> Optional[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.PropuestaID, c.CodProv, c.Estado, ISNULL(c.Revision, 1), c.SnapshotHash,
               s.ComparativaJson, s.PedidoPropuestoJson, s.FechaActualizacion
        FROM Procurement.BorradorPedidosCabecera c
        LEFT JOIN Procurement.BorradorPedidosComparativa s ON s.PropuestaID = c.PropuestaID
        WHERE c.PropuestaID = ?
        """,
        (propuesta_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    comparativa = loads_json(row[5], []) or []
    propuesto = loads_json(row[6], []) or []
    # Fallback: rebuild propuesto from lineas if snapshot empty
    if not propuesto:
        cur.execute(
            """
            SELECT CodProd, Descrip, CantidadPropuesta, CostoCalculadoUSD
            FROM Procurement.BorradorPedidosLineas
            WHERE PropuestaID = ?
            """,
            (propuesta_id,),
        )
        propuesto = [
            {
                "barra": str(r[0] or "").strip(),
                "descripcion": r[1],
                "proveedor": str(row[1] or "").strip(),
                "cantidad": int(r[2] or 0),
                "precio": float(r[3]) if r[3] is not None else None,
            }
            for r in cur.fetchall()
        ]
    desv = build_desviacion_rows(comparativa)
    return {
        "propuesta_id": int(row[0]),
        "cod_prov": str(row[1] or "").strip(),
        "estado": str(row[2] or ""),
        "revision": int(row[3] or 1),
        "snapshot_hash": row[4],
        "comparativa_cantidades": comparativa,
        "pedido_propuesto": propuesto,
        "desviaciones": len(desv),
        "desviacion_rows": desv,
        "fecha_actualizacion": str(row[7] or ""),
    }


def _recalc_totals(propuesto: Sequence[Dict[str, Any]]) -> Tuple[int, int, Optional[float]]:
    lineas = 0
    unidades = 0
    monto = 0.0
    has_precio = False
    for r in propuesto:
        try:
            qty = int(r.get("cantidad") or 0)
        except (TypeError, ValueError):
            qty = 0
        if qty <= 0:
            continue
        lineas += 1
        unidades += qty
        try:
            precio = float(r.get("precio"))
            monto += qty * precio
            has_precio = True
        except (TypeError, ValueError):
            pass
    return lineas, unidades, (monto if has_precio else None)


def save_snapshot_edits(
    conn: Any,
    propuesta_id: int,
    *,
    pedido_propuesto: List[Dict[str, Any]],
    comparativa_cantidades: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Persist qty edits: bump revision, rewrite lineas + snapshot (ADR-0030 Q7)."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT CodProv, Estado, ISNULL(Revision, 1)
        FROM Procurement.BorradorPedidosCabecera
        WHERE PropuestaID = ?
        """,
        (propuesta_id,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError("propuesta_not_found")
    cod_prov, estado, revision = str(row[0]).strip(), str(row[1]), int(row[2] or 1)
    if estado not in ("BORRADOR", "PENDIENTE_APROBACION", "FALLIDO_ENVIO"):
        raise ValueError(f"estado_no_editable:{estado}")

    # keep existing comparativa if not provided
    if comparativa_cantidades is None:
        cur.execute(
            "SELECT ComparativaJson FROM Procurement.BorradorPedidosComparativa WHERE PropuestaID = ?",
            (propuesta_id,),
        )
        r2 = cur.fetchone()
        comparativa_cantidades = loads_json(r2[0], []) if r2 else []

    # sync qty_propuesto in comparativa by barra_propuesto
    qty_by_barra = {
        str(r.get("barra") or "").strip(): int(r.get("cantidad") or 0)
        for r in pedido_propuesto
        if str(r.get("barra") or "").strip()
    }
    synced_comp = []
    for crow in comparativa_cantidades or []:
        item = dict(crow)
        bp = str(item.get("barra_propuesto") or "").strip()
        if bp in qty_by_barra:
            item["qty_propuesto"] = qty_by_barra[bp]
        synced_comp.append(item)

    new_rev = revision + 1
    snap = snapshot_hash(synced_comp, pedido_propuesto)
    total_lineas, total_unidades, monto = _recalc_totals(pedido_propuesto)

    cur.execute("DELETE FROM Procurement.BorradorPedidosLineas WHERE PropuestaID = ?", (propuesta_id,))
    for r in pedido_propuesto:
        barra = str(r.get("barra") or "").strip()
        if not barra:
            continue
        try:
            qty = int(r.get("cantidad") or 0)
        except (TypeError, ValueError):
            qty = 0
        if qty <= 0:
            continue
        precio = r.get("precio")
        try:
            precio_f = float(precio) if precio is not None else None
        except (TypeError, ValueError):
            precio_f = None
        cur.execute(
            """
            INSERT INTO Procurement.BorradorPedidosLineas
                (PropuestaID, CodProd, Descrip, CantidadPropuesta, CostoBaseBs, CostoCalculadoUSD,
                 InventarioActual, Minimo, Maximo)
            VALUES (?, ?, ?, ?, NULL, ?, NULL, NULL, NULL)
            """,
            (
                propuesta_id,
                barra,
                str(r.get("descripcion") or r.get("descrip") or "")[:150],
                qty,
                precio_f,
            ),
        )

    cur.execute(
        """
        UPDATE Procurement.BorradorPedidosCabecera
        SET Revision = ?, SnapshotHash = ?, TotalLineas = ?, TotalUnidades = ?, MontoTotalUSD = ?
        WHERE PropuestaID = ?
        """,
        (new_rev, snap, total_lineas, total_unidades, monto, propuesta_id),
    )
    cjson = dumps_json(synced_comp)
    pjson = dumps_json(pedido_propuesto)
    cur.execute(
        """
        MERGE Procurement.BorradorPedidosComparativa AS t
        USING (SELECT ? AS PropuestaID) AS s ON t.PropuestaID = s.PropuestaID
        WHEN MATCHED THEN UPDATE SET
            Revision = ?, SnapshotHash = ?, ComparativaJson = ?, PedidoPropuestoJson = ?,
            FechaActualizacion = SYSUTCDATETIME()
        WHEN NOT MATCHED THEN INSERT
            (PropuestaID, Revision, SnapshotHash, ComparativaJson, PedidoPropuestoJson, FechaActualizacion)
        VALUES (?, ?, ?, ?, ?, SYSUTCDATETIME());
        """,
        (
            propuesta_id,
            new_rev,
            snap,
            cjson,
            pjson,
            propuesta_id,
            new_rev,
            snap,
            cjson,
            pjson,
        ),
    )
    return {
        "propuesta_id": propuesta_id,
        "cod_prov": cod_prov,
        "estado": estado,
        "revision": new_rev,
        "snapshot_hash": snap,
        "desviaciones": count_desviaciones(synced_comp),
        "total_lineas": total_lineas,
        "total_unidades": total_unidades,
        "monto_total_usd": monto,
    }


def set_estado(
    conn: Any,
    propuesta_id: int,
    nuevo_estado: str,
    *,
    motivo: Optional[str] = None,
    expected_revision: Optional[int] = None,
    expected_hash: Optional[str] = None,
) -> Dict[str, Any]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT Estado, ISNULL(Revision, 1), SnapshotHash
        FROM Procurement.BorradorPedidosCabecera
        WHERE PropuestaID = ?
        """,
        (propuesta_id,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError("propuesta_not_found")
    estado, revision, snap_hash = str(row[0]), int(row[1] or 1), row[2]
    if expected_revision is not None and int(expected_revision) != revision:
        raise ValueError("revision_stale")
    if expected_hash is not None and snap_hash and str(expected_hash) != str(snap_hash):
        raise ValueError("hash_stale")
    if nuevo_estado == "RECHAZADO" and not (motivo or "").strip():
        raise ValueError("motivo_requerido")
    cur.execute(
        """
        UPDATE Procurement.BorradorPedidosCabecera
        SET Estado = ?, MotivoRechazo = CASE WHEN ? IS NULL THEN MotivoRechazo ELSE ? END
        WHERE PropuestaID = ?
        """,
        (nuevo_estado, motivo, (motivo or "")[:500] if motivo else None, propuesta_id),
    )
    return {
        "propuesta_id": propuesta_id,
        "estado": nuevo_estado,
        "revision": revision,
        "snapshot_hash": snap_hash,
        "estado_previo": estado,
        "motivo_rechazo": motivo,
    }


def clonar_a_borrador(conn: Any, propuesta_id: int) -> Dict[str, Any]:
    """Historial → nueva PropuestaID en BORRADOR with copied lines + snapshot."""
    snap = get_comparativa(conn, propuesta_id)
    if not snap:
        raise ValueError("propuesta_not_found")
    cur = conn.cursor()
    cur.execute(
        """
        SELECT CodProv, ParametrosJson, TotalLineas, TotalUnidades, MontoTotalUSD
        FROM Procurement.BorradorPedidosCabecera WHERE PropuestaID = ?
        """,
        (propuesta_id,),
    )
    cab = cur.fetchone()
    if not cab:
        raise ValueError("propuesta_not_found")
    cod_prov = str(cab[0]).strip()
    # replace existing BORRADOR for same CodProv
    cur.execute(
        """
        DELETE FROM Procurement.BorradorPedidosLineas
        WHERE PropuestaID IN (
            SELECT PropuestaID FROM Procurement.BorradorPedidosCabecera
            WHERE Estado = 'BORRADOR' AND UPPER(LTRIM(RTRIM(CodProv))) = UPPER(LTRIM(RTRIM(?)))
        )
        """
        ,
        (cod_prov,),
    )
    cur.execute(
        """
        DELETE FROM Procurement.BorradorPedidosCabecera
        WHERE Estado = 'BORRADOR' AND UPPER(LTRIM(RTRIM(CodProv))) = UPPER(LTRIM(RTRIM(?)))
        """,
        (cod_prov,),
    )
    propuesto = snap["pedido_propuesto"]
    comparativa = snap["comparativa_cantidades"]
    sh = snapshot_hash(comparativa, propuesto)
    cur.execute(
        """
        INSERT INTO Procurement.BorradorPedidosCabecera
            (CodProv, FechaGeneracion, TotalLineas, TotalUnidades, MontoTotalUSD, TasaCambioBCV,
             Estado, ParametrosJson, Revision, SnapshotHash)
        OUTPUT INSERTED.PropuestaID
        VALUES (?, SYSUTCDATETIME(), ?, ?, ?, NULL, 'BORRADOR', ?, 1, ?)
        """,
        (cod_prov, cab[2], cab[3], cab[4], cab[1], sh),
    )
    new_id = int(cur.fetchone()[0])
    for r in propuesto:
        barra = str(r.get("barra") or "").strip()
        if not barra:
            continue
        qty = int(r.get("cantidad") or 0)
        if qty <= 0:
            continue
        precio = r.get("precio")
        try:
            precio_f = float(precio) if precio is not None else None
        except (TypeError, ValueError):
            precio_f = None
        cur.execute(
            """
            INSERT INTO Procurement.BorradorPedidosLineas
                (PropuestaID, CodProd, Descrip, CantidadPropuesta, CostoBaseBs, CostoCalculadoUSD,
                 InventarioActual, Minimo, Maximo)
            VALUES (?, ?, ?, ?, NULL, ?, NULL, NULL, NULL)
            """,
            (
                new_id,
                barra,
                str(r.get("descripcion") or r.get("descrip") or "")[:150],
                qty,
                precio_f,
            ),
        )
    cjson = dumps_json(comparativa)
    pjson = dumps_json(propuesto)
    cur.execute(
        """
        INSERT INTO Procurement.BorradorPedidosComparativa
            (PropuestaID, Revision, SnapshotHash, ComparativaJson, PedidoPropuestoJson, FechaActualizacion)
        VALUES (?, 1, ?, ?, ?, SYSUTCDATETIME())
        """,
        (new_id, sh, cjson, pjson),
    )
    return {
        "propuesta_id": new_id,
        "cod_prov": cod_prov,
        "estado": "BORRADOR",
        "revision": 1,
        "snapshot_hash": sh,
        "clonado_desde": propuesta_id,
    }


def run_ttl_job(conn: Any, *, now: Optional[datetime] = None) -> Dict[str, Any]:
    """ADR-0030 TTL: purge BORRADOR 24h; auto-reject PENDIENTE/FALLIDO 72h; purge Comp ENVIADO>7d."""
    now = now or datetime.now(timezone.utc)
    cur = conn.cursor()
    stats = {"borrador_purged": 0, "auto_rechazados": 0, "comp_purged": 0, "avisos": 0}

    # avisos at 48h for PENDIENTE/FALLIDO still <72h
    cur.execute(
        """
        UPDATE Procurement.BorradorPedidosCabecera
        SET AvisoTTLEnviado = 1
        WHERE Estado IN ('PENDIENTE_APROBACION', 'FALLIDO_ENVIO')
          AND ISNULL(AvisoTTLEnviado, 0) = 0
          AND FechaGeneracion <= DATEADD(hour, -48, SYSUTCDATETIME())
          AND FechaGeneracion > DATEADD(hour, -72, SYSUTCDATETIME())
        """
    )
    stats["avisos"] = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0

    cur.execute(
        """
        UPDATE Procurement.BorradorPedidosCabecera
        SET Estado = 'RECHAZADO',
            MotivoRechazo = CASE
                WHEN Estado = 'PENDIENTE_APROBACION' THEN N'expirado'
                ELSE N'fallido expirado'
            END
        WHERE Estado IN ('PENDIENTE_APROBACION', 'FALLIDO_ENVIO')
          AND FechaGeneracion <= DATEADD(hour, -72, SYSUTCDATETIME())
        """
    )
    stats["auto_rechazados"] = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0

    # purge BORRADOR > 24h (lineas cascade if FK; else delete lineas then cab; comparativa CASCADE)
    cur.execute(
        """
        SELECT PropuestaID FROM Procurement.BorradorPedidosCabecera
        WHERE Estado = 'BORRADOR'
          AND FechaGeneracion <= DATEADD(hour, -24, SYSUTCDATETIME())
        """
    )
    ids = [int(r[0]) for r in cur.fetchall()]
    for pid in ids:
        cur.execute("DELETE FROM Procurement.BorradorPedidosLineas WHERE PropuestaID = ?", (pid,))
        cur.execute("DELETE FROM Procurement.BorradorPedidosCabecera WHERE PropuestaID = ?", (pid,))
    stats["borrador_purged"] = len(ids)

    # purge Comparativa blob for ENVIADO/RECHAZADO older than 7d (keep cabecera)
    cur.execute(
        """
        DELETE s
        FROM Procurement.BorradorPedidosComparativa s
        INNER JOIN Procurement.BorradorPedidosCabecera c ON c.PropuestaID = s.PropuestaID
        WHERE c.Estado IN ('ENVIADO', 'RECHAZADO')
          AND ISNULL(s.FechaActualizacion, c.FechaGeneracion) <= DATEADD(day, -7, SYSUTCDATETIME())
        """
    )
    stats["comp_purged"] = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
    return stats
