"""
Motor de Rotación Grupal Dinámica
==================================
Arquitectura híbrida:
  - CACHED: Lee R1 (SKU) + R2 (Base: PA+Conc+FF) de Procurement.RotacionGrupal (~10ms)
  - DYNAMIC: Calcula on-the-fly con GROUP BY variable para cualquier combinación de atributos (~1-3s)

Endpoints:
  GET  /api/rotacion-grupal/           → Consulta grupos (cached o dinámico)
  GET  /api/rotacion-grupal/atributos  → Lista de atributos disponibles
  GET  /api/rotacion-grupal/freshness  → Estado de frescura de la tabla
  POST /api/rotacion-grupal/recalcular → Forzar recálculo del SP

Autor: Synapse/Antigravity
Fecha: 2026-06-17
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import database

router = APIRouter(prefix="/api/rotacion-grupal", tags=["Rotación Grupal"])

# ── Seguridad: Whitelist de atributos válidos para GROUP BY dinámico ──
# Estos son los nombres EXACTOS de columnas en Procurement.RotacionGrupal
ATRIBUTOS_VALIDOS = {
    'principio_activo', 'concentracion', 'forma_farmaceutica',
    'cantidad_presentacion', 'origen', 'fabricante',
    'contenido_neto', 'generico', 'marca', 'blister'
}

ATRIBUTOS_BASE = {'principio_activo', 'concentracion', 'forma_farmaceutica'}

# Default: recálculo si han pasado más de 15 minutos
RECALCULO_MINUTOS_DEFAULT = 15

# ── Helpers ──

def _validate_atributos(atributos_str: str) -> list:
    """
    Parsea y valida la lista de atributos solicitados.
    Siempre incluye los 3 base. Retorna lista ordenada.
    """
    if not atributos_str or atributos_str.lower() == "base":
        return sorted(ATRIBUTOS_BASE)
    
    requested = {a.strip().lower() for a in atributos_str.split(",")}
    
    # Remover "base" si viene como token
    requested.discard("base")
    
    # Validar contra whitelist
    invalid = requested - ATRIBUTOS_VALIDOS
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Atributos no válidos: {', '.join(invalid)}. "
                   f"Válidos: {', '.join(sorted(ATRIBUTOS_VALIDOS))}"
        )
    
    # Siempre incluir los 3 base
    all_attrs = ATRIBUTOS_BASE | requested
    return sorted(all_attrs)


def _parse_filtros(filtros_str: Optional[str]) -> dict:
    """Parsea filtros JSON. Valida claves contra whitelist."""
    if not filtros_str:
        return {}
    try:
        filtros = json.loads(filtros_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Filtros debe ser JSON válido")
    
    invalid_keys = set(filtros.keys()) - ATRIBUTOS_VALIDOS
    if invalid_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Claves de filtro no válidas: {', '.join(invalid_keys)}"
        )
    return filtros


def _check_and_recalculate(conn, force: bool = False, max_minutes: int = RECALCULO_MINUTOS_DEFAULT):
    """
    Verifica si la tabla RotacionGrupal necesita recálculo.
    Si force=True o ha pasado más de max_minutes, ejecuta el SP.
    Retorna True si recalculó, False si estaba fresca.
    """
    if not force:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DATEDIFF(MINUTE, MAX(ultima_actualizacion), GETDATE()) AS minutes_ago
                FROM Procurement.RotacionGrupal
            """)
            row = cursor.fetchone()
            cursor.close()
            
            if row and row.minutes_ago is not None and row.minutes_ago < max_minutes:
                return False  # Tabla fresca, no recalcular
        except Exception:
            pass  # Si falla la verificación, recalcular por seguridad
    
    try:
        cursor = conn.cursor()
        cursor.execute("EXEC Procurement.SP_RecalcularRotacionGrupal")
        cursor.commit()
        cursor.close()
        logging.info("RotacionGrupal recalculada exitosamente")
        return True
    except Exception as e:
        logging.error(f"Error recalculando RotacionGrupal: {e}")
        raise HTTPException(status_code=500, detail=f"Error en recálculo: {str(e)}")


