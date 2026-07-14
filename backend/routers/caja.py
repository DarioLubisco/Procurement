import os
import io
import uvicorn
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from database import get_db_connection
from datetime import date
from typing import List, Optional
import pyodbc
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

router = APIRouter()

# Pydantic Schemas for validation (Phase 1)
class BilletesItem(BaseModel):
    denominacion: int
    cantidad: int
    total: float

class TarjetaItem(BaseModel):
    tipo: str
    punto_de_venta: str
    referencia: str
    monto: float

class DiferenciaItem(BaseModel):
    category: str
    sistema: float
    manual: float
    diferencia: float

class ConciliarRequest(BaseModel):
    vendedor_codigo: str
    vendedor_nombre: str | None = None
    fecha_ini: str
    fecha_fin: str
    efectivo_desglose: list[BilletesItem] = []
    divisa_desglose: list[BilletesItem] = []
    tarjeta_desglose: list[TarjetaItem] = []
    diferencias: list[DiferenciaItem] = []
    # Totals
    manual_efectivo_bs: float
    manual_divisas: float
    manual_euros: float
    manual_tdd: float
    manual_tdc: float
    manual_biopago: float
    manual_pago_movil: float = 0.0
    manual_transferencia: float = 0.0
    session_token: str | None = None

class RepararFechasRequest(BaseModel):
    fecha_inicio: str
    fecha_fin: str

@router.get("/caja/vendedores")
async def get_vendedores():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT CodVend, Descrip FROM dbo.SAVEND WHERE Activo = 1 ORDER BY Descrip")
        vendedores = [{"codigo": r[0].strip(), "nombre": r[1].strip() if r[1] else r[0].strip()} for r in cursor.fetchall()]
        return {"status": "success", "data": vendedores}
    except pyodbc.Error as strErr:
        raise HTTPException(status_code=500, detail=f"Database error: {str(strErr)}")
    finally:
        cursor.close()
        conn.close()

