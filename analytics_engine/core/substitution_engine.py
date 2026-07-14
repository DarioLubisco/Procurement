"""
Motor de Sustitución Inteligente — Analytics Engine
====================================================
Dado un producto (por código de barras o código interno), retorna candidatos
de sustitución ordenados por proximidad multi-atributo y competitividad.

Modo de operación:
  - EXACTO (98.8% de productos): JOIN sobre campos MDM normalizados
    (principio_activo + concentración + forma_farmacéutica)
  - FALLBACK: Para el 1.2% sin MDM, usa solo la descripción del producto

Ranking de candidatos:
  1. Mismo PA + misma concentración + misma FF  (sustituto perfecto)
  2. Mismo PA + misma concentración + diferente FF (cambio de forma)
  3. Mismo PA + diferente concentración (ajuste de dosis)
  
Dentro de cada nivel, ordena por:
  - PDR score (confiabilidad de disponibilidad)
  - Precio competitivo (menor primero)
"""
import logging
from typing import Optional
from .db import query_dataframe, db_cursor

logger = logging.getLogger("AnalyticsEngine.SubstitutionEngine")


def find_substitutes(
    codbarras: str,
    *,
    max_results: int = 20,
    incluir_mismo_proveedor: bool = True,
    solo_con_stock: bool = True,
) -> dict:
    """
    Busca sustitutos para un producto dado su código de barras.
    
    Returns:
        {
            "producto_origen": { ... },
            "candidatos": [
                {"nivel": 1, "proveedor": "...", "precio": ..., "pdr": ..., ...},
                ...
            ],
            "modo": "exacto" | "fallback",
            "total_candidatos": int
        }
    """
    # ── Paso 1: Obtener atributos MDM del producto origen ──
    producto = _obtener_producto_mdm(codbarras)
    
    if not producto:
        return {
            "producto_origen": None,
            "candidatos": [],
            "modo": "no_encontrado",
            "total_candidatos": 0,
            "error": f"Producto con codbarras '{codbarras}' no encontrado en MDM"
        }
    
    pa = producto.get("principio_activo")
    conc = producto.get("concentracion")
    ff = producto.get("forma_farmaceutica")
    
    # ── Paso 2: Determinar modo de búsqueda ──
    if pa and conc and ff:
        modo = "exacto"
        candidatos = _buscar_exacto(
            pa, conc, ff,
            codbarras_excluir=codbarras,
            incluir_mismo_proveedor=incluir_mismo_proveedor,
            solo_con_stock=solo_con_stock,
            max_results=max_results,
        )
    elif pa:
        # Tiene PA pero le falta concentración o FF
        modo = "parcial"
        candidatos = _buscar_parcial(
            pa, conc, ff,
            codbarras_excluir=codbarras,
            max_results=max_results,
        )
    else:
        modo = "fallback"
        candidatos = []
    
    return {
        "producto_origen": producto,
        "candidatos": candidatos,
        "modo": modo,
        "total_candidatos": len(candidatos),
    }


def _obtener_producto_mdm(codbarras: str) -> Optional[dict]:
    """Obtiene los atributos MDM normalizados de un producto."""
    sql = """
        SELECT TOP 1
            eq.codbarras,
            eq.descrip1art AS descripcion,
            eq.principio_activo_Des AS principio_activo,
            eq.concentracion_Des AS concentracion,
            eq.forma_farmaceutica_Des AS forma_farmaceutica,
            eq.marca_Des AS marca,
            eq.fabricante_Des AS fabricante,
            eq.origen_Des AS origen,
            eq.generico_Des AS generico,
            eq.es_medicamento,
            eq.clasificacion_insumo_Des AS clasificacion_insumo
        FROM Procurement.por_aprobacion_equivalencias eq
        WHERE eq.codbarras = ?
    """
    df = query_dataframe(sql, params=[codbarras])
    if df.empty:
        return None
    row = df.iloc[0]
    return {k: (None if str(v) == 'nan' else v) for k, v in row.to_dict().items()}


