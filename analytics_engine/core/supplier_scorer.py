"""
Calificación de Proveedores (Scorecard) — Analytics Engine
============================================================
Calcula un score compuesto 0-1000 para cada proveedor activo,
evaluando 6 dimensiones que complementan el PDR (micro, producto-proveedor)
con una visión macro (proveedor completo).

Variables del Scorecard:
  1. Competitividad de precio — ¿Cuántas veces es el más barato?
  2. Frescura de datos — ¿Cada cuánto actualiza su catálogo?
  3. Amplitud de catálogo — ¿Cuántos productos ofrece?
  4. Tasa de anomalías — ¿Cuántos precios anómalos tiene?
  5. Vitalidad de stock (PDR promedio) — ¿Cuán confiables sus datos?
  6. Calidad de datos — ¿Cuántas validaciones GX pasa?
"""
import logging
from datetime import datetime

import numpy as np
import pandas as pd

logger = logging.getLogger("AnalyticsEngine.SupplierScorer")

# Pesos configurables (suman 1.0)
DEFAULT_WEIGHTS = {
    "competitividad_precio": 0.25,
    "frescura_datos": 0.15,
    "amplitud_catalogo": 0.15,
    "tasa_anomalias": 0.15,
    "vitalidad_pdr": 0.20,
    "calidad_datos": 0.10,
}


def score_suppliers(
    *,
    weights: dict = None,
    anomaly_results: dict = None,
) -> dict:
    """
    Calcula el scorecard de todos los proveedores activos.
    
    Args:
        weights: Pesos personalizados para las 6 dimensiones.
        anomaly_results: Resultados del anomaly_detector (si ya se ejecutó).
    
    Returns:
        {
            "scores": [
                {
                    "proveedor": str,
                    "score_total": int (0-1000),
                    "dimensiones": { competitividad: ..., frescura: ..., ... },
                    "rank": int,
                },
                ...
            ],
            "metadata": { "timestamp": ..., "weights": ..., "n_proveedores": ... }
        }
    """
    from .db import query_dataframe, db_cursor
    
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    
    # ── Dimensión 1: Competitividad de precio ──
    competitividad = _calcular_competitividad()
    
    # ── Dimensión 2: Frescura de datos ──
    frescura = _calcular_frescura()
    
    # ── Dimensión 3: Amplitud de catálogo ──
    amplitud = _calcular_amplitud()
    
    # ── Dimensión 4: Tasa de anomalías ──
    anomalias = _calcular_tasa_anomalias(anomaly_results)
    
    # ── Dimensión 5: Vitalidad PDR promedio ──
    pdr = _calcular_pdr_promedio()
    
    # ── Dimensión 6: Calidad de datos (placeholder hasta que GX acumule logs) ──
    calidad = _calcular_calidad()
    
    # ── Combinar scores ──
    proveedores = set()
    for d in [competitividad, frescura, amplitud, anomalias, pdr, calidad]:
        proveedores.update(d.keys())
    
    scores = []
    for prov in sorted(proveedores):
        dims = {
            "competitividad_precio": competitividad.get(prov, 0.5),
            "frescura_datos": frescura.get(prov, 0.5),
            "amplitud_catalogo": amplitud.get(prov, 0.5),
            "tasa_anomalias": anomalias.get(prov, 0.8),
            "vitalidad_pdr": pdr.get(prov, 0.5),
            "calidad_datos": calidad.get(prov, 0.8),
        }
        
        score_total = sum(dims[k] * w[k] for k in w) * 1000
        score_total = int(min(max(score_total, 0), 1000))
        
        scores.append({
            "proveedor": prov,
            "score_total": score_total,
            "dimensiones": {k: round(v, 4) for k, v in dims.items()},
        })
    
    # Ordenar y asignar rank
    scores.sort(key=lambda x: x["score_total"], reverse=True)
    for i, s in enumerate(scores, 1):
        s["rank"] = i
    
    # Persistir en Procurement.ProveedorScorecard
    _persistir_scores(scores)
    
    return {
        "scores": scores,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "weights": w,
            "n_proveedores": len(scores),
        }
    }


def _calcular_competitividad() -> dict:
    """
    ¿Cuántas veces este proveedor tiene el precio más bajo?
    Retorna dict {proveedor: score 0.0-1.0}
    """
    from .db import query_dataframe
    
    sql = """
        SELECT 
            proveedor,
            COUNT(*) AS total_productos,
            SUM(CASE WHEN precio_unitario = precio_min THEN 1 ELSE 0 END) AS veces_mas_barato
        FROM Analitica.Mercado_Vivo mv
        INNER JOIN Analitica.Estadisticas_Producto ep
            ON mv.codbarras = ep.codbarras
        WHERE mv.precio_unitario > 0
          AND ep.total_proveedores >= 2
        GROUP BY proveedor
    """
    df = query_dataframe(sql)
    if df.empty:
        return {}
    
    df["ratio"] = df["veces_mas_barato"] / df["total_productos"]
    return dict(zip(df["proveedor"], df["ratio"].clip(0, 1)))