@router.get("/caja/puntos_venta")
async def get_puntos_venta():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT p.id, p.nombre_pos, p.tipo, b.nombre AS banco_nombre, p.categoria
            FROM Custom.CajaPuntosVenta p
            JOIN Custom.CajaBancos b ON p.banco_id = b.id
            WHERE p.activo = 1 AND b.activo = 1
            ORDER BY p.categoria, b.nombre, p.nombre_pos
        """)
        puntos = [
            {"id": r[0], "nombre": f"{r[1]} ({r[3]})", "tipo": r[2].strip(), "categoria": r[4].strip()}
            for r in cursor.fetchall()
        ]
        return {"status": "success", "data": puntos}
    except pyodbc.Error as strErr:
        raise HTTPException(status_code=500, detail=f"Database error: {str(strErr)}")
    finally:
        cursor.close()
        conn.close()

@router.get("/caja/tasa_del_dia")
async def get_tasa_del_dia():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT TOP 1 DolarBCV FROM dbo.DolarToday ORDER BY Fecha DESC")
        row = cursor.fetchone()
        tasa = float(row[0]) if row else 40.50 # Valor por defecto si no hay datos
        return {"status": "success", "tasa": tasa}
    except pyodbc.Error as strErr:
        raise HTTPException(status_code=500, detail=f"Database error: {str(strErr)}")
    finally:
        cursor.close()
        conn.close()

# Endpoint to test /caja/sistema/totales
@router.get("/caja/sistema/totales")
async def get_totales(vendedor_codigo: str, fecha: str, session_token: str | None = None, force: bool = False):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Base Efectivo (CancelE) ajustado por TipoFac
        cursor.execute("""
            SELECT 
                ISNULL(SUM(CASE WHEN TipoFac = 'C' THEN -CancelE ELSE CancelE END), 0),
                ISNULL(SUM(CASE WHEN TipoFac = 'C' THEN -(Descto1 + Descto2) ELSE (Descto1 + Descto2) END), 0)
            FROM dbo.SAFACT
            WHERE CodVend = ? AND CAST(FechaE AS DATE) = ? AND TipoFac IN ('A', 'C')
        """, (vendedor_codigo, fecha))
        row_fact = cursor.fetchone()
        base_efectivo = float(row_fact[0] if row_fact else 0.0)
        tot_descuento = float(row_fact[1] if row_fact else 0.0)

        # 2. Desglose dinámico usando SAIPAVTA puro con multiplicador de signo
        cursor.execute("""
            SELECT 
                ISNULL(SUM(CASE WHEN t.TipoIns = 2 AND i.CodTarj NOT IN ('006', '021') THEN (CASE WHEN f.TipoFac='C' THEN -i.Monto ELSE i.Monto END) ELSE 0 END), 0) AS TotDispositivos,
                ISNULL(SUM(CASE WHEN t.TipoIns = 3 AND i.CodTarj NOT IN ('006', '021') THEN (CASE WHEN f.TipoFac='C' THEN -i.Monto ELSE i.Monto END) ELSE 0 END), 0) AS TotBancos,
                ISNULL(SUM(CASE WHEN i.CodTarj = '006' THEN (CASE WHEN f.TipoFac='C' THEN -i.Monto ELSE i.Monto END) ELSE 0 END), 0) AS TotEfectivoBs,
                ISNULL(SUM(CASE WHEN t.TipoIns NOT IN (2, 3) AND i.CodTarj NOT IN ('006', '021') THEN (CASE WHEN f.TipoFac='C' THEN -i.Monto ELSE i.Monto END) ELSE 0 END), 0) AS TotOtros,
                ISNULL(SUM(CASE WHEN i.CodTarj = '021' THEN (CASE WHEN f.TipoFac='C' THEN -i.Monto ELSE i.Monto END) ELSE 0 END), 0) AS TotDivisas
            FROM dbo.SAIPAVTA i
            JOIN dbo.SAFACT   f ON i.NumeroD = f.NumeroD AND i.TipoFac = f.TipoFac
            LEFT JOIN dbo.SATARJ t ON i.CodTarj = t.CodTarj
            WHERE f.CodVend = ?
              AND CAST(f.FechaE AS DATE) = ?
              AND f.TipoFac IN ('A', 'C')
        """, (vendedor_codigo, fecha))
        row_elec = cursor.fetchone()
        tot_dispositivos = float(row_elec[0] if row_elec else 0.0)
        tot_bancos       = float(row_elec[1] if row_elec else 0.0)
        tot_efectivo_tarj= float(row_elec[2] if row_elec else 0.0)
        tot_otros        = float(row_elec[3] if row_elec else 0.0)
        tot_divisas      = float(row_elec[4] if row_elec else 0.0)

        # Restamos tot_divisas porque CancelE (base_efectivo) incluye TODO el efectivo (incluyendo dólares)
        # de lo contrario, el sistema suma los dólares en la casilla de Dólares Y en la de Efectivo Bs.
        tot_efectivo_bs = (base_efectivo + tot_efectivo_tarj) - tot_divisas

        # 3. Extraer las devoluciones (Notas de Crédito) de hoy para mostrarlas
        cursor.execute("""
            SELECT f.NumeroD, f.Monto, f.CancelE, f.CancelT
            FROM dbo.SAFACT f
            WHERE f.CodVend = ? AND CAST(f.FechaE AS DATE) = ? AND f.TipoFac = 'C'
        """, (vendedor_codigo, fecha))
        devoluciones = [{"factura": row[0], "monto": float(row[1])} for row in cursor.fetchall()]

        totales_sistema = {
            "totefectivo_bs":  tot_efectivo_bs,
            "totdivisas":      tot_divisas,
            "tottarjeta":      tot_dispositivos + tot_bancos + tot_otros,
            "totdispositivos": tot_dispositivos,
            "totbancos":       tot_bancos,
            "tototros":        tot_otros,
            "totdescuento":    tot_descuento,
            "devoluciones":    devoluciones
        }

        # 2. Check for an active Precierre (estado = 'BORRADOR')
        cursor.execute('''
            SELECT id, manual_efectivo_bs, manual_divisas, manual_euros, manual_tdd, manual_tdc, manual_biopago, manual_pago_movil, ISNULL(manual_transferencia, 0)
            FROM Custom.CajaCierre WITH (UPDLOCK, SERIALIZABLE)
            WHERE vendedor_codigo = ? AND CAST(fecha_ini AS DATE) = ? AND estado = 'BORRADOR'
        ''', (vendedor_codigo, fecha))
        
        borrador_row = cursor.fetchone()
        
        has_precierre = False
        borrador_actual = {}
        
        if borrador_row:
            has_precierre = True
            cierre_id = borrador_row[0]
            
            # Session ownership logic
            if session_token:
                if force:
                    # ⚡ Toma forzada: sobreescribir el token sin condición
                    cursor.execute(
                        "UPDATE Custom.CajaCierre SET session_token = ? WHERE id = ?",
                        (session_token, cierre_id)
                    )
                    conn.commit()
                else:
                    # First-come-first-served: solo tomar si nadie lo ocupa
                    cursor.execute("""
                        UPDATE Custom.CajaCierre
                        SET session_token = ?
                        WHERE id = ? AND (session_token IS NULL OR session_token = '')
                    """, (session_token, cierre_id))
                    conn.commit()

                    # Si rowcount == 0, otra sesión ya lo ocupa → 409 con nombre del dueño
                    if cursor.rowcount == 0:
                        cursor.execute("SELECT session_token FROM Custom.CajaCierre WHERE id = ?", (cierre_id,))
                        owner_row = cursor.fetchone()
                        existing_owner = owner_row[0] if owner_row else None
                        if existing_owner and existing_owner != session_token:
                            owner_display = existing_owner.split('|')[0] if '|' in existing_owner else "otro dispositivo"
                            raise HTTPException(
                                status_code=409,
                                detail=f"CONCURRENCY_ERROR: Este borrador ya está siendo editado por {owner_display}."
                            )
                
            borrador_actual = {
                "cierre_id": cierre_id,
                "manual_efectivo_bs": float(borrador_row[1]),
                "manual_divisas": float(borrador_row[2]),
                "manual_euros": float(borrador_row[3]),
                "manual_tdd": float(borrador_row[4]),
                "manual_tdc": float(borrador_row[5]),
                "manual_biopago": float(borrador_row[6]),
                "manual_pago_movil": float(borrador_row[7] if borrador_row[7] is not None else 0),
                "manual_transferencia": float(borrador_row[8]),
                "detalles_efectivo": [],
                "detalles_tarjetas": []
            }
            
            # Fetch detailed denominations
            cursor.execute("SELECT denominacion, cantidad, total FROM Custom.CajaCierreEfectivo WHERE cierre_id = ?", (cierre_id,))
            borrador_actual["detalles_efectivo"] = [{"denominacion": r[0], "cantidad": r[1], "total": float(r[2])} for r in cursor.fetchall()]
            
            # Fetch detailed card transactions
            cursor.execute("SELECT tipo, punto_de_venta, referencia, monto FROM Custom.CajaCierreTarjeta WHERE cierre_id = ?", (cierre_id,))
            borrador_actual["detalles_tarjetas"] = [{"tipo": r[0], "punto_de_venta": r[1], "referencia": r[2], "monto": float(r[3])} for r in cursor.fetchall()]
            
        return {
            "status": "success",
            "has_precierre": has_precierre,
            "totales_sistema": totales_sistema,
            "borrador_actual": borrador_actual
        }
        
    except pyodbc.Error as strErr:
        raise HTTPException(status_code=500, detail=f"Database error: {str(strErr)}")
    finally:
        cursor.close()
        conn.close()

@router.post("/caja/conciliar/guardar_borrador")
async def guardar_borrador(payload: ConciliarRequest):
    return await _upsert_cierre(payload, estado="BORRADOR")

@router.post("/caja/conciliar/finalizar")
async def finalizar_cuadre(payload: ConciliarRequest):
    return await _upsert_cierre(payload, estado="FINALIZADO")


import logging
logger = logging.getLogger(__name__)

async def _upsert_cierre(payload: ConciliarRequest, estado: str):
    """Core upsert logic for both Precierre and Cierre Definitivo."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    with open(r"c:\Users\DARIO LUBISCO\.gemini\antigravity\scratch\caja_debug.log", "a") as f:
        f.write(f"\n--- _upsert_cierre called ---\n")
        f.write(f"Vendedor: {payload.vendedor_codigo}, Estado: {estado}\n")
        f.write(f"Payload Token: {payload.session_token}\n")
        
    try:
        # Check for an existing BORRADOR to update instead of creating a duplicate
        cursor.execute('''
            SELECT id, session_token FROM Custom.CajaCierre WITH (UPDLOCK, SERIALIZABLE)
            WHERE vendedor_codigo = ?
              AND CAST(fecha_ini AS DATE) = ?
              AND estado = 'BORRADOR'
        ''', (payload.vendedor_codigo, payload.fecha_ini))
        existing = cursor.fetchone()
        
        with open(r"c:\Users\DARIO LUBISCO\.gemini\antigravity\scratch\caja_debug.log", "a") as f:
            if existing:
                f.write(f"Existing ID: {existing[0]}, Existing Token: {existing[1]}\n")
            else:
                f.write("No existing BORRADOR found.\n")
                
        if existing:
            cierre_id = existing[0]
            existing_token = existing[1]
            
            # Optimistic Locking / Multi-tab validation
            if existing_token and payload.session_token and existing_token != payload.session_token:
                with open(r"c:\Users\DARIO LUBISCO\.gemini\antigravity\scratch\caja_debug.log", "a") as f:
                    f.write("-> CONCURRENCY ERROR: Tokens do not match!\n")
                owner_display = existing_token.split('|')[0] if '|' in existing_token else "otro dispositivo"
                conn.rollback()
                raise HTTPException(status_code=409, detail=f"CONCURRENCY_ERROR: Este borrador ya está siendo editado por {owner_display}.")
                
            # Update the header
            cursor.execute('''
                UPDATE Custom.CajaCierre SET
                    vendedor_nombre    = ?,
                    manual_efectivo_bs = ?,
                    manual_divisas     = ?,
                    manual_euros       = ?,
                    manual_tdd         = ?,
                    manual_tdc         = ?,
                    manual_biopago     = ?,
                    manual_pago_movil  = ?,
                    manual_transferencia = ?,
                    estado             = ?,
                    session_token      = ?
                WHERE id = ?
            ''', (payload.vendedor_nombre, payload.manual_efectivo_bs, payload.manual_divisas, payload.manual_euros,
                  payload.manual_tdd, payload.manual_tdc, payload.manual_biopago, payload.manual_pago_movil, payload.manual_transferencia,
                  estado, payload.session_token, cierre_id))
            # Wipe detail tables before re-inserting
            cursor.execute("DELETE FROM Custom.CajaCierreEfectivo WHERE cierre_id = ?", (cierre_id,))
            cursor.execute("DELETE FROM Custom.CajaCierreDivisa    WHERE cierre_id = ?", (cierre_id,))
            cursor.execute("DELETE FROM Custom.CajaCierreTarjeta   WHERE cierre_id = ?", (cierre_id,))
            cursor.execute("DELETE FROM Custom.CajaCierreDiferencia WHERE cierre_id = ?", (cierre_id,))
        else:
            # Insert new header
            cursor.execute('''
                SET NOCOUNT ON;
                INSERT INTO Custom.CajaCierre
                    (vendedor_codigo, vendedor_nombre, fecha_ini, fecha_fin,
                     manual_efectivo_bs, manual_divisas, manual_euros,
                     manual_tdd, manual_tdc, manual_biopago, manual_pago_movil, manual_transferencia, estado, session_token)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (payload.vendedor_codigo, payload.vendedor_nombre,
                  payload.fecha_ini, payload.fecha_fin,
                  payload.manual_efectivo_bs, payload.manual_divisas, payload.manual_euros,
                  payload.manual_tdd, payload.manual_tdc, payload.manual_biopago, payload.manual_pago_movil, payload.manual_transferencia, estado, payload.session_token))
            row = cursor.fetchone()
            if not row:
                raise Exception("No data returned from INSERT statement into CajaCierre")
            cierre_id = int(row[0])
        
        # -- Insert denomination breakdown (Bs) ----------------------------
        for item in payload.efectivo_desglose:
            if item.cantidad > 0:
                cursor.execute(
                    "INSERT INTO Custom.CajaCierreEfectivo (cierre_id, denominacion, cantidad, total) VALUES (?,?,?,?)",
                    (cierre_id, item.denominacion, item.cantidad, item.total)
                )
        
        # -- Insert USD denominations --------------------------------------
        for item in payload.divisa_desglose:
            if item.cantidad > 0:
                cursor.execute(
                    "INSERT INTO Custom.CajaCierreDivisa (cierre_id, moneda, denominacion, cantidad, total) VALUES (?,?,?,?,?)",
                    (cierre_id, 'USD', item.denominacion, item.cantidad, item.total)
                )

        # -- Insert POS tickets --------------------------------------------
        for ticket in payload.tarjeta_desglose:
            cursor.execute(
                "INSERT INTO Custom.CajaCierreTarjeta (cierre_id, tipo, punto_de_venta, referencia, monto) VALUES (?,?,?,?,?)",
                (cierre_id, ticket.tipo, ticket.punto_de_venta, ticket.referencia, ticket.monto)
            )
        
        # -- Insert differences (always, for audit/reporting) --------------
        for diff in payload.diferencias:
            cursor.execute(
                "INSERT INTO Custom.CajaCierreDiferencia (cierre_id, vendedor_codigo, vendedor_nombre, category, sistema, manual) VALUES (?,?,?,?,?,?)",
                (cierre_id, payload.vendedor_codigo, payload.vendedor_nombre, diff.category, diff.sistema, diff.manual)
            )
        
        conn.commit()
        
        msg = "Precierre guardado correctamente" if estado == 'BORRADOR' else "Cierre finalizado y sellado"
        return {"status": "success", "message": msg, "cierre_id": cierre_id}

    except Exception as e:
        conn.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

# -- Módulo de Reportes ------------------------------------------

@router.get("/caja/reportes/lista")
async def listar_reportes(fecha_desde: str, fecha_hasta: str, vendedor_codigo: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = '''
            SELECT id, vendedor_codigo, vendedor_nombre, fecha_ini, estado, 
                   manual_efectivo_bs, manual_divisas, manual_tdd, manual_tdc, manual_biopago, manual_pago_movil
            FROM Custom.CajaCierre
            WHERE CAST(fecha_ini AS DATE) >= ? AND CAST(fecha_ini AS DATE) <= ?
        '''
        params = [fecha_desde, fecha_hasta]
        
        if vendedor_codigo:
            query += " AND vendedor_codigo = ?"
            params.append(vendedor_codigo)
            
        query += " ORDER BY fecha_ini DESC"
        
        cursor.execute(query, params)
        cols = [column[0] for column in cursor.description]
        cierres = [dict(zip(cols, row)) for row in cursor.fetchall()]
        
        for c in cierres:
            c['manual_efectivo_bs'] = float(c['manual_efectivo_bs'] or 0)
            c['manual_divisas'] = float(c['manual_divisas'] or 0)
            c['manual_tdd'] = float(c['manual_tdd'] or 0)
            c['manual_tdc'] = float(c['manual_tdc'] or 0)
            c['manual_biopago'] = float(c['manual_biopago'] or 0)
            c['manual_pago_movil'] = float(c['manual_pago_movil'] or 0)
            
        return {"status": "success", "data": cierres}
    except pyodbc.Error as strErr:
        raise HTTPException(status_code=500, detail=f"Database error: {str(strErr)}")
    finally:
        cursor.close()
        conn.close()

@router.get("/caja/reportes/detalle/{cierre_id}")
async def detalle_reporte(cierre_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, vendedor_codigo, vendedor_nombre, fecha_ini, estado, manual_efectivo_bs, manual_divisas, manual_tdd, manual_tdc, manual_biopago, manual_pago_movil, ISNULL(manual_transferencia, 0) FROM Custom.CajaCierre WHERE id = ?", (cierre_id,))
        header_row = cursor.fetchone()
        if not header_row:
            raise HTTPException(status_code=404, detail="Cierre no encontrado")
            
        header = {
            "id": header_row[0], "vendedor_codigo": header_row[1], "vendedor_nombre": header_row[2],
            "fecha_ini": header_row[3], "estado": header_row[4],
            "manual_efectivo_bs": float(header_row[5] or 0), "manual_divisas": float(header_row[6] or 0),
            "manual_tdd": float(header_row[7] or 0), "manual_tdc": float(header_row[8] or 0),
            "manual_biopago": float(header_row[9] or 0), "manual_pago_movil": float(header_row[10] or 0),
            "manual_transferencia": float(header_row[11])
        }
            
        # Differences
        cursor.execute("SELECT category, sistema, manual FROM Custom.CajaCierreDiferencia WHERE cierre_id = ?", (cierre_id,))
        diferencias = [{"category": r[0], "sistema": float(r[1]), "manual": float(r[2]), "diferencia": float(r[2]-r[1])} for r in cursor.fetchall()]
        
        # Tickets
        cursor.execute("SELECT tipo, punto_de_venta, referencia, monto FROM Custom.CajaCierreTarjeta WHERE cierre_id = ?", (cierre_id,))
        tickets = [{"tipo": r[0], "punto_de_venta": r[1], "referencia": r[2], "monto": float(r[3])} for r in cursor.fetchall()]
        
        # Billetes
        cursor.execute("SELECT denominacion, cantidad, total FROM Custom.CajaCierreEfectivo WHERE cierre_id = ?", (cierre_id,))
        efectivo = [{"denominacion": r[0], "cantidad": r[1], "total": float(r[2])} for r in cursor.fetchall()]
        
        cursor.execute("SELECT denominacion, cantidad, total FROM Custom.CajaCierreDivisa WHERE cierre_id = ?", (cierre_id,))
        divisas = [{"denominacion": r[0], "cantidad": r[1], "total": float(r[2])} for r in cursor.fetchall()]

        return {
            "status": "success", 
            "data": {
                "header": header,
                "diferencias": diferencias,
                "tickets": tickets,
                "efectivo": efectivo,
                "divisas": divisas
            }
        }
    except pyodbc.Error as strErr:
        raise HTTPException(status_code=500, detail=f"Database error: {str(strErr)}")
    finally:
        cursor.close()
        conn.close()

# -- Admin: Autenticación y Panel Global --------------------------------------

@router.get("/caja/usuario/perfil")
async def get_perfil_usuario(cod_usua: str):
    """
    Consulta SSUSRS para obtener el perfil del usuario: 
    su nombre, nivel (1=admin, 4=vendedor), el código de vendedor asociado,
    y si estí¡ activo.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT CodUsua, Descrip, Level, CodVend, Activo FROM SSUSRS WHERE CodUsua = ? AND Activo = 1",
            (cod_usua,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario no encontrado o inactivo")
        
        nivel = int(row[2]) if row[2] is not None else 4
        # Level 1 = SuperAdmin, Level 2 = Supervisor/Admin â€“ ambos tienen acceso al Panel Global
        es_admin = (nivel <= 2)
        
        return {
            "status": "success",
            "data": {
                "cod_usua": str(row[0]).strip(),
                "nombre": str(row[1]).strip(),
                "level": nivel,
                "es_admin": es_admin,
                "cod_vend": str(row[3]).strip() if row[3] else None,
                "activo": bool(row[4])
            }
        }
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@router.get("/caja/admin/resumen_diario")
async def get_resumen_diario(fecha: str):
    """
    Vista exclusiva del Administrador:
    - Muestra todos los vendedores activos con ventas ese día.
    - Indica si tienen un cierre FINALIZADO o BORRADOR o si estí¡n PENDIENTES.
    - Incluye los totales del sistema (desde SAFACT) para cada uno.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Totales del sistema por vendedor para la fecha indicada
        cursor.execute('''
            WITH TotalesFactura AS (
                SELECT 
                    f.CodVend,
                    COUNT(f.NumeroD) AS nro_facturas,
                    SUM(ISNULL(CASE WHEN f.TipoFac='C' THEN -f.CancelE ELSE f.CancelE END, 0)) AS base_efectivo,
                    SUM(ISNULL(CASE WHEN f.TipoFac='C' THEN -f.CancelT ELSE f.CancelT END, 0)) AS base_tarjeta,
                    SUM(ISNULL(CASE WHEN f.TipoFac='C' THEN -(f.Descto1 + f.Descto2) ELSE (f.Descto1 + f.Descto2) END, 0)) AS tot_descuento
                FROM dbo.SAFACT f
                WHERE CAST(f.FechaE AS DATE) = ?
                  AND f.TipoFac IN ('A', 'C')
                GROUP BY f.CodVend
            ),
            EfecEnTarj AS (
                SELECT 
                    f.CodVend,
                    SUM(ISNULL(i.Monto, 0)) AS efec_tarj
                FROM dbo.SAIPAVTA i
                JOIN dbo.SAFACT f ON i.NumeroD = f.NumeroD AND i.TipoFac = f.TipoFac
                WHERE CAST(f.FechaE AS DATE) = ?
                  AND f.TipoFac IN ('A', 'C')
                  AND i.CodTarj = '006'
                GROUP BY f.CodVend
            )
            SELECT 
                t.CodVend,
                v.Descrip AS nombre,
                t.base_efectivo + ISNULL(e.efec_tarj, 0) AS tot_efectivo_sis,
                t.base_tarjeta - ISNULL(e.efec_tarj, 0) AS tot_tarjeta_sis,
                t.nro_facturas,
                t.tot_descuento
            FROM TotalesFactura t
            JOIN dbo.SAVEND v ON t.CodVend = v.CodVend
            LEFT JOIN EfecEnTarj e ON t.CodVend = e.CodVend
        ''', (fecha, fecha))
        
        vendedores_sis = {}
        for r in cursor.fetchall():
            vendedores_sis[str(r[0]).strip()] = {
                "cod_vend": str(r[0]).strip(),
                "nombre": str(r[1]).strip(),
                "tot_efectivo_sis": float(r[2]),
                "tot_tarjeta_sis": float(r[3]),
                "nro_facturas": int(r[4]),
                "tot_descuento": float(r[5]),
                "estado_cierre": "PENDIENTE",
                "cierre_id": None,
                "manual_efectivo_bs": 0.0,
                "manual_total_pos": 0.0,
            }
        
        # 2. Verificar el estado del cierre de cada vendedor
        cursor.execute('''
            SELECT vendedor_codigo, id, estado, 
                   manual_efectivo_bs, manual_divisas,
                   manual_tdd, manual_tdc, manual_biopago, manual_pago_movil
            FROM Custom.CajaCierre
            WHERE CAST(fecha_ini AS DATE) = ?
        ''', (fecha,))
        
        for r in cursor.fetchall():
            cod = str(r[0]).strip()
            if cod in vendedores_sis:
                vendedores_sis[cod]["estado_cierre"] = str(r[2]).strip()
                vendedores_sis[cod]["cierre_id"] = int(r[1])
                vendedores_sis[cod]["manual_efectivo_bs"] = float(r[3] or 0)
                # Sumar todos los electrónicos para el resumen
                vendedores_sis[cod]["manual_total_pos"] = float((r[5] or 0) + (r[6] or 0) + (r[7] or 0) + (r[8] or 0))
        
        # 3. Totales globales
        resultado = list(vendedores_sis.values())
        total_global_sis = sum(v["tot_efectivo_sis"] + v["tot_tarjeta_sis"] for v in resultado)
        total_global_manual = sum(v["manual_efectivo_bs"] + v["manual_total_pos"] for v in resultado)
        
        pendientes = [v for v in resultado if v["estado_cierre"] == "PENDIENTE"]
        borradores = [v for v in resultado if v["estado_cierre"] == "BORRADOR"]
        finalizados = [v for v in resultado if v["estado_cierre"] == "FINALIZADO"]
        
        return {
            "status": "success",
            "fecha": fecha,
            "resumen": {
                "total_vendedores": len(resultado),
                "pendientes": len(pendientes),
                "borradores": len(borradores),
                "finalizados": len(finalizados),
                "total_global_sistema": total_global_sis,
                "total_global_manual": total_global_manual,
                "diferencia_global": total_global_manual - total_global_sis
            },
            "data": sorted(resultado, key=lambda x: x["nombre"])
        }
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


# -- Calculadora Mixta â€” Modelo de datos --------------------------------------
class GuardarTransaccionRequest(BaseModel):
    vendedor_codigo: str | None = None
    observacion: str | None = None
    tasa_bcv: float
    # Factura
    factura_bs: float
    factura_usd: float
    # Entradas USD
    rec_ef_usd: float = 0.0
    rec_on_usd: float = 0.0
    # Entradas Bs
    rec_ef_bs: float = 0.0
    rec_pm_bs: float = 0.0
    rec_bio_bs: float = 0.0
    # Totales recibidos
    total_rec_usd: float = 0.0
    total_rec_bs: float = 0.0
    # Vuelto
    vuelto_usd: float = 0.0
    vuelto_bs: float = 0.0
    vuelto_pm_bs: float = 0.0
    total_vuelto_usd: float = 0.0
    # Resultado
    resultado: str = "EXACTO"
    diff_usd: float = 0.0
    diff_bs: float = 0.0


@router.post("/caja/calculadora/guardar")
async def guardar_transaccion(payload: GuardarTransaccionRequest):
    """Persiste una transacción de la Calculadora Mixta."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SET NOCOUNT ON;
            INSERT INTO Custom.CajaTransaccionesDolares
                (vendedor_codigo, observacion, tasa_bcv,
                 factura_bs, factura_usd,
                 rec_ef_usd, rec_on_usd,
                 rec_ef_bs, rec_pm_bs, rec_bio_bs,
                 total_rec_usd, total_rec_bs,
                 vuelto_usd, vuelto_bs, vuelto_pm_bs, total_vuelto_usd,
                 resultado, diff_usd, diff_bs)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);
            
            SELECT SCOPE_IDENTITY(), GETDATE();
        ''', (
            payload.vendedor_codigo, payload.observacion, payload.tasa_bcv,
            payload.factura_bs, payload.factura_usd,
            payload.rec_ef_usd, payload.rec_on_usd,
            payload.rec_ef_bs, payload.rec_pm_bs, payload.rec_bio_bs,
            payload.total_rec_usd, payload.total_rec_bs,
            payload.vuelto_usd, payload.vuelto_bs, payload.vuelto_pm_bs, payload.total_vuelto_usd,
            payload.resultado, payload.diff_usd, payload.diff_bs
        ))
        row = cursor.fetchone()
        if not row:
            raise Exception("No data returned from INSERT statement (fetchone returned None)")
        
        conn.commit()
        return {
            "status": "success",
            "message": "Transacción guardada",
            "id": row[0],
            "fecha": str(row[1])
        }
    except Exception as e:
        conn.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

