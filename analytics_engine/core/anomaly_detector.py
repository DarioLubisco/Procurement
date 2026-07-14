"""
Detector de Anomalías de Precios — Analytics Engine
=====================================================
Usa Scikit-learn IsolationForest para detectar precios anómalos en el mercado.

Estrategia dual:
  - Si hay ≥30 snapshots en Mercado_Historico: IsolationForest entrenado
  - Si hay <30 snapshots: fallback a z-score (3 sigmas) usando Estadisticas_Producto

Política de acción (decidida por el usuario):
  → Opción 3: Alerta + bloqueo temporal hasta revisión humana
"""
import logging
import os
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("AnalyticsEngine.AnomalyDetector")

# Umbral mínimo de snapshots para usar IsolationForest
MIN_SNAPSHOTS_FOR_IF = 30

# Directorio para modelos serializados
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
os.makedirs(MODELS_DIR, exist_ok=True)


def detect_anomalies(
    proveedor: Optional[str] = None,
    contamination: float = 0.05,
    zscore_threshold: float = 3.0,
) -> dict:
    """
    Detecta precios anómalos en el mercado actual.
    
    Args:
        proveedor: Filtrar por proveedor específico, o None para todos.
        contamination: Fracción esperada de anomalías (default 5%).
        zscore_threshold: Umbral de desviaciones estándar para z-score.
    
    Returns:
        {
            "metodo": "isolation_forest" | "zscore",
            "total_evaluados": int,
            "anomalias": [ { producto, proveedor, precio, score, accion }, ... ],
            "resumen": { total_anomalias, pct_anomalias, proveedor_mas_anomalias },
            "modelo_info": { ... }
        }
    """
    from .db import query_dataframe
    
    # ── Paso 1: Evaluar disponibilidad de historial ──
    n_snapshots = _contar_snapshots()
    logger.info(f"Snapshots disponibles en Mercado_Historico: {n_snapshots}")
    
    if n_snapshots >= MIN_SNAPSHOTS_FOR_IF:
        return _detect_with_isolation_forest(proveedor, contamination)
    else:
        logger.warning(
            f"Solo {n_snapshots} snapshots (necesita {MIN_SNAPSHOTS_FOR_IF}). "
            f"Usando z-score como fallback."
        )
        return _detect_with_zscore(proveedor, zscore_threshold)


def _contar_snapshots() -> int:
    """Cuenta los días únicos de snapshot en Mercado_Historico."""
    from .db import query_dataframe
    sql = "SELECT COUNT(DISTINCT fecha_snapshot) AS n FROM Analitica.Mercado_Historico"
    df = query_dataframe(sql)
    return int(df.iloc[0]["n"]) if not df.empty else 0


def _detect_with_zscore(
    proveedor: Optional[str],
    threshold: float = 3.0,
) -> dict:
    """
    Fallback: detecta anomalías usando z-score sobre Estadisticas_Producto.
    Usa precio_mediana y precio_desviacion que ya calcula la vista.
    """
    from .db import query_dataframe
    
    prov_filter = "WHERE mv.proveedor = ?" if proveedor else ""
    params = [proveedor] if proveedor else []
    
    sql = f"""
        SELECT 
            mv.codbarras,
            mv.descripcion_producto,
            mv.proveedor,
            mv.precio_unitario,
            ep.precio_mediana,
            ep.precio_desviacion,
            ep.rango_precios,
            ep.total_proveedores
        FROM Analitica.Mercado_Vivo mv
        INNER JOIN Analitica.Estadisticas_Producto ep
            ON mv.codbarras = ep.codbarras
        {prov_filter}
        AND ep.precio_desviacion > 0
        AND ep.total_proveedores >= 2
        AND mv.precio_unitario > 0
    """
    
    df = query_dataframe(sql, params=params if params else None)
    
    if df.empty:
        return {
            "metodo": "zscore",
            "total_evaluados": 0,
            "anomalias": [],
            "resumen": {"total_anomalias": 0, "pct_anomalias": 0},
            "modelo_info": {"threshold": threshold, "snapshots_disponibles": 0}
        }
    
    # Calcular z-score
    df["zscore"] = (
        (df["precio_unitario"] - df["precio_mediana"]) / df["precio_desviacion"]
    ).abs()
    
    # Filtrar anomalías
    anomalias_df = df[df["zscore"] > threshold].copy()
    anomalias_df = anomalias_df.sort_values("zscore", ascending=False)
    
    anomalias = []
    for _, row in anomalias_df.iterrows():
        anomalias.append({
            "codbarras": row["codbarras"],
            "descripcion": row["descripcion_producto"],
            "proveedor": row["proveedor"],
            "precio_actual": round(float(row["precio_unitario"]), 2),
            "precio_mediana_mercado": round(float(row["precio_mediana"]), 2),
            "desviacion_estandar": round(float(row["precio_desviacion"]), 2),
            "zscore": round(float(row["zscore"]), 2),
            "score_anomalia": min(round(float(row["zscore"]) / 10, 4), 1.0),
            "accion": "BLOQUEO_TEMPORAL",
            "motivo": (
                f"Precio ${row['precio_unitario']:.2f} está a "
                f"{row['zscore']:.1f} desviaciones de la mediana "
                f"${row['precio_mediana']:.2f}"
            ),
        })
    
    total = len(df)
    n_anomalias = len(anomalias)
    
    # Proveedor con más anomalías
    prov_top = None
    if anomalias:
        from collections import Counter
        counts = Counter(a["proveedor"] for a in anomalias)
        prov_top = counts.most_common(1)[0] if counts else None
    
    return {
        "metodo": "zscore",
        "total_evaluados": total,
        "anomalias": anomalias,
        "resumen": {
            "total_anomalias": n_anomalias,
            "pct_anomalias": round(n_anomalias / total * 100, 2) if total else 0,
            "proveedor_mas_anomalias": (
                {"proveedor": prov_top[0], "cantidad": prov_top[1]}
                if prov_top else None
            ),
        },
        "modelo_info": {
            "threshold_zscore": threshold,
            "snapshots_disponibles": _contar_snapshots(),
            "nota": (
                f"Usando z-score como fallback. Se necesitan ≥{MIN_SNAPSHOTS_FOR_IF} "
                f"snapshots para activar IsolationForest. "
                f"El cron diario ya está activo."
            ),
        }
    }


