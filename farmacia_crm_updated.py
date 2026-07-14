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
    Devuelve los productos disponibles, agrupados primero por presentación exacta 
    (Principio Activo + Forma Farmacéutica + Concentración) y luego variaciones con otra concentración/forma.
    Usa estrictamente Precio3 (Bs) y PrecioI3 (USD).
    """
    try:
        conn = connect_db()
        cursor = conn.cursor(as_dict=True)
        
        words = [w for w in keyword.split() if len(w) > 2]
        if not words:
            words = [keyword]
        like_clauses = " AND ".join([f"s.Descrip LIKE '%{w}%'" for w in words])

        # Step 1: Find target product
        query_target = f"""
        SELECT TOP 1
            e.principio_activo,
            e.concentracion,
            e.forma_farmaceutica,
            e.principio_activo_Des,
            e.concentracion_Des,
            e.forma_farmaceutica_Des
        FROM dbo.SAPROD s
        INNER JOIN Procurement.por_aprobacion_equivalencias e
            ON s.CodProd = e.codbarras
        WHERE {like_clauses}
          AND s.Activo = 1
          AND e.principio_activo IS NOT NULL
        ORDER BY s.Existen DESC
        """
        cursor.execute(query_target)
        target = cursor.fetchone()
        
        if not target:
            # Fallback if no exact medical equivalents found
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
            response = f"Resultados para '{keyword}':\n\n"
            response += f"=== Productos Sin Clasificar (No mapeados en MDM) ===\n"
            response += f"NOTA: Estos productos no tienen Principio Activo asignado en la base de datos, por lo que no se pueden agrupar por alternativas.\n\n"
            for row in results:
                stock = row['Existen']
                precio_bs = row['Precio3']
                precio_usd = row['PrecioI3']
                desc = row['Descrip']
                response += f"- {desc}: {stock:.0f} unidades disponibles. Precio: Bs. {precio_bs:.2f} / ${precio_usd:.2f} USD\n"
            return response

        # Step 2: Find all products with the same active ingredient
        pa_id = target['principio_activo']
        target_conc = target['concentracion']
        target_forma = target['forma_farmaceutica']
        pa_name = target['principio_activo_Des'] or 'N/A'
        target_conc_des = target['concentracion_Des'] or ''
        target_forma_des = target['forma_farmaceutica_Des'] or ''
        
        query_all = f"""
        SELECT TOP 30
            s.CodProd,
            s.Descrip,
            s.Precio3,
            s.PrecioI3,
            s.Existen,
            e.principio_activo_Des,
            e.concentracion,
            e.forma_farmaceutica,
            e.concentracion_Des,
            e.forma_farmaceutica_Des,
            e.origen_Des,
            e.fabricante_Des
        FROM dbo.SAPROD s
        INNER JOIN Procurement.por_aprobacion_equivalencias e
            ON s.CodProd = e.codbarras
        WHERE e.principio_activo = '{pa_id}'
          AND s.Activo = 1 
          AND s.Existen > 0
        ORDER BY s.Existen DESC;
        """
        cursor.execute(query_all)
        results = cursor.fetchall()
        conn.close()
        
        # Agrupar TODO el inventario con el mismo principio activo por Forma Farmacéutica
        from collections import defaultdict
        grouped_vars = defaultdict(list)
        
        for row in results:
            ff_des = row.get('forma_farmaceutica_Des')
            if not ff_des or str(ff_des).lower() == 'null':
                ff_des = 'Otras Formas'
            else:
                # Normalizar a mayúsculas para evitar grupos duplicados (Tableta, TABLETA, Tabletas)
                ff_des = str(ff_des).strip().upper()
                if ff_des.endswith('S'): # Simplificación rápida para plurales
                    ff_des = ff_des[:-1]
                
            grouped_vars[ff_des].append(row)
            
        response = f"Resultados para '{keyword}' (Principio Activo: {pa_name}):\n\n"
        
        # Primero mostrar el grupo de la forma farmacéutica solicitada (si existe)
        target_ff_name = target_forma_des if (target_forma_des and str(target_forma_des).lower() != 'null') else 'Otras Formas'
        target_ff_name = str(target_ff_name).strip().upper()
        if target_ff_name.endswith('S'):
            target_ff_name = target_ff_name[:-1]
        
        if target_ff_name in grouped_vars:
            response += f"=== {target_ff_name} ===\n"
            for row in grouped_vars[target_ff_name][:15]:
                stock = row['Existen']
                precio_bs = row['Precio3']
                precio_usd = row['PrecioI3']
                desc = row['Descrip']
                fab = row.get('fabricante_Des', 'N/A')
                response += f"- {desc} (Fab: {fab}): {stock:.0f} disp. | Bs. {precio_bs:.2f} / ${precio_usd:.2f} USD\n"
            
            # Removerlo para no imprimirlo dos veces
            del grouped_vars[target_ff_name]
            
        # Mostrar el resto de los grupos
        for ff_des, group_rows in grouped_vars.items():
            response += f"\n=== {ff_des} ===\n"
            for row in group_rows[:15]:
                stock = row['Existen']
                precio_bs = row['Precio3']
                precio_usd = row['PrecioI3']
                desc = row['Descrip']
                fab = row.get('fabricante_Des', 'N/A')
                response += f"- {desc} (Fab: {fab}): {stock:.0f} disp. | Bs. {precio_bs:.2f} / ${precio_usd:.2f} USD\n"
                
        return response

    except Exception as e:
        logger.error(f"Error consultando inventario: {e}")
        return f"Error consultando inventario: {str(e)}"

def consultar_horarios() -> str:
    return "Nuestro horario de atención es de Lunes a Domingo de 8:00 AM a 9:00 PM."