@router.delete("/caja/calculadora/transaccion/{transaccion_id}")
async def eliminar_transaccion_dolares(transaccion_id: int, cod_usua: str):
    """Anula una transacción del registro histórico de la Calculadora Mixta. Requiere permisos Admin."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check permissions
        cursor.execute("SELECT Level FROM SSUSRS WHERE CodUsua = ? AND Activo = 1", (cod_usua,))
        user_db = cursor.fetchone()
        if not user_db or int(user_db[0] if user_db[0] is not None else 4) > 2:
            raise HTTPException(status_code=403, detail="Permisos insuficientes. Sólo administradores pueden anular transacciones.")

        cursor.execute("UPDATE Custom.CajaTransaccionesDolares SET anulado = 1, observacion = ISNULL(CAST(observacion AS VARCHAR(MAX)), '') + ' [ANULADO]' WHERE id = ?", (transaccion_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Transacción no encontrada")
        conn.commit()
        return {"status": "success", "message": "Transacción eliminada correctamente."}
    except pyodbc.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

@router.get("/caja/calculadora/reporte")
async def reporte_dolares(fecha: str | None = None, vendedor_codigo: str | None = None):
    """
    Retorna el resumen de dólares del día (o de la fecha indicada):
    - Total efectivo USD recibido
    - Total Zelle recibido
    - Total vuelto USD dado
    - Saldo neto USD en caja
    - Últimas N transacciones
    Filtra opcionalmente por un vendedor en específico.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if not fecha:
            fecha = date.today().isoformat()

        # Armar lógica condicional de filtrado para el vendedor
        filtro_vend_sql = ""
        params_summary = [fecha]
        if vendedor_codigo:
            filtro_vend_sql = " AND vendedor_codigo = ?"
            params_summary.append(vendedor_codigo)

        cursor.execute(f'''
            SELECT
                COUNT(*)                              AS nro_transacciones,
                ISNULL(SUM(rec_ef_usd), 0)            AS total_efectivo_usd,
                ISNULL(SUM(rec_on_usd), 0)            AS total_zelle_usd,
                ISNULL(SUM(rec_ef_usd + rec_on_usd), 0) AS total_entrada_usd,
                ISNULL(SUM(rec_ef_bs),  0)            AS total_entrada_bs_ef,
                ISNULL(SUM(rec_pm_bs),  0)            AS total_entrada_bs_pm,
                ISNULL(SUM(rec_bio_bs), 0)            AS total_entrada_bs_bio,
                ISNULL(SUM(vuelto_usd), 0)            AS total_vuelto_usd,
                ISNULL(SUM(rec_ef_usd + rec_on_usd), 0)
                    - ISNULL(SUM(vuelto_usd), 0)      AS saldo_usd_caja
            FROM Custom.CajaTransaccionesDolares
            WHERE CAST(fecha AS DATE) = ? AND anulado = 0 {filtro_vend_sql}
        ''', tuple(params_summary))
        summary_row = cursor.fetchone()

        summary = {
            "fecha": fecha,
            "nro_transacciones": int(summary_row[0]),
            "total_efectivo_usd": float(summary_row[1]),
            "total_zelle_usd":    float(summary_row[2]),
            "total_entrada_usd":  float(summary_row[3]),
            "total_entrada_bs_ef": float(summary_row[4]),
            "total_entrada_bs_pm": float(summary_row[5]),
            "total_entrada_bs_bio": float(summary_row[6]),
            "total_vuelto_usd":   float(summary_row[7]),
            "saldo_usd_caja":     float(summary_row[8]),
        }

        # Últimas 50 transacciones del día
        cursor.execute(f'''
            SELECT TOP 50
                id, fecha, vendedor_codigo, observacion, tasa_bcv,
                factura_bs, factura_usd,
                rec_ef_usd, rec_on_usd, rec_ef_bs, rec_pm_bs, rec_bio_bs,
                total_rec_usd, total_rec_bs,
                vuelto_usd, vuelto_bs, vuelto_pm_bs, total_vuelto_usd,
                resultado, diff_usd, diff_bs, anulado
            FROM Custom.CajaTransaccionesDolares
            WHERE CAST(fecha AS DATE) = ? {filtro_vend_sql}
            ORDER BY id DESC
        ''', tuple(params_summary))

        cols = [c[0] for c in cursor.description]
        transacciones = [dict(zip(cols, row)) for row in cursor.fetchall()]
        # Serialise datetime/decimal
        for t in transacciones:
            for k, v in t.items():
                if hasattr(v, 'isoformat'):
                    t[k] = v.isoformat()
                elif v is None:
                    t[k] = None
                else:
                    try:
                        t[k] = float(v)
                    except (TypeError, ValueError):
                        t[k] = str(v)

        return {"status": "success", "summary": summary, "transacciones": transacciones}

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