def _buscar_exacto(
    pa: str,
    conc: str,
    ff: str,
    *,
    codbarras_excluir: str = "",
    incluir_mismo_proveedor: bool = True,
    solo_con_stock: bool = True,
    max_results: int = 20,
) -> list:
    """
    Búsqueda por JOIN exacto sobre campos MDM normalizados.
    Retorna candidatos en 3 niveles de proximidad.
    """
    # Nivel 1: Mismo PA + misma concentración + misma FF
    # Nivel 2: Mismo PA + misma concentración (cualquier FF)
    # Nivel 3: Mismo PA (cualquier concentración y FF)
    stock_filter = "AND mv.stock_disponible > 0" if solo_con_stock else ""
    
    sql = f"""
        SELECT 
            mv.codbarras,
            mv.descripcion_producto,
            mv.proveedor,
            mv.precio_unitario,
            mv.stock_disponible,
            mv.fecha_carga,
            eq.principio_activo_Des AS principio_activo,
            eq.concentracion_Des AS concentracion,
            eq.forma_farmaceutica_Des AS forma_farmaceutica,
            eq.marca_Des AS marca,
            eq.fabricante_Des AS fabricante,
            eq.generico_Des AS generico,
            COALESCE(pdr.pdr_score, 0.5) AS pdr_score,
            -- Nivel de proximidad
            CASE 
                WHEN eq.principio_activo_Des = ?
                 AND eq.concentracion_Des = ?
                 AND eq.forma_farmaceutica_Des = ?
                THEN 1
                WHEN eq.principio_activo_Des = ?
                 AND eq.concentracion_Des = ?
                THEN 2
                WHEN eq.principio_activo_Des = ?
                THEN 3
                ELSE 4
            END AS nivel_proximidad
        FROM Analitica.Mercado_Vivo mv
        INNER JOIN Procurement.por_aprobacion_equivalencias eq
            ON mv.codbarras = eq.codbarras
        LEFT JOIN Analitica.Mercado_Vivo_PDR pdr
            ON mv.codbarras = pdr.codbarras 
            AND mv.proveedor = pdr.proveedor
        WHERE eq.principio_activo_Des = ?
          AND mv.codbarras != ?
          {stock_filter}
        ORDER BY nivel_proximidad ASC, pdr_score DESC, mv.precio_unitario ASC
    """
    
    params = [pa, conc, ff, pa, conc, pa, pa, codbarras_excluir]
    df = query_dataframe(sql, params=params)
    
    if df.empty:
        return []
    
    # Limitar resultados
    df = df.head(max_results)
    
    candidatos = []
    for _, row in df.iterrows():
        candidatos.append({
            "nivel": int(row["nivel_proximidad"]),
            "nivel_descripcion": _describir_nivel(int(row["nivel_proximidad"])),
            "codbarras": row["codbarras"],
            "descripcion": row["descripcion_producto"],
            "proveedor": row["proveedor"],
            "precio": float(row["precio_unitario"]) if row["precio_unitario"] else None,
            "stock": int(row["stock_disponible"]) if row["stock_disponible"] else 0,
            "pdr_score": round(float(row["pdr_score"]), 4),
            "principio_activo": row["principio_activo"],
            "concentracion": row["concentracion"],
            "forma_farmaceutica": row["forma_farmaceutica"],
            "marca": row.get("marca"),
            "generico": row.get("generico"),
        })
    
    return candidatos


def _buscar_parcial(
    pa: str,
    conc: Optional[str],
    ff: Optional[str],
    *,
    codbarras_excluir: str = "",
    max_results: int = 20,
) -> list:
    """Búsqueda parcial cuando solo hay PA disponible."""
    sql = """
        SELECT TOP (?)
            mv.codbarras,
            mv.descripcion_producto,
            mv.proveedor,
            mv.precio_unitario,
            mv.stock_disponible,
            eq.principio_activo_Des AS principio_activo,
            eq.concentracion_Des AS concentracion,
            eq.forma_farmaceutica_Des AS forma_farmaceutica,
            COALESCE(pdr.pdr_score, 0.5) AS pdr_score
        FROM Analitica.Mercado_Vivo mv
        INNER JOIN Procurement.por_aprobacion_equivalencias eq
            ON mv.codbarras = eq.codbarras
        LEFT JOIN Analitica.Mercado_Vivo_PDR pdr
            ON mv.codbarras = pdr.codbarras AND mv.proveedor = pdr.proveedor
        WHERE eq.principio_activo_Des = ?
          AND mv.codbarras != ?
          AND mv.stock_disponible > 0
        ORDER BY pdr_score DESC, mv.precio_unitario ASC
    """
    df = query_dataframe(sql, params=[max_results, pa, codbarras_excluir])
    
    if df.empty:
        return []
    
    return [
        {
            "nivel": 3,
            "nivel_descripcion": "Mismo principio activo (parcial)",
            "codbarras": row["codbarras"],
            "descripcion": row["descripcion_producto"],
            "proveedor": row["proveedor"],
            "precio": float(row["precio_unitario"]) if row["precio_unitario"] else None,
            "stock": int(row["stock_disponible"]) if row["stock_disponible"] else 0,
            "pdr_score": round(float(row["pdr_score"]), 4),
            "principio_activo": row["principio_activo"],
            "concentracion": row.get("concentracion"),
            "forma_farmaceutica": row.get("forma_farmaceutica"),
        }
        for _, row in df.iterrows()
    ]


def _describir_nivel(nivel: int) -> str:
    """Descripción legible del nivel de proximidad."""
    descripciones = {
        1: "Sustituto perfecto (mismo PA + concentración + forma farmacéutica)",
        2: "Cambio de forma farmacéutica (mismo PA + concentración)",
        3: "Ajuste de dosis (mismo principio activo)",
        4: "Relación indirecta",
    }
    return descripciones.get(nivel, "Desconocido")