def _calcular_frescura() -> dict:
    """
    Qué tan reciente es la última carga del proveedor.
    Score 1.0 = hoy, 0.0 = hace 30+ días.
    """
    from .db import query_dataframe
    
    sql = """
        SELECT 
            proveedor,
            MAX(fecha_carga) AS ultima_carga,
            DATEDIFF(HOUR, MAX(fecha_carga), GETDATE()) AS horas_desde_carga
        FROM Analitica.Mercado_Vivo
        GROUP BY proveedor
    """
    df = query_dataframe(sql)
    if df.empty:
        return {}
    
    # Score: 1.0 si <24h, decae linealmente hasta 0 en 720h (30 días)
    df["score"] = (1 - df["horas_desde_carga"] / 720).clip(0, 1)
    return dict(zip(df["proveedor"], df["score"]))


def _calcular_amplitud() -> dict:
    """
    Cuántos productos ofrece vs el proveedor con más productos.
    """
    from .db import query_dataframe
    
    sql = """
        SELECT proveedor, COUNT(DISTINCT codbarras) AS n_productos
        FROM Analitica.Mercado_Vivo
        GROUP BY proveedor
    """
    df = query_dataframe(sql)
    if df.empty:
        return {}
    
    max_productos = df["n_productos"].max()
    if max_productos == 0:
        return {}
    
    df["score"] = df["n_productos"] / max_productos
    return dict(zip(df["proveedor"], df["score"].clip(0, 1)))


def _calcular_tasa_anomalias(anomaly_results: dict = None) -> dict:
    """
    Inverso de la tasa de anomalías. Más anomalías = peor score.
    """
    if not anomaly_results or not anomaly_results.get("anomalias"):
        # Sin datos de anomalías, todos obtienen score neutral
        return {}
    
    from collections import Counter
    
    # Contar anomalías por proveedor
    conteo = Counter(a["proveedor"] for a in anomaly_results["anomalias"])
    total = anomaly_results.get("total_evaluados", 1)
    
    scores = {}
    for prov, n_anomalias in conteo.items():
        # Score = 1 - (anomalías / total evaluados), mínimo 0
        scores[prov] = max(1 - (n_anomalias / total * 10), 0)
    
    return scores


def _calcular_pdr_promedio() -> dict:
    """PDR score promedio de los productos de cada proveedor."""
    from .db import query_dataframe
    
    sql = """
        SELECT proveedor, AVG(pdr_score) AS pdr_promedio
        FROM Analitica.Mercado_Vivo_PDR
        GROUP BY proveedor
    """
    try:
        df = query_dataframe(sql)
        if df.empty:
            return {}
        return dict(zip(df["proveedor"], df["pdr_promedio"].clip(0, 1)))
    except Exception:
        # Mercado_Vivo_PDR puede no existir aún
        return {}


def _calcular_calidad() -> dict:
    """
    Placeholder: calidad de datos basada en GX.
    Se llenará cuando GX acumule logs de validación.
    Por ahora, todos los proveedores obtienen 0.8 (neutral-positivo).
    """
    return {}


def _persistir_scores(scores: list):
    """Guarda los scores en Procurement.ProveedorScorecard."""
    from .db import db_cursor
    
    try:
        with db_cursor() as cursor:
            for s in scores:
                cursor.execute("""
                    MERGE Procurement.ProveedorScorecard AS target
                    USING (SELECT ? AS proveedor) AS source
                    ON target.proveedor = source.proveedor
                    WHEN MATCHED THEN
                        UPDATE SET 
                            score_total = ?,
                            competitividad = ?,
                            frescura = ?,
                            amplitud = ?,
                            anomalias = ?,
                            pdr_promedio = ?,
                            calidad = ?,
                            updated_at = GETDATE()
                    WHEN NOT MATCHED THEN
                        INSERT (proveedor, score_total, competitividad, frescura, 
                                amplitud, anomalias, pdr_promedio, calidad, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, GETDATE());
                """,
                    # MERGE params
                    s["proveedor"],
                    # UPDATE params
                    s["score_total"],
                    s["dimensiones"]["competitividad_precio"],
                    s["dimensiones"]["frescura_datos"],
                    s["dimensiones"]["amplitud_catalogo"],
                    s["dimensiones"]["tasa_anomalias"],
                    s["dimensiones"]["vitalidad_pdr"],
                    s["dimensiones"]["calidad_datos"],
                    # INSERT params
                    s["proveedor"],
                    s["score_total"],
                    s["dimensiones"]["competitividad_precio"],
                    s["dimensiones"]["frescura_datos"],
                    s["dimensiones"]["amplitud_catalogo"],
                    s["dimensiones"]["tasa_anomalias"],
                    s["dimensiones"]["vitalidad_pdr"],
                    s["dimensiones"]["calidad_datos"],
                )
        logger.info(f"Scores persistidos para {len(scores)} proveedores")
    except Exception as e:
        logger.warning(f"No se pudieron persistir scores (tabla puede no existir): {e}")