# -- PDF Reporte de Cierre -----------------------------------------------------

@router.get("/caja/reportes/{cierre_id}/pdf")
async def generar_pdf_cierre(cierre_id: int):
    """Genera un PDF del precierre o cierre de caja. Funciona para BORRADOR y FINALIZADO."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Cabecera del cierre
        cursor.execute("""
            SELECT id, vendedor_codigo, vendedor_nombre, fecha_ini, estado,
                   manual_efectivo_bs, manual_divisas, manual_tdd, manual_tdc,
                   manual_biopago, manual_pago_movil, ISNULL(manual_transferencia, 0)
            FROM Custom.CajaCierre WHERE id = ?
        """, (cierre_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Cierre no encontrado")

        cierre = {
            "id": row[0], "cod_vend": str(row[1]).strip(),
            "nombre": str(row[2]).strip() if row[2] else str(row[1]).strip(),
            "fecha": str(row[3])[:10], "estado": str(row[4]).strip(),
            "ef_bs": float(row[5] or 0), "divisas": float(row[6] or 0),
            "tdd": float(row[7] or 0), "tdc": float(row[8] or 0),
            "biopago": float(row[9] or 0), "pago_movil": float(row[10] or 0),
            "transferencia": float(row[11] or 0),
        }

        # 2. Última venta del vendedor ese día (hora de factura)
        cursor.execute("""
            SELECT TOP 1 CONVERT(varchar(8), FechaE, 8) as hora, NumeroD
            FROM dbo.SAFACT
            WHERE CodVend = ? AND CAST(FechaE AS DATE) = ? AND TipoFac IN ('A','C')
            ORDER BY FechaE DESC
        """, (cierre["cod_vend"], cierre["fecha"]))
        ult_vta = cursor.fetchone()
        hora_ultima_venta = str(ult_vta[0]).strip() if ult_vta else "--:--:--"
        ultima_factura = str(ult_vta[1]).strip() if ult_vta else "N/A"

        # 3. Totales detallados del sistema para ese vendedor ese día
        cursor.execute("""
            SELECT 
                -- Efectivo y Divisas
                ISNULL(SUM(CASE WHEN i.CodTarj = '006' THEN (CASE WHEN f.TipoFac='C' THEN -i.Monto ELSE i.Monto END) ELSE 0 END), 0) AS sis_ef_bs_tarj,
                ISNULL(SUM(CASE WHEN i.CodTarj = '021' THEN (CASE WHEN f.TipoFac='C' THEN -i.Monto ELSE i.Monto END) ELSE 0 END), 0) AS sis_divisas_bs,
                -- Dispositivos POS (TipoIns 2)
                ISNULL(SUM(CASE WHEN t.TipoIns = 2 AND UPPER(t.Descrip) NOT LIKE '%CREDITO%' AND UPPER(t.Descrip) NOT LIKE '%TDC%' AND UPPER(t.Descrip) NOT LIKE '%BIOPAGO%' THEN (CASE WHEN f.TipoFac='C' THEN -i.Monto ELSE i.Monto END) ELSE 0 END), 0) AS sis_tdd,
                ISNULL(SUM(CASE WHEN t.TipoIns = 2 AND (UPPER(t.Descrip) LIKE '%CREDITO%' OR UPPER(t.Descrip) LIKE '%TDC%') THEN (CASE WHEN f.TipoFac='C' THEN -i.Monto ELSE i.Monto END) ELSE 0 END), 0) AS sis_tdc,
                ISNULL(SUM(CASE WHEN t.TipoIns = 2 AND UPPER(t.Descrip) LIKE '%BIOPAGO%' THEN (CASE WHEN f.TipoFac='C' THEN -i.Monto ELSE i.Monto END) ELSE 0 END), 0) AS sis_biopago,
                -- Bancos/Transferencias (TipoIns 3)
                ISNULL(SUM(CASE WHEN t.TipoIns = 3 AND (UPPER(t.Descrip) LIKE '%PAGO%MOVIL%' OR UPPER(t.Descrip) LIKE '%PM%' OR UPPER(t.Descrip) LIKE '%MOVIL%') THEN (CASE WHEN f.TipoFac='C' THEN -i.Monto ELSE i.Monto END) ELSE 0 END), 0) AS sis_pm,
                ISNULL(SUM(CASE WHEN t.TipoIns = 3 AND UPPER(t.Descrip) NOT LIKE '%PAGO%MOVIL%' AND UPPER(t.Descrip) NOT LIKE '%PM%' AND UPPER(t.Descrip) NOT LIKE '%MOVIL%' THEN (CASE WHEN f.TipoFac='C' THEN -i.Monto ELSE i.Monto END) ELSE 0 END), 0) AS sis_transferencia,
                -- Otros
                ISNULL(SUM(CASE WHEN t.TipoIns NOT IN (2, 3) AND i.CodTarj NOT IN ('006', '021') THEN (CASE WHEN f.TipoFac='C' THEN -i.Monto ELSE i.Monto END) ELSE 0 END), 0) AS sis_otros
            FROM dbo.SAIPAVTA i
            JOIN dbo.SAFACT f ON i.NumeroD = f.NumeroD AND i.TipoFac = f.TipoFac
            LEFT JOIN dbo.SATARJ t ON i.CodTarj = t.CodTarj
            WHERE f.CodVend = ? AND CAST(f.FechaE AS DATE) = ? AND f.TipoFac IN ('A','C')
        """, (cierre["cod_vend"], cierre["fecha"]))
        
        gran_row = cursor.fetchone()
        sys_vals = {
            "ef_bs_tarj": float(gran_row[0]),
            "divisas_bs": float(gran_row[1]),
            "tdd": float(gran_row[2]),
            "tdc": float(gran_row[3]),
            "biopago": float(gran_row[4]),
            "pm": float(gran_row[5]),
            "transferencia": float(gran_row[6]),
            "otros": float(gran_row[7])
        }

        # Complementar con SAFACT (Efectivo base)
        # 3. Datos del sistema (Saint) - Resumen para el PDF
        cursor.execute("""
            SELECT 
                SUM(ISNULL(CASE WHEN TipoFac = 'C' THEN -CancelE ELSE CancelE END, 0)), 
                COUNT(NumeroD),
                SUM(ISNULL(CASE WHEN TipoFac = 'C' THEN -(Descto1 + Descto2) ELSE (Descto1 + Descto2) END, 0))
            FROM dbo.SAFACT 
            WHERE CodVend = ? AND CAST(FechaE AS DATE) = ? AND TipoFac IN ('A','C')
        """, (cierre["cod_vend"], cierre["fecha"]))
        fact_row = cursor.fetchone()
        sys_vals["ef_bs_base"] = float(fact_row[0] if fact_row[0] else 0)
        nro_facturas = int(fact_row[1] if fact_row[1] else 0)
        tot_descuento = float(fact_row[2] if fact_row[2] else 0)

        # Totales agrupados para el comparativo
        sis_ef_bs_total = sys_vals["ef_bs_base"] + sys_vals["ef_bs_tarj"]
        sis_efectivo = sis_ef_bs_total + sys_vals["divisas_bs"]
        sis_tarjeta  = sys_vals["tdd"] + sys_vals["tdc"] + sys_vals["biopago"] + sys_vals["pm"] + sys_vals["transferencia"] + sys_vals["otros"]


        # 4. Tickets de tarjeta anotados
        cursor.execute("""
            SELECT tipo, punto_de_venta, referencia, monto
            FROM Custom.CajaCierreTarjeta WHERE cierre_id = ?
            ORDER BY tipo, monto DESC
        """, (cierre_id,))
        tickets = [{"tipo": r[0], "pos": r[1], "ref": r[2], "monto": float(r[3])} for r in cursor.fetchall()]

        # 4.5. Extraer devoluciones (Notas de Crédito)
        cursor.execute("""
            SELECT f.NumeroD, f.Monto, f.CancelE, f.CancelT
            FROM dbo.SAFACT f
            WHERE f.CodVend = ? AND CAST(f.FechaE AS DATE) = ? AND f.TipoFac = 'C'
        """, (cierre["cod_vend"], cierre["fecha"]))
        devoluciones_aplicadas = [{"factura": row[0], "monto": float(row[1])} for row in cursor.fetchall()]

        # 5. Desglose de billetes Bs. y divisa
        cursor.execute("SELECT denominacion, cantidad, total FROM Custom.CajaCierreEfectivo WHERE cierre_id = ? ORDER BY denominacion DESC", (cierre_id,))
        billetes_bs = [{"denom": r[0], "cant": r[1], "sub": float(r[2])} for r in cursor.fetchall()]

        cursor.execute("SELECT denominacion, cantidad, total FROM Custom.CajaCierreDivisa WHERE cierre_id = ? ORDER BY denominacion DESC", (cierre_id,))
        billetes_usd = [{"denom": r[0], "cant": r[1], "sub": float(r[2])} for r in cursor.fetchall()]

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

    # -- Construir PDF --------------------------------------------------------
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    # Paleta de colores corporativa
    DARK  = colors.HexColor("#0f172a")
    BLUE  = colors.HexColor("#3b82f6")
    GREEN = colors.HexColor("#10b981")
    RED   = colors.HexColor("#ef4444")
    GOLD  = colors.HexColor("#f59e0b")
    LGRAY = colors.HexColor("#f1f5f9")
    MGRAY = colors.HexColor("#94a3b8")

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", fontSize=18, fontName="Helvetica-Bold", textColor=DARK, alignment=TA_CENTER, spaceAfter=20)
    h2 = ParagraphStyle("h2", fontSize=12, fontName="Helvetica-Bold", textColor=BLUE, spaceAfter=10, alignment=TA_CENTER)
    normal = ParagraphStyle("n", fontSize=9, fontName="Helvetica")
    small  = ParagraphStyle("small", fontSize=8, textColor=MGRAY, fontName="Helvetica")
    mono   = ParagraphStyle("mono", fontSize=9, textColor=DARK, fontName="Courier")
    right  = ParagraphStyle("right", fontSize=9, textColor=DARK, fontName="Helvetica", alignment=TA_RIGHT)

    def fmt(n): return f"Bs. {float(n):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    def fmtN(n): return f"{float(n):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    estado_color = GREEN if cierre["estado"] == "FINALIZADO" else GOLD
    estado_label = f"{'(OK) CIERRE FINALIZADO' if cierre['estado'] == 'FINALIZADO' else '(!) PRECIERRE (BORRADOR)'}"

    story = []

    # -- Encabezado -----------------------------------------------------------
    story.append(Paragraph("PORTAL FINANCIERO AMC", h1))
    story.append(Paragraph("Farmacia Americana · Cuadre de Caja", 
        ParagraphStyle("sub", fontSize=10, textColor=MGRAY, fontName="Helvetica", alignment=TA_CENTER)))
    story.append(Spacer(1, 0.3*cm))

    # Badge de estado
    badge_data = [[Paragraph(estado_label, ParagraphStyle("badge", fontSize=11, textColor=colors.white, fontName="Helvetica-Bold", alignment=TA_CENTER))]]
    badge_tbl = Table(badge_data, colWidths=[16*cm])
    badge_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), estado_color),
        ("ROUNDEDCORNERS", [6]),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(badge_tbl)
    story.append(Spacer(1, 0.5*cm))

    # -- Info del turno --------------------------------------------------------
    info_data = [
        [Paragraph("<b>Responsable</b>", normal), Paragraph(cierre["nombre"], mono),
         Paragraph("<b>Código</b>", normal), Paragraph(cierre["cod_vend"], mono)],
        [Paragraph("<b>Fecha Turno</b>", normal), Paragraph(cierre["fecha"], mono),
         Paragraph("<b>Cierre ID</b>", normal), Paragraph(f"#{cierre_id}", mono)],
        [Paragraph("<b>Última Venta</b>", normal), Paragraph(f"{hora_ultima_venta}", ParagraphStyle("hora", fontSize=10, textColor=BLUE, fontName="Courier-Bold")),
         Paragraph("<b>Última Factura</b>", normal), Paragraph(f"#{ultima_factura}", mono)],
        [Paragraph("<b>Facturas del día</b>", normal), Paragraph(str(nro_facturas), mono),
         Paragraph("<b>Estado</b>", normal), Paragraph(cierre["estado"], ParagraphStyle("st", fontSize=9, textColor=estado_color, fontName="Helvetica-Bold"))],
    ]
    info_tbl = Table(info_data, colWidths=[3.5*cm, 5*cm, 3.5*cm, 4*cm])
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), LGRAY),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [LGRAY, colors.white]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 0.6*cm))

    # -- Comparativo Sistema vs Manual -----------------------------------------
    story.append(Paragraph("COMPARATIVO SISTEMA vs DECLARADO", h2))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    story.append(Spacer(1, 0.2*cm))

    man_ef    = cierre["ef_bs"]
    man_div   = cierre["divisas"]
    man_tdd   = cierre["tdd"]
    man_tdc   = cierre["tdc"]
    man_bio   = cierre["biopago"]
    man_pm    = cierre["pago_movil"]
    man_trans = cierre["transferencia"]

    man_ef_total  = man_ef + man_div
    man_disp      = man_tdd + man_tdc + man_bio          # Dispositivos POS
    man_bancos    = man_pm + man_trans                   # Transferencias bancarias
    man_pos_total = man_disp + man_bancos

    diff_ef   = man_ef_total - sis_efectivo
    
    # System totals separated
    sis_disp = sys_vals["tdd"] + sys_vals["tdc"] + sys_vals["biopago"] + sys_vals["otros"]
    sis_bancos = sys_vals["pm"] + sys_vals["transferencia"]

    diff_disp = man_disp - sis_disp
    diff_banc = man_bancos - sis_bancos
    diff_tot  = (man_ef_total + man_pos_total) - (sis_efectivo + sis_tarjeta)

    def diff_color(v): return GREEN if v >= 0 else RED
    def diff_str(v): return ("+ " if v >= 0 else "- ") + fmtN(abs(v))
    def sub_p(txt): return Paragraph(txt, ParagraphStyle("sub", fontSize=8, fontName="Helvetica", textColor=MGRAY, leftIndent=8))
    def sub_r(txt): return Paragraph(txt, ParagraphStyle("subr", fontSize=8, fontName="Helvetica", textColor=MGRAY, alignment=TA_RIGHT))

    comp_header = [
        Paragraph("<b>Categoría</b>", normal),
        Paragraph("<b>Sistema</b>", right),
        Paragraph("<b>Declarado</b>", right),
        Paragraph("<b>Diferencia</b>", right)
    ]
    comp_rows = [
        comp_header,
        # -- EFECTIVO --
        [Paragraph("<b>EFECTIVO TOTAL</b>", ParagraphStyle("gr",fontSize=9,fontName="Helvetica-Bold")),
         Paragraph(fmt(sis_efectivo), ParagraphStyle("gr2",fontSize=9,fontName="Helvetica-Bold",alignment=TA_RIGHT)),
         Paragraph(fmt(man_ef_total), ParagraphStyle("gr3",fontSize=9,fontName="Helvetica-Bold",alignment=TA_RIGHT)),
         Paragraph(diff_str(diff_ef), ParagraphStyle("dg",fontSize=9,fontName="Helvetica-Bold",textColor=diff_color(diff_ef),alignment=TA_RIGHT))],
        [sub_p("  -> Efectivo Bs."), sub_r(fmt(sis_ef_bs_total)), sub_r(fmt(man_ef)), Paragraph("", right)],
        [sub_p("  -> Divisas USD (en Bs.)"), sub_r(fmt(sys_vals["divisas_bs"])), sub_r(fmt(man_div)), Paragraph("", right)],
        # -- DISPOSITIVOS POS --
        [Paragraph("<b>DISPOSITIVOS POS</b>", ParagraphStyle("gr4",fontSize=9,fontName="Helvetica-Bold")),
         Paragraph(fmt(sis_disp), ParagraphStyle("gr5",fontSize=9,fontName="Helvetica-Bold",alignment=TA_RIGHT)),
         Paragraph(fmt(man_disp), ParagraphStyle("gr6",fontSize=9,fontName="Helvetica-Bold",alignment=TA_RIGHT)),
         Paragraph(diff_str(diff_disp), ParagraphStyle("dd",fontSize=9,fontName="Helvetica-Bold",textColor=diff_color(diff_disp),alignment=TA_RIGHT))],
        [sub_p("  -> TDD (Débito)"), sub_r(fmt(sys_vals["tdd"])), sub_r(fmt(man_tdd)), Paragraph("", right)],
        [sub_p("  -> TDC (Crédito)"), sub_r(fmt(sys_vals["tdc"])), sub_r(fmt(man_tdc)), Paragraph("", right)],
        [sub_p("  -> Biopago"), sub_r(fmt(sys_vals["biopago"])), sub_r(fmt(man_bio)), Paragraph("", right)],
        # -- TRANSFERENCIAS BANCARIAS --
        [Paragraph("<b>PAGO MÓVIL / TRANSF.</b>", ParagraphStyle("gr7",fontSize=9,fontName="Helvetica-Bold")),
         Paragraph(fmt(sis_bancos), right),
         Paragraph(fmt(man_bancos), ParagraphStyle("gr8",fontSize=9,fontName="Helvetica-Bold",alignment=TA_RIGHT)),
         Paragraph(diff_str(diff_banc), ParagraphStyle("dd2",fontSize=9,fontName="Helvetica-Bold",textColor=diff_color(diff_banc),alignment=TA_RIGHT))],
        [sub_p("  -> Pago Móvil"), sub_r(fmt(sys_vals["pm"])), sub_r(fmt(man_pm)), Paragraph("", right)],
        [sub_p("  -> Transferencia"), sub_r(fmt(sys_vals["transferencia"])), sub_r(fmt(man_trans)), Paragraph("", right)],
        # -- DESCUENTO BASE --
        [Paragraph("<b>DESCUENTO BASE (SAINT)</b>", ParagraphStyle("gr9",fontSize=9,fontName="Helvetica-Bold",textColor=GOLD)),
         Paragraph(fmt(tot_descuento), ParagraphStyle("gr10",fontSize=9,fontName="Helvetica-Bold",alignment=TA_RIGHT,textColor=GOLD)),
         Paragraph("-", ParagraphStyle("gr11",fontSize=9,fontName="Helvetica-Bold",alignment=TA_RIGHT)),
         Paragraph("", right)],
        # -- TOTAL --
        [Paragraph("<b>TOTAL GENERAL</b>", ParagraphStyle("tb",fontSize=9,fontName="Helvetica-Bold")),
         Paragraph(fmt(sis_efectivo+sis_tarjeta), ParagraphStyle("tr",fontSize=9,fontName="Helvetica-Bold",alignment=TA_RIGHT)),
         Paragraph(fmt(man_ef_total+man_pos_total), ParagraphStyle("tr2",fontSize=9,fontName="Helvetica-Bold",alignment=TA_RIGHT)),
         Paragraph(diff_str(diff_tot), ParagraphStyle("td",fontSize=9,fontName="Helvetica-Bold",textColor=diff_color(diff_tot),alignment=TA_RIGHT))],
    ]
    comp_tbl = Table(comp_rows, colWidths=[5.5*cm, 3.5*cm, 3.5*cm, 3.5*cm])
    comp_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), DARK),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("BACKGROUND", (0,-1), (-1,-1), LGRAY),
        ("BACKGROUND", (0,1), (-1,1), colors.HexColor("#e8f5e9")),
        ("BACKGROUND", (0,4), (-1,4), colors.HexColor("#e3f2fd")),
        ("BACKGROUND", (0,8), (-1,8), colors.HexColor("#fff8e1")),
        ("ROWBACKGROUNDS", (0,2), (-1,3), [colors.white, LGRAY]),
        ("ROWBACKGROUNDS", (0,5), (-1,7), [colors.white, LGRAY, colors.white]),
        ("ROWBACKGROUNDS", (0,9), (-1,10), [colors.white, LGRAY]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 8), ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("ALIGN", (1,0), (-1,-1), "RIGHT"),
    ]))
    story.append(comp_tbl)
    story.append(Spacer(1, 0.6*cm))

    # -- Desglose Efectivo Bs. -------------------------------------------------
    if billetes_bs:
        story.append(Paragraph("DESGLOSE EFECTIVO BOLíVARES", h2))
        story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
        story.append(Spacer(1, 0.2*cm))
        ef_rows = [[Paragraph("<b>Denominación</b>", normal), Paragraph("<b>Cantidad</b>", right), Paragraph("<b>Subtotal</b>", right)]]
        for b in billetes_bs:
            ef_rows.append([
                Paragraph(f"Bs. {b['denom']:,.0f}", mono),
                Paragraph(str(b["cant"]), right),
                Paragraph(fmt(b["sub"]), right),
            ])
        ef_rows.append([Paragraph("<b>TOTAL</b>", ParagraphStyle("t", fontSize=9, fontName="Helvetica-Bold")),
                        Paragraph("", right),
                        Paragraph(fmt(cierre["ef_bs"]), ParagraphStyle("tr", fontSize=9, fontName="Helvetica-Bold", alignment=TA_RIGHT))])
        ef_tbl = Table(ef_rows, colWidths=[6*cm, 5*cm, 5*cm])
        ef_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), DARK), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("BACKGROUND", (0,-1), (-1,-1), LGRAY),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, LGRAY]),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 8), ("RIGHTPADDING", (0,0), (-1,-1), 8),
            ("ALIGN", (1,0), (-1,-1), "RIGHT"),
        ]))
        story.append(ef_tbl)
        story.append(Spacer(1, 0.6*cm))

    # -- Desglose USD ----------------------------------------------------------
    if billetes_usd:
        story.append(Paragraph("DESGLOSE DIVISAS (USD)", h2))
        story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
        story.append(Spacer(1, 0.2*cm))
        usd_rows = [[Paragraph("<b>Billete</b>", normal), Paragraph("<b>Cantidad</b>", right), Paragraph("<b>Subtotal</b>", right)]]
        for b in billetes_usd:
            usd_rows.append([
                Paragraph(f"$ {b['denom']:,.0f}", mono),
                Paragraph(str(b["cant"]), right),
                Paragraph(f"$ {fmtN(b['sub'])}", right),
            ])
        usd_rows.append([Paragraph("<b>TOTAL</b>", ParagraphStyle("t", fontSize=9, fontName="Helvetica-Bold")),
                         Paragraph("", right),
                         Paragraph(f"$ {fmtN(cierre['divisas'])}", ParagraphStyle("tr", fontSize=9, fontName="Helvetica-Bold", alignment=TA_RIGHT))])
        usd_tbl = Table(usd_rows, colWidths=[6*cm, 5*cm, 5*cm])
        usd_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), DARK), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("BACKGROUND", (0,-1), (-1,-1), LGRAY),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, LGRAY]),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 8), ("RIGHTPADDING", (0,0), (-1,-1), 8),
            ("ALIGN", (1,0), (-1,-1), "RIGHT"),
        ]))
        story.append(usd_tbl)
        story.append(Spacer(1, 0.6*cm))

    # -- Tickets POS -----------------------------------------------------------
    if tickets:
        story.append(Paragraph("TICKETS POS / ELECTRÓNICOS ANOTADOS", h2))
        story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
        story.append(Spacer(1, 0.2*cm))
        tk_rows = [[Paragraph("<b>Tipo</b>", normal), Paragraph("<b>Terminal</b>", normal),
                    Paragraph("<b>Referencia</b>", normal), Paragraph("<b>Monto</b>", right)]]
        for t in tickets:
            tk_rows.append([
                Paragraph(t["tipo"], mono),
                Paragraph(t["pos"], ParagraphStyle("ps", fontSize=8, fontName="Helvetica")),
                Paragraph(t["ref"], mono),
                Paragraph(fmt(t["monto"]), right),
            ])
        tk_rows.append([
            Paragraph("", normal), Paragraph("", normal),
            Paragraph("<b>TOTAL TICKETS</b>", ParagraphStyle("tt", fontSize=9, fontName="Helvetica-Bold", alignment=TA_RIGHT)),
            Paragraph(fmt(man_pos_total), ParagraphStyle("tm", fontSize=9, fontName="Helvetica-Bold", alignment=TA_RIGHT)),
        ])
        tk_tbl = Table(tk_rows, colWidths=[2.5*cm, 6.5*cm, 3*cm, 4*cm])
        tk_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), DARK), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("BACKGROUND", (0,-1), (-1,-1), LGRAY),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, LGRAY]),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6),
            ("ALIGN", (3,0), (3,-1), "RIGHT"),
        ]))
        story.append(tk_tbl)
        story.append(Spacer(1, 0.6*cm))

    # -- Devoluciones (Notas de Crédito) ---------------------------------------
    if devoluciones_aplicadas:
        story.append(Paragraph("DEVOLUCIONES APLICADAS AL SISTEMA", h2))
        story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
        story.append(Spacer(1, 0.2*cm))
        dev_rows = [[Paragraph("<b>Factura / Nota C.</b>", normal), Paragraph("<b>Monto Retornado</b>", right)]]
        tot_dev = 0
        for d in devoluciones_aplicadas:
            dev_rows.append([
                Paragraph(f"#{d['factura']}", mono),
                Paragraph(f"- {fmt(d['monto'])}", ParagraphStyle("dm", fontSize=9, textColor=RED, alignment=TA_RIGHT)),
            ])
            tot_dev += d["monto"]
        dev_rows.append([
            Paragraph("<b>TOTAL DEVOLUCIONES</b>", ParagraphStyle("td", fontSize=9, fontName="Helvetica-Bold", alignment=TA_RIGHT)),
            Paragraph(f"- {fmt(tot_dev)}", ParagraphStyle("tdm", fontSize=9, textColor=RED, fontName="Helvetica-Bold", alignment=TA_RIGHT)),
        ])
        dev_tbl = Table(dev_rows, colWidths=[10*cm, 6*cm])
        dev_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), DARK), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#fee2e2")), # Light red background for total
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, LGRAY]),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6),
            ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ]))
        story.append(dev_tbl)
        story.append(Spacer(1, 0.6*cm))

    # -- Pie de Página ---------------------------------------------------------
    from datetime import datetime
    story.append(HRFlowable(width="100%", thickness=1, color=MGRAY))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"Documento generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')} · Portal Financiero AMC · Cierre #{cierre_id}",
        ParagraphStyle("foot", fontSize=7.5, textColor=MGRAY, fontName="Helvetica", alignment=TA_CENTER)
    ))
    if cierre["estado"] == "BORRADOR":
        story.append(Spacer(1, 0.15*cm))
        story.append(Paragraph(
            "(!) Este documento es un PRECIERRE no oficial. El cierre definitivo aún no ha sido finalizado.",
            ParagraphStyle("warn", fontSize=8, textColor=GOLD, fontName="Helvetica-Bold", alignment=TA_CENTER)
        ))

    doc.build(story)
    buffer.seek(0)

    filename = f"cierre_{cierre_id}_{cierre['estado'].lower()}_{cierre['fecha']}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )


# -- Pago Móvil â€” Bandeja de Captura -----------------------------------------

class CapturarPagoMovilRequest(BaseModel):
    registros_ids: List[int]             # IDs de Procurement.CajaPagoMovil a capturar
    cod_usua: str                        # Quien captura (usuario Saint)
    cierre_id: Optional[int] = None      # ID del cierre al que se asocian (opcional, para vincular)


@router.get("/caja/pagomovil/pendientes")
async def get_pagomovil_pendientes(fecha: Optional[str] = None):
    """
    Retorna todos los registros de Procurement.CajaPagoMovil que aún no han sido
    procesados (procesado = 0), opcionalmente filtrados por fecha.
    Muestra el id íºnico para trazabilidad.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if fecha:
            cursor.execute("""
                SELECT id, banco, monto, referencia, texto_original, created_at
                FROM Procurement.CajaPagoMovil
                WHERE (procesado = 0 OR procesado IS NULL)
                  AND CAST(created_at AS DATE) = ?
                ORDER BY created_at DESC
            """, (fecha,))
        else:
            # Sin filtro de fecha: muestra pendientes de hoy y ayer (ventana de 2 días)
            cursor.execute("""
                SELECT id, banco, monto, referencia, texto_original, created_at
                FROM Procurement.CajaPagoMovil
                WHERE (procesado = 0 OR procesado IS NULL)
                  AND created_at >= DATEADD(DAY, -1, CAST(GETDATE() AS DATE))
                ORDER BY created_at DESC
            """)

        cols = [c[0] for c in cursor.description]
        rows = []
        for r in cursor.fetchall():
            item = dict(zip(cols, r))
            # Serialise datetime / decimal
            for k, v in item.items():
                if hasattr(v, 'isoformat'):
                    item[k] = v.isoformat()
                elif v is None:
                    item[k] = None
                else:
                    try:
                        item[k] = float(v) if isinstance(v, object) and hasattr(v, '__float__') else v
                    except Exception:
                        item[k] = str(v)
            rows.append(item)

        return {"status": "success", "total": len(rows), "data": rows}

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@router.post("/caja/pagomovil/capturar")
async def capturar_pagomovil(payload: CapturarPagoMovilRequest):
    """
    Marca uno o mí¡s registros de Procurement.CajaPagoMovil como procesados.
    Registra el usuario que los capturó (cod_usua) y el cierre_id si se provee.
    Opera de forma atómica â€” si algíºn registro ya fue procesado, ignora ese ID.
    Retorna la lista de registros efectivamente capturados para que el frontend
    los agregue como tickets al cuadre activo.
    """
    if not payload.registros_ids:
        raise HTTPException(status_code=400, detail="Debe indicar al menos un ID.")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Construir placeholders para IN clause
        placeholders = ",".join(["?" for _ in payload.registros_ids])

        # Leer los registros pendientes que aún no fueron tomados (previene doble captura)
        cursor.execute(f"""
            SELECT id, banco, monto, referencia
            FROM Procurement.CajaPagoMovil
            WHERE id IN ({placeholders})
              AND (procesado = 0 OR procesado IS NULL)
        """, payload.registros_ids)

        disponibles = cursor.fetchall()
        if not disponibles:
            return {"status": "warning", "message": "Todos los registros seleccionados ya fueron procesados.", "capturados": []}

        ids_disponibles = [r[0] for r in disponibles]
        placeholders2 = ",".join(["?" for _ in ids_disponibles])

        # Marcar como procesados en bloque atómico
        params = [1, payload.cod_usua]
        if payload.cierre_id:
            params.append(payload.cierre_id)
            cursor.execute(f"""
                UPDATE Procurement.CajaPagoMovil
                SET procesado      = ?,
                    capturado_por  = ?,
                    capturado_en   = GETDATE(),
                    cierre_id      = ?
                WHERE id IN ({placeholders2})
            """, params + ids_disponibles)
        else:
            cursor.execute(f"""
                UPDATE Procurement.CajaPagoMovil
                SET procesado      = ?,
                    capturado_por  = ?,
                    capturado_en   = GETDATE()
                WHERE id IN ({placeholders2})
            """, params + ids_disponibles)

        conn.commit()

        # Armar respuesta con detalles de los capturados
        capturados = [
            {
                "id": r[0],
                "banco": str(r[1]).strip() if r[1] else "N/A",
                "monto": float(r[2]) if r[2] else 0.0,
                "referencia": str(r[3]).strip() if r[3] else ""
            }
            for r in disponibles
        ]

        return {
            "status": "success",
            "message": f"{len(capturados)} registro(s) capturado(s) por {payload.cod_usua}",
            "capturados": capturados
        }

    except pyodbc.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

