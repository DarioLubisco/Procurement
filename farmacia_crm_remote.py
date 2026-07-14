import sys
import subprocess
import urllib.request
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("farmacia_crm")

try:
    import pymssql
except ImportError:
    pass

def connect_db():
    servers = [
        '10.147.18.192\\efficacis3',  # ZeroTier
        '100.125.8.80\\efficacis3',   # Tailscale
        '10.200.8.5\\efficacis3'      # LAN Local
    ]
    
    for server in servers:
        try:
            conn = pymssql.connect(
                server=server, 
                user='sa', 
                password='Twinc3pt.', 
                database='EnterpriseAdmin_AMC',
                login_timeout=3
            )
            return conn
        except Exception as e:
            logger.warning(f"Fallo conexión con {server}: {e}")
            continue
            
    raise Exception("No se pudo conectar a la base de datos por ninguna de las IPs (ZeroTier, Tailscale, LAN)")

def consultar_inventario(keyword: str) -> str:
    """
    Busca en el inventario un medicamento por su nombre o palabra clave (ej. ibuprofeno).
    Devuelve los productos disponibles y sus equivalentes genéricos o de otras marcas 
    que tengan el mismo principio activo, concentración y forma farmacéutica.
    Incluye precios en bolívares y dólares.
    """
    
    try:
        conn = connect_db()
        cursor = conn.cursor(as_dict=True)
        
        # Split keywords to allow robust searching (e.g. "ibuprofeno de 800")
        words = [w for w in keyword.split() if len(w) > 2]
        if not words:
            words = [keyword]
        like_clauses = " AND ".join([f"s.Descrip LIKE '%{w}%'" for w in words])

        query = f"""
        WITH TargetProduct AS (
            SELECT TOP 1
                e.principio_activo,
                e.concentracion,
                e.forma_farmaceutica
            FROM dbo.SAPROD s
            INNER JOIN Procurement.por_aprobacion_equivalencias e
                ON s.CodProd = e.codigo
            WHERE {like_clauses}
              AND s.Activo = 1
              AND e.principio_activo IS NOT NULL
            ORDER BY s.Existen DESC
        )
        SELECT TOP 10
            s.CodProd,
            s.Descrip,
            s.Precio3,
            s.PrecioI3,
            s.Existen,
            e.principio_activo_Des,
            e.concentracion_Des,
            e.forma_farmaceutica_Des,
            e.origen_Des,
            e.fabricante_Des
        FROM dbo.SAPROD s
        INNER JOIN Procurement.por_aprobacion_equivalencias e
            ON s.CodProd = e.codigo
        INNER JOIN TargetProduct t
            ON e.principio_activo = t.principio_activo
           AND COALESCE(e.concentracion, 0) = COALESCE(t.concentracion, 0)
           AND COALESCE(e.forma_farmaceutica, 0) = COALESCE(t.forma_farmaceutica, 0)
        WHERE s.Activo = 1 
          AND s.Existen > 0
        ORDER BY s.Existen DESC;
        """
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Fallback if no exact medical equivalents found
        if not results:
            fallback_query = f"""
            SELECT TOP 10 CodProd, Descrip, Precio3, PrecioI3, Existen
            FROM dbo.SAPROD s
            WHERE s.Activo = 1 AND s.Existen > 0 AND {like_clauses}
            ORDER BY s.Existen DESC
            """
            cursor.execute(fallback_query)
            results = cursor.fetchall()
            
            if not results:
                conn.close()
                return f"No se encontró stock ni coincidencias para '{keyword}'."
                
            conn.close()
            response = f"Resultados directos para '{keyword}':\n\n"
            for row in results:
                stock = row['Existen']
                precio_bs = row['Precio3']
                precio_usd = row['PrecioI3']
                desc = row['Descrip']
                response += f"- {desc}: {stock:.0f} unidades disponibles. Precio: Bs. {precio_bs:.2f} / ${precio_usd:.2f} USD\n"
            return response
            
        conn.close()
        
        pa_name = results[0].get('principio_activo_Des', 'N/A')
        conc = results[0].get('concentracion_Des', '')
        forma = results[0].get('forma_farmaceutica_Des', '')
        
        response = f"Resultados y equivalentes para '{keyword}' (Principio Activo: {pa_name} {conc} {forma}):\n\n"
        for row in results:
            stock = row['Existen']
            precio_bs = row['Precio3']
            precio_usd = row['PrecioI3']
            desc = row['Descrip']
            fab = row.get('fabricante_Des', 'N/A')
            
            response += f"- {desc} (Fab: {fab}): {stock:.0f} unidades disponibles. Precio: Bs. {precio_bs:.2f} / ${precio_usd:.2f} USD\n"
        
        return response
    except Exception as e:
        logger.error(f"Error consultando inventario: {e}")
        return f"Error consultando inventario: {str(e)}"

def consultar_horarios() -> str:
    """
    Devuelve los horarios de atención y apertura de la farmacia.
    """
    return "Nuestro horario de atención es de Lunes a Domingo de 8:00 AM a 9:00 PM."