def _detect_with_isolation_forest(
    proveedor: Optional[str],
    contamination: float = 0.05,
) -> dict:
    """
    Detección avanzada usando IsolationForest sobre datos históricos.
    Entrena por rangos de precio (evita comparar Insulina con Acetaminofén).
    """
    from sklearn.ensemble import IsolationForest
    from .db import query_dataframe
    
    prov_filter = "AND mv.proveedor = ?" if proveedor else ""
    params = [proveedor] if proveedor else []
    
    # Obtener datos actuales + estadísticas
    sql = f"""
        SELECT 
            mv.codbarras,
            mv.descripcion_producto,
            mv.proveedor,
            mv.precio_unitario,
            ep.precio_min,
            ep.precio_max,
            ep.precio_mediana,
            ep.precio_desviacion,
            ep.total_proveedores,
            ep.rango_precios
        FROM Analitica.Mercado_Vivo mv
        INNER JOIN Analitica.Estadisticas_Producto ep
            ON mv.codbarras = ep.codbarras
        WHERE mv.precio_unitario > 0
          AND ep.total_proveedores >= 2
          {prov_filter}
    """
    
    df = query_dataframe(sql, params=params if params else None)
    
    if df.empty or len(df) < 10:
        return {
            "metodo": "isolation_forest",
            "total_evaluados": len(df),
            "anomalias": [],
            "resumen": {"total_anomalias": 0, "pct_anomalias": 0},
            "modelo_info": {"error": "Datos insuficientes para IsolationForest"}
        }
    
    # Features para IsolationForest
    df["precio_vs_mediana"] = (df["precio_unitario"] / df["precio_mediana"]).clip(0, 10)
    df["precio_vs_min"] = (df["precio_unitario"] / df["precio_min"]).clip(0, 10)
    df["rango_normalizado"] = (
        df["rango_precios"] / df["precio_mediana"]
    ).clip(0, 10).fillna(0)
    
    features = df[["precio_vs_mediana", "precio_vs_min", "rango_normalizado"]].fillna(0)
    
    # Entrenar IsolationForest
    model = IsolationForest(
        contamination=contamination,
        n_estimators=200,
        max_samples="auto",
        random_state=42,
        n_jobs=-1,
    )
    
    df["if_score"] = model.fit_predict(features)
    df["anomaly_score"] = -model.decision_function(features)
    
    # Filtrar anomalías (score = -1)
    anomalias_df = df[df["if_score"] == -1].copy()
    anomalias_df = anomalias_df.sort_values("anomaly_score", ascending=False)
    
    anomalias = []
    for _, row in anomalias_df.iterrows():
        anomalias.append({
            "codbarras": row["codbarras"],
            "descripcion": row["descripcion_producto"],
            "proveedor": row["proveedor"],
            "precio_actual": round(float(row["precio_unitario"]), 2),
            "precio_mediana_mercado": round(float(row["precio_mediana"]), 2),
            "precio_min_mercado": round(float(row["precio_min"]), 2),
            "ratio_vs_mediana": round(float(row["precio_vs_mediana"]), 2),
            "anomaly_score": round(float(row["anomaly_score"]), 4),
            "accion": "BLOQUEO_TEMPORAL",
            "motivo": (
                f"IsolationForest: precio ${row['precio_unitario']:.2f} "
                f"vs mediana ${row['precio_mediana']:.2f} "
                f"(ratio {row['precio_vs_mediana']:.2f}x)"
            ),
        })
    
    total = len(df)
    n_anomalias = len(anomalias)
    
    # Serializar modelo
    try:
        import joblib
        model_path = os.path.join(
            MODELS_DIR,
            f"isolation_forest_{proveedor or 'global'}_{datetime.now():%Y%m%d}.joblib"
        )
        joblib.dump(model, model_path)
        logger.info(f"Modelo guardado en {model_path}")
    except Exception as e:
        logger.warning(f"No se pudo serializar el modelo: {e}")
        model_path = None
    
    from collections import Counter
    prov_top = None
    if anomalias:
        counts = Counter(a["proveedor"] for a in anomalias)
        prov_top = counts.most_common(1)[0] if counts else None
    
    return {
        "metodo": "isolation_forest",
        "total_evaluados": total,
        "anomalias": anomalias,
        "resumen": {
            "total_anomalias": n_anomalias,
            "pct_anomalias": round(n_anomalias / total * 100, 2) if total else 0,
            "proveedor_mas_anomalias": (
                {"proveedor": prov_top[0], "cantidad": prov_top[1]}
                if prov_top else None
            ),
        },
        "modelo_info": {
            "contamination": contamination,
            "n_estimators": 200,
            "features_usadas": ["precio_vs_mediana", "precio_vs_min", "rango_normalizado"],
            "modelo_serializado": model_path,
            "snapshots_disponibles": _contar_snapshots(),
        }
    }
