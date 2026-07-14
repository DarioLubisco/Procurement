from fastapi import APIRouter, HTTPException
from database import get_db_connection
from typing import Dict, Any

router = APIRouter(prefix="/inventario", tags=["inventario"])

@router.get("/status")
async def get_inventario_status() -> Dict[str, Any]:
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Resumen general y conteos
        query = """
        SELECT 
            COUNT(*) as total_items,
            COUNT(CASE WHEN cl.FechaE < GETDATE() THEN 1 END) as items_vencidos,
            COUNT(CASE WHEN cl.FechaE >= GETDATE() AND cl.FechaE <= DATEADD(DAY, 30, GETDATE()) THEN 1 END) as items_criticos,
            COUNT(CASE WHEN cl.FechaE > DATEADD(DAY, 30, GETDATE()) AND cl.FechaE <= DATEADD(DAY, 90, GETDATE()) THEN 1 END) as items_proximos,
            (COUNT(CASE WHEN cl.FechaE > DATEADD(MONTH, 6, GETDATE()) THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)) as indice_calidad
        FROM dbo.CUSTOM_LOTES cl
        WHERE cl.Cantidad > 0;
        """
        cursor.execute(query)
        row = cursor.fetchone()
        
        if row:
            return {
                "total_items": row.total_items or 0,
                "items_vencidos": row.items_vencidos or 0,
                "items_criticos": row.items_criticos or 0,
                "items_proximos": row.items_proximos or 0,
                "indice_calidad": float(row.indice_calidad) if row.indice_calidad is not None else 100.0
            }
        else:
            return {
                "total_items": 0, "items_vencidos": 0, "items_criticos": 0, "items_proximos": 0, "indice_calidad": 100.0
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@router.get("/vencimientos")
async def get_vencimientos() -> Dict[str, Any]:
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
        SELECT 
            sp.CodProd,
            sp.Descrip,
            cl.NroLote,
            cl.Cantidad,
            cl.FechaE,
            cl.Precio1,
            DATEDIFF(DAY, GETDATE(), cl.FechaE) AS dias_para_vencer
        FROM dbo.CUSTOM_LOTES cl
        INNER JOIN dbo.SAPROD sp ON cl.CodProd = sp.CodProd
        WHERE cl.Cantidad > 0
          AND sp.Activo = 1
          AND cl.FechaE <= DATEADD(DAY, 180, GETDATE())
        ORDER BY cl.FechaE ASC;
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        resultados = []
        for r in rows:
            resultados.append({
                "codigo": r.CodProd,
                "producto": r.Descrip,
                "lote": r.NroLote,
                "stock": float(r.Cantidad),
                "fecha_vencimiento": r.FechaE.strftime("%Y-%m-%d") if r.FechaE else None,
                "precio": float(r.Precio1) if r.Precio1 else 0.0,
                "dias_para_vencer": r.dias_para_vencer
            })
            
        return {"data": resultados}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@router.get("/frescura-etl")
async def get_frescura_etl() -> Dict[str, Any]:
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
        SELECT 
            Proveedor,
            Protocolo_Conexion,
            LastProcessedAt,
            Horas_Transcurridas,
            Estado_Semaforo
        FROM Proveedores.VW_Estado_Frescura_ETL
        WHERE Monitorear_Dashboard = 1
        ORDER BY 
            CASE 
                WHEN Estado_Semaforo LIKE 'ROJO%' THEN 1
                WHEN Estado_Semaforo LIKE 'NARANJA%' THEN 2
                ELSE 3 
            END,
            Horas_Transcurridas DESC;
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        resultados = []
        for r in rows:
            resultados.append({
                "proveedor": r.Proveedor,
                "protocolo": r.Protocolo_Conexion,
                "ultima_actualizacion": r.LastProcessedAt.strftime("%Y-%m-%d %H:%M:%S") if r.LastProcessedAt else "Nunca",
                "horas_transcurridas": float(r.Horas_Transcurridas) if r.Horas_Transcurridas is not None else -1,
                "estado_semaforo": r.Estado_Semaforo
            })
            
        return {"data": resultados}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