@router.post("/caja/admin/reparar-fechas")
async def reparar_fechas(req: RepararFechasRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = "UPDATE SAFACT SET FechaE=FechaT WHERE FechaT BETWEEN ? AND ?"
        cursor.execute(query, (req.fecha_inicio, req.fecha_fin))
        filas_afectadas = cursor.rowcount
        conn.commit()
        return {"status": "success", "message": f"Se repararon {filas_afectadas} facturas.", "filas_afectadas": filas_afectadas}
    except pyodbc.Error as strErr:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(strErr)}")
    finally:
        cursor.close()
        conn.close()


# ── Reporte de Ventas (Pivot) ─────────────────────────────────────────────────

@router.get("/caja/reportes/ventas")
async def reporte_ventas(
    fecha_desde: str,
    fecha_hasta: str,
    vendedor_codigo: str | None = None,
    incluir_nc: bool = True
):
    """
    Retorna KPIs globales + detalle por vendedor×fecha para el módulo de
    Reporte de Ventas. Alimenta la pivot grid del frontend.
    Campos de descuento: Descto1 (cabecera dto1), Descto2 (cabecera dto2).
    Las Notas de Crédito (TipoFac='C') se restan del total cuando incluir_nc=True.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        tipos = "('A','C')" if incluir_nc else "('A')"
        vend_filter = "AND f.CodVend = ?" if vendedor_codigo else ""
        params_base: list = [fecha_desde, fecha_hasta]
        if vendedor_codigo:
            params_base.append(vendedor_codigo)

        # ── Detalle por Vendedor × Fecha ──────────────────────────────────
        sql_detalle = f"""
            SELECT
                CAST(f.FechaE AS DATE)                                         AS fecha,
                RTRIM(f.CodVend)                                               AS cod_vend,
                RTRIM(v.Descrip)                                               AS vendedor,
                COUNT(DISTINCT CASE WHEN f.TipoFac='A' THEN f.NumeroD END)     AS nro_ventas,
                COUNT(DISTINCT CASE WHEN f.TipoFac='C' THEN f.NumeroD END)     AS nro_nc,
                ISNULL(SUM(CASE WHEN f.TipoFac='C' THEN -f.Monto    ELSE f.Monto    END),0) AS venta_bruta,
                ISNULL(SUM(CASE WHEN f.TipoFac='C' THEN -f.Descto1  ELSE f.Descto1  END),0) AS descto1,
                ISNULL(SUM(CASE WHEN f.TipoFac='C' THEN -f.Descto2  ELSE f.Descto2  END),0) AS descto2,
                ISNULL(SUM(CASE WHEN f.TipoFac='C' THEN -(f.Descto1+f.Descto2)
                                                   ELSE  (f.Descto1+f.Descto2) END),0) AS descuento_total,
                ISNULL(SUM(CASE WHEN f.TipoFac='C'
                                THEN -(f.Monto-(f.Descto1+f.Descto2))
                                ELSE  (f.Monto-(f.Descto1+f.Descto2)) END),0) AS venta_neta,
                ISNULL(SUM(CASE WHEN f.TipoFac='C' THEN -f.CancelE  ELSE f.CancelE  END),0) AS pago_efectivo,
                ISNULL(SUM(CASE WHEN f.TipoFac='C' THEN -f.CancelT  ELSE f.CancelT  END),0) AS pago_tarjeta
            FROM dbo.SAFACT f
            JOIN dbo.SAVEND v ON f.CodVend = v.CodVend
            WHERE CAST(f.FechaE AS DATE) BETWEEN ? AND ?
              AND f.TipoFac IN {tipos}
              {vend_filter}
            GROUP BY CAST(f.FechaE AS DATE), f.CodVend, v.Descrip
            ORDER BY CAST(f.FechaE AS DATE), v.Descrip
        """
        cursor.execute(sql_detalle, params_base)
        cols = [c[0] for c in cursor.description]
        STRING_FIELDS = {'cod_vend', 'vendedor', 'fecha', 'tipo'}
        detalles = []
        for row in cursor.fetchall():
            d = dict(zip(cols, row))
            for k, v in d.items():
                if k in STRING_FIELDS:
                    d[k] = str(v).strip() if v is not None else ''
                elif hasattr(v, 'isoformat'):
                    d[k] = str(v)
                elif v is None:
                    d[k] = 0
                else:
                    try:
                        d[k] = float(v)
                    except (TypeError, ValueError):
                        d[k] = str(v)
            # pct_descuento: avoid divide-by-zero
            d['pct_descuento'] = round(
                (d['descuento_total'] / d['venta_bruta'] * 100) if d['venta_bruta'] else 0, 2
            )
            d['nro_facturas'] = int(d['nro_ventas'] + d['nro_nc'])
            detalles.append(d)

        # ── KPIs Globales ─────────────────────────────────────────────────
        tot_bruta     = sum(d['venta_bruta']     for d in detalles)
        tot_neta      = sum(d['venta_neta']      for d in detalles)
        tot_dto       = sum(d['descuento_total'] for d in detalles)
        tot_descto1   = sum(d['descto1']         for d in detalles)
        tot_descto2   = sum(d['descto2']         for d in detalles)
        tot_ventas    = int(sum(d['nro_ventas']  for d in detalles))
        tot_nc        = int(sum(d['nro_nc']      for d in detalles))
        pct_global    = round((tot_dto / tot_bruta * 100) if tot_bruta else 0, 2)
        ticket_prom   = round((tot_neta / tot_ventas) if tot_ventas else 0, 2)

        kpis = {
            "venta_bruta":      round(tot_bruta, 2),
            "venta_neta":       round(tot_neta, 2),
            "descuento_total":  round(tot_dto, 2),
            "descto1":          round(tot_descto1, 2),
            "descto2":          round(tot_descto2, 2),
            "pct_descuento":    pct_global,
            "nro_ventas":       tot_ventas,
            "nro_nc":           tot_nc,
            "ticket_promedio":  round(ticket_prom, 2),
        }

        return {"status": "success", "kpis": kpis, "detalles": detalles}

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


# ── Dashboard Charts (Hora + Categoría) ──────────────────────────────────────

@router.get("/caja/reportes/ventas/dashboard")
async def dashboard_charts(fecha: str):
    """
    Retorna datos agregados para los gráficos del dashboard móvil:
      - ventas_por_hora:  agrupación por DATEPART(hour) de SAFACT
      - ventas_por_categoria: agrupación por SAINSTA.Descrip vía SAITEMFAC→SAPROD
    Parámetro `fecha` es la fecha del día a consultar (YYYY-MM-DD).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # ── Ventas por Hora ──────────────────────────────────────────────
        cursor.execute("""
            SELECT
                DATEPART(hour, f.FechaE)                                    AS hora,
                SUM(CASE WHEN f.TipoFac='C' THEN -f.Monto ELSE f.Monto END) AS total
            FROM dbo.SAFACT f
            WHERE CAST(f.FechaE AS DATE) = ?
              AND f.TipoFac IN ('A','C')
            GROUP BY DATEPART(hour, f.FechaE)
            ORDER BY hora
        """, (fecha,))
        hourly = [
            {"hora": int(r[0]), "total": round(float(r[1]), 2)}
            for r in cursor.fetchall()
        ]

        # ── Ventas por Categoría ─────────────────────────────────────────
        cursor.execute("""
            SELECT
                RTRIM(inst.Descrip)                                          AS category,
                SUM(CASE WHEN f.TipoFac='C' THEN -i.TotalItem
                                              ELSE  i.TotalItem END)         AS amount
            FROM dbo.SAITEMFAC i
            JOIN dbo.SAFACT   f    ON i.NumeroD = f.NumeroD AND i.TipoFac = f.TipoFac
            JOIN dbo.SAPROD   p    ON i.CodItem = p.CodProd
            JOIN dbo.SAINSTA  inst ON p.CodInst = inst.CodInst
            WHERE CAST(f.FechaE AS DATE) = ?
              AND f.TipoFac IN ('A','C')
            GROUP BY inst.Descrip
            ORDER BY amount DESC
        """, (fecha,))
        categories = [
            {"category": str(r[0]).strip(), "amount": round(float(r[1]), 2)}
            for r in cursor.fetchall()
        ]

        return {
            "status": "success",
            "fecha": fecha,
            "ventas_por_hora": hourly,
            "ventas_por_categoria": categories,
        }

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