def _build_dynamic_query(atributos: list, filtros: dict, buscar: Optional[str], 
                          page: int, page_size: int):
    """
    Construye la query dinámica con GROUP BY variable.
    Retorna (query_str, params_list) con parámetros seguros.
    """
    # Construir SELECT y GROUP BY con nombres validados (whitelist)
    select_cols = ", ".join([f"rg.{attr}" for attr in atributos])
    group_cols = ", ".join([f"rg.{attr}" for attr in atributos])
    
    # Construir descripciones: para los 3 base, traer _Des
    desc_selects = []
    for attr in atributos:
        if attr in ATRIBUTOS_BASE:
            desc_selects.append(f"MAX(eq.{attr}_Des) AS {attr}_Des")
    desc_sql = (", " + ", ".join(desc_selects)) if desc_selects else ""
    
    # WHERE clause con parámetros
    where_parts = ["rg.principio_activo IS NOT NULL"]
    params = []
    
    # Filtros de atributos (parametrizados)
    for attr, value in filtros.items():
        if attr in ATRIBUTOS_VALIDOS:  # Ya validado, pero doble check
            where_parts.append(f"rg.{attr} = ?")
            params.append(str(value))
    
    # Búsqueda por texto
    if buscar:
        where_parts.append("""(
            eq.principio_activo_Des LIKE ? 
            OR eq.descrip1art LIKE ?
            OR eq.concentracion_Des LIKE ?
        )""")
        search_param = f"%{buscar}%"
        params.extend([search_param, search_param, search_param])
    
    where_sql = " AND ".join(where_parts)
    offset = (page - 1) * page_size
    
    # Query principal
    query = f"""
    SELECT 
        {select_cols}
        {desc_sql},
        SUM(COALESCE(rg.rot_sku, 0)) AS rot_grupo,
        COUNT(*) AS skus_en_grupo,
        SUM(COALESCE(rg.existen_sku, 0)) AS inv_grupo
    FROM Procurement.RotacionGrupal rg
    LEFT JOIN Procurement.por_aprobacion_equivalencias eq 
        ON rg.codbarras = eq.codbarras
    WHERE {where_sql}
    GROUP BY {group_cols}
    HAVING SUM(COALESCE(rg.rot_sku, 0)) > 0
    ORDER BY rot_grupo DESC
    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    params.extend([offset, page_size])
    
    # Query de conteo
    count_query = f"""
    SELECT COUNT(*) AS total FROM (
        SELECT {select_cols}
        FROM Procurement.RotacionGrupal rg
        LEFT JOIN Procurement.por_aprobacion_equivalencias eq 
            ON rg.codbarras = eq.codbarras
        WHERE {where_sql}
        GROUP BY {group_cols}
        HAVING SUM(COALESCE(rg.rot_sku, 0)) > 0
    ) sub
    """
    # count_query usa los mismos params excepto offset/page_size
    count_params = params[:-2]
    
    return query, params, count_query, count_params


def _build_cached_query(filtros: dict, buscar: Optional[str], 
                         page: int, page_size: int, mode: str = "grupos"):
    """
    Construye query para lectura cached (R2 base) de la tabla materializada.
    mode: 'grupos' = agrupado por PA+Conc+FF, 'detalle' = por SKU
    """
    where_parts = ["rg.principio_activo IS NOT NULL"]
    params = []
    
    for attr, value in filtros.items():
        if attr in ATRIBUTOS_VALIDOS:
            where_parts.append(f"rg.{attr} = ?")
            params.append(str(value))
    
    if buscar:
        where_parts.append("""(
            eq.principio_activo_Des LIKE ? 
            OR eq.descrip1art LIKE ?
            OR eq.concentracion_Des LIKE ?
        )""")
        search_param = f"%{buscar}%"
        params.extend([search_param, search_param, search_param])
    
    where_sql = " AND ".join(where_parts)
    offset = (page - 1) * page_size
    
    if mode == "grupos":
        query = f"""
        SELECT 
            rg.principio_activo,
            rg.concentracion,
            rg.forma_farmaceutica,
            MAX(eq.principio_activo_Des) AS principio_activo_Des,
            MAX(eq.concentracion_Des) AS concentracion_Des,
            MAX(eq.forma_farmaceutica_Des) AS forma_farmaceutica_Des,
            MAX(rg.rot_base) AS rot_grupo,
            MAX(rg.skus_base) AS skus_en_grupo,
            MAX(rg.inv_base) AS inv_grupo
        FROM Procurement.RotacionGrupal rg
        LEFT JOIN Procurement.por_aprobacion_equivalencias eq 
            ON rg.codbarras = eq.codbarras
        WHERE {where_sql}
        GROUP BY rg.principio_activo, rg.concentracion, rg.forma_farmaceutica
        HAVING MAX(rg.rot_base) > 0
        ORDER BY rot_grupo DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
    else:  # detalle por SKU
        query = f"""
        SELECT 
            rg.codbarras,
            rg.principio_activo,
            rg.concentracion,
            rg.forma_farmaceutica,
            rg.cantidad_presentacion,
            rg.origen,
            rg.fabricante,
            rg.generico,
            rg.rot_sku,
            rg.existen_sku,
            rg.rot_base,
            rg.skus_base,
            rg.inv_base,
            eq.principio_activo_Des,
            eq.concentracion_Des,
            eq.forma_farmaceutica_Des,
            eq.descrip1art,
            eq.elasticidad_demanda
        FROM Procurement.RotacionGrupal rg
        LEFT JOIN Procurement.por_aprobacion_equivalencias eq 
            ON rg.codbarras = eq.codbarras
        WHERE {where_sql}
        ORDER BY rg.rot_base DESC, rg.rot_sku DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
    
    params.extend([offset, page_size])
    
    # Count query
    count_query = f"""
    SELECT COUNT(*) AS total
    FROM Procurement.RotacionGrupal rg
    LEFT JOIN Procurement.por_aprobacion_equivalencias eq 
        ON rg.codbarras = eq.codbarras
    WHERE {where_sql}
    """
    count_params = params[:-2]
    
    return query, params, count_query, count_params


# ── Endpoints ──

@router.get("/")
async def get_rotacion_grupal(
    atributos: str = Query("base", description="'base' para R2 cached, o lista: 'base,origen,generico'"),
    buscar: Optional[str] = Query(None, description="Búsqueda por texto en descripción/PA"),
    filtros: Optional[str] = Query(None, description='Filtros JSON: {"origen":"3","generico":"1"}'),
    mode: str = Query("grupos", description="'grupos' = agrupado, 'detalle' = por SKU"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    max_cache_minutes: int = Query(RECALCULO_MINUTOS_DEFAULT, ge=1, le=1440,
                                    description="Máximo minutos antes de recalcular (default 15)")
):
    """
    Motor de Rotación Grupal Dinámica.
    
    Modos de uso:
    - **Cached (R2):** `?atributos=base` → Lee de tabla materializada (~10ms)
    - **Dinámico:** `?atributos=base,origen` → Calcula on-the-fly (~1-3s)
    - **Con filtros:** `?atributos=base,origen&filtros={"origen":"3"}` → Solo productos de origen=3
    - **Búsqueda:** `?buscar=acetaminofen` → Filtra por texto
    - **Detalle SKU:** `?mode=detalle` → Muestra cada SKU individual
    """
    try:
        conn = database.get_db_connection()
        
        # Verificar frescura y recalcular si necesario
        _check_and_recalculate(conn, force=False, max_minutes=max_cache_minutes)
        
        # Parsear inputs
        parsed_atributos = _validate_atributos(atributos)
        parsed_filtros = _parse_filtros(filtros)
        
        is_base_only = set(parsed_atributos) == ATRIBUTOS_BASE and not parsed_filtros
        
        # Decidir: cached o dinámico
        if is_base_only or (set(parsed_atributos) == ATRIBUTOS_BASE):
            # Cached path — lectura directa de tabla materializada
            query, params, count_query, count_params = _build_cached_query(
                parsed_filtros, buscar, page, page_size, mode
            )
            source = "cached"
        else:
            # Dynamic path — GROUP BY variable
            query, params, count_query, count_params = _build_dynamic_query(
                parsed_atributos, parsed_filtros, buscar, page, page_size
            )
            source = "dynamic"
            mode = "grupos"  # Dinámico siempre retorna grupos
        
        # Ejecutar queries
        cursor = conn.cursor()
        
        cursor.execute(count_query, count_params)
        total = cursor.fetchone().total
        
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            item = {}
            for i, col in enumerate(columns):
                val = row[i]
                # Convertir Decimal a float para JSON
                if hasattr(val, 'as_tuple'):
                    val = float(val)
                elif isinstance(val, datetime):
                    val = val.isoformat()
                item[col] = val
            results.append(item)
        
        cursor.close()
        conn.close()
        
        return {
            "source": source,
            "mode": mode,
            "atributos": parsed_atributos,
            "filtros": parsed_filtros,
            "buscar": buscar,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
            "data": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error en rotación grupal: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/atributos")
async def get_atributos():
    """
    Lista de atributos disponibles para agrupación dinámica.
    Incluye los 3 base (siempre activos) y los extensibles.
    """
    try:
        conn = database.get_db_connection()
        query = """
            SELECT id, nombre_campo, etiqueta, es_base, activo, cardinalidad, descripcion
            FROM Procurement.RotacionGrupal_Atributos
            ORDER BY es_base DESC, id
        """
        df = pd.read_sql(query, conn)
        conn.close()
        
        atributos = []
        for _, row in df.iterrows():
            atributos.append({
                "id": int(row['id']),
                "nombre_campo": row['nombre_campo'],
                "etiqueta": row['etiqueta'],
                "es_base": bool(row['es_base']),
                "activo": bool(row['activo']),
                "cardinalidad": int(row['cardinalidad']) if pd.notna(row['cardinalidad']) else None,
                "descripcion": row['descripcion']
            })
        
        return {"atributos": atributos}
        
    except Exception as e:
        logging.error(f"Error obteniendo atributos: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/freshness")
async def get_freshness():
    """
    Estado de frescura de la tabla materializada.
    Útil para el frontend para mostrar cuándo fue la última actualización.
    """
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                MIN(ultima_actualizacion) AS oldest_update,
                MAX(ultima_actualizacion) AS newest_update,
                COUNT(*) AS total_rows,
                DATEDIFF(MINUTE, MAX(ultima_actualizacion), GETDATE()) AS minutes_since_update
            FROM Procurement.RotacionGrupal
        """)
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row or row.total_rows == 0:
            return {
                "status": "empty",
                "message": "La tabla RotacionGrupal está vacía. Ejecute recálculo.",
                "total_rows": 0
            }
        
        minutes = row.minutes_since_update or 0
        if minutes <= RECALCULO_MINUTOS_DEFAULT:
            status = "fresh"
        elif minutes <= 60:
            status = "stale"
        else:
            status = "outdated"
        
        return {
            "status": status,
            "oldest_update": row.oldest_update.isoformat() if row.oldest_update else None,
            "newest_update": row.newest_update.isoformat() if row.newest_update else None,
            "total_rows": row.total_rows,
            "minutes_since_update": minutes,
            "threshold_minutes": RECALCULO_MINUTOS_DEFAULT
        }
        
    except Exception as e:
        logging.error(f"Error verificando frescura: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recalcular")
async def force_recalculate():
    """
    Fuerza un recálculo inmediato del SP.
    Útil después de cambios masivos de datos.
    """
    try:
        conn = database.get_db_connection()
        recalculated = _check_and_recalculate(conn, force=True)
        conn.close()
        
        return {
            "status": "ok",
            "recalculated": recalculated,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error en recálculo forzado: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