# ── Reporte de Devoluciones (NC) ──────────────────────────────────────────────

@router.get("/caja/reportes/devoluciones")
async def reporte_devoluciones(
    fecha_desde: str,
    fecha_hasta: str,
    vendedor_codigo: str | None = None
):
    """
    Retorna listado de Notas de Crédito (TipoFac='C') con detalle
    para control de devoluciones en el cierre de caja.
    Cada factura devuelta debe entregarse en físico al supervisor.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        vend_filter = "AND f.CodVend = ?" if vendedor_codigo else ""
        params: list = [fecha_desde, fecha_hasta]
        if vendedor_codigo:
            params.append(vendedor_codigo)

        sql = f"""
            SELECT
                CAST(f.FechaE AS DATE)   AS fecha,
                RTRIM(f.CodVend)         AS cod_vend,
                RTRIM(v.Descrip)         AS vendedor,
                f.NumeroD                AS nro_nc,
                f.Monto                  AS monto,
                f.Descto1                AS descto1,
                f.Descto2                AS descto2,
                f.Monto - (f.Descto1 + f.Descto2) AS monto_neto,
                f.CancelE                AS pago_efectivo,
                f.CancelT                AS pago_tarjeta,
                RTRIM(ISNULL(f.Observa, ''))  AS observacion
            FROM dbo.SAFACT f
            JOIN dbo.SAVEND v ON f.CodVend = v.CodVend
            WHERE CAST(f.FechaE AS DATE) BETWEEN ? AND ?
              AND f.TipoFac = 'C'
              {vend_filter}
            ORDER BY CAST(f.FechaE AS DATE) DESC, f.NumeroD DESC
        """
        cursor.execute(sql, params)
        cols = [c[0] for c in cursor.description]
        registros = []
        for row in cursor.fetchall():
            d = dict(zip(cols, row))
            for k, val in d.items():
                if hasattr(val, 'isoformat'):
                    d[k] = str(val)
                elif val is None:
                    d[k] = 0
                else:
                    try:
                        d[k] = float(val)
                    except (TypeError, ValueError):
                        d[k] = str(val)
            registros.append(d)

        total_nc = len(registros)
        total_monto = round(sum(r['monto'] for r in registros), 2)

        return {
            "status": "success",
            "total_nc": total_nc,
            "total_monto": total_monto,
            "registros": registros
        }

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


# ── Detalle de Facturas (Drill-Down) ─────────────────────────────────────────

@router.get("/caja/reportes/ventas/detalle")
async def detalle_facturas(
    fecha: str,
    vendedor: str | None = None,
    tipo_fac: str = "A"  # A=ventas, C=NC, AC=ambos
):
    """
    Retorna facturas individuales para una fecha+vendedor.
    Incluye líneas de producto (SAITEMFAC) anidadas.
    Usado como drill-down desde la pivot grid.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        tipos = "('A','C')" if tipo_fac == "AC" else f"('{tipo_fac}')"
        vend_filter = "AND f.CodVend = ?" if vendedor else ""
        params: list = [fecha]
        if vendedor:
            params.append(vendedor)

        # ── Cabeceras de factura ──
        # Intentamos con SACLIE primero, si falla (tabla no existe) usamos fallback
        def _row_to_dict(row, cols):
            _STR_KEYS = {'numero', 'tipo', 'cod_vend', 'vendedor', 'cod_cliente',
                         'cliente', 'hora', 'fecha', 'cod_producto', 'producto'}
            d = dict(zip(cols, row))
            for k, val in list(d.items()):
                if k in _STR_KEYS:
                    d[k] = str(val).strip() if val is not None else ''
                elif hasattr(val, 'isoformat'):
                    d[k] = str(val)
                elif val is None:
                    d[k] = 0
                else:
                    try:
                        d[k] = float(val)
                    except (TypeError, ValueError):
                        d[k] = str(val)
            return d

        sql_fac_full = f"""
            SELECT
                f.NumeroD                          AS numero,
                f.TipoFac                          AS tipo,
                CAST(f.FechaE AS DATE)             AS fecha,
                ISNULL(CONVERT(VARCHAR(5), f.FechaE, 108), '') AS hora,
                RTRIM(f.CodVend)                   AS cod_vend,
                RTRIM(v.Descrip)                   AS vendedor,
                RTRIM(f.CodClie)                   AS cod_cliente,
                RTRIM(ISNULL(c.Descrip,'CONSUMIDOR FINAL')) AS cliente,
                f.Monto                            AS monto,
                ISNULL(f.DesctoP, 0)               AS desctoP,
                ISNULL(f.Descto1, 0)               AS descto1,
                ISNULL(f.Descto2, 0)               AS descto2,
                f.Monto - (ISNULL(f.DesctoP,0) + ISNULL(f.Descto1,0) + ISNULL(f.Descto2,0)) AS neto
            FROM dbo.SAFACT f
            JOIN dbo.SAVEND v ON f.CodVend = v.CodVend
            LEFT JOIN dbo.SACLIE c ON f.CodClie = c.CodClie
            WHERE CAST(f.FechaE AS DATE) = ?
              AND f.TipoFac IN {tipos}
              {vend_filter}
            ORDER BY f.FechaE, f.NumeroD
        """

        sql_fac_simple = f"""
            SELECT
                f.NumeroD                          AS numero,
                f.TipoFac                          AS tipo,
                CAST(f.FechaE AS DATE)             AS fecha,
                ''                                 AS hora,
                RTRIM(f.CodVend)                   AS cod_vend,
                RTRIM(v.Descrip)                   AS vendedor,
                RTRIM(f.CodClie)                   AS cod_cliente,
                RTRIM(f.CodClie)                   AS cliente,
                f.Monto                            AS monto,
                ISNULL(f.DesctoP, 0)               AS desctoP,
                ISNULL(f.Descto1, 0)               AS descto1,
                ISNULL(f.Descto2, 0)               AS descto2,
                f.Monto - (ISNULL(f.DesctoP,0) + ISNULL(f.Descto1,0) + ISNULL(f.Descto2,0)) AS neto
            FROM dbo.SAFACT f
            JOIN dbo.SAVEND v ON f.CodVend = v.CodVend
            WHERE CAST(f.FechaE AS DATE) = ?
              AND f.TipoFac IN {tipos}
              {vend_filter}
            ORDER BY f.NumeroD
        """

        facturas = []
        try:
            cursor.execute(sql_fac_full, params)
            cols_fac = [c[0] for c in cursor.description]
            for row in cursor.fetchall():
                facturas.append(_row_to_dict(row, cols_fac))
        except pyodbc.Error:
            # Fallback sin SACLIE (tabla de clientes no disponible)
            cursor.execute(sql_fac_simple, params)
            cols_fac = [c[0] for c in cursor.description]
            for row in cursor.fetchall():
                facturas.append(_row_to_dict(row, cols_fac))

        # ── Items de cada factura ──
        if facturas:
            numeros = [str(f['numero']).strip() for f in facturas]
            placeholders = ','.join(['?'] * len(numeros))

            sql_items_full = f"""
                SELECT
                    i.NumeroD                           AS numero,
                    RTRIM(i.CodItem)                    AS cod_producto,
                    RTRIM(ISNULL(p.Descrip, i.CodItem)) AS producto,
                    i.Cantidad                          AS cantidad,
                    i.Precio                            AS precio_unitario,
                    i.TotalItem                         AS monto_linea,
                    ISNULL(i.Descto, 0)                 AS descto_linea
                FROM dbo.SAITEMFAC i
                LEFT JOIN dbo.SAPROD p ON i.CodItem = p.CodProd
                WHERE i.NumeroD IN ({placeholders})
                ORDER BY i.NumeroD, i.NroLinea
            """

            sql_items_simple = f"""
                SELECT
                    i.NumeroD                           AS numero,
                    RTRIM(i.CodItem)                    AS cod_producto,
                    RTRIM(i.CodItem)                    AS producto,
                    i.Cantidad                          AS cantidad,
                    i.Precio                            AS precio_unitario,
                    i.TotalItem                         AS monto_linea,
                    ISNULL(i.Descto, 0)                 AS descto_linea
                FROM dbo.SAITEMFAC i
                WHERE i.NumeroD IN ({placeholders})
                ORDER BY i.NumeroD, i.NroLinea
            """

            items_map = {}
            try:
                cursor.execute(sql_items_full, numeros)
            except pyodbc.Error:
                cursor.execute(sql_items_simple, numeros)

            cols_it = [c[0] for c in cursor.description]
            for row in cursor.fetchall():
                it = _row_to_dict(row, cols_it)
                num = str(it['numero']).strip()
                if num not in items_map:
                    items_map[num] = []
                items_map[num].append(it)

            for f in facturas:
                f['productos'] = items_map.get(str(f['numero']).strip(), [])
        else:
            pass

        return {"status": "success", "total": len(facturas), "facturas": facturas}

    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()
