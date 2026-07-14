"""
Validación de Calidad de Datos ETL — Analytics Engine
======================================================
Valida los archivos de proveedores ANTES de insertar en las tablas
Proveedores.*_Inventario, usando reglas declarativas inspiradas en
Great Expectations pero implementadas de forma ligera (sin el runtime
completo de GX) para funcionar en los scripts ETL de Debian.

Pipeline: Archivo crudo → validate() → impute() → INSERT

Incluye:
  - Validación estructural (columnas, tipos, nulls)
  - Validación semántica (rangos de precio, códigos de barras)
  - Imputación controlada (precio NULL → KNN, stock NULL → 0)
"""
import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("AnalyticsEngine.DataQuality")

# ══════════════════════════════════════════════════════════════
# REGLAS DE VALIDACIÓN POR VARIANTE DE ESQUEMA (A-E)
# ══════════════════════════════════════════════════════════════

VARIANT_RULES = {
    # Variante A: 13 proveedores (Andicar, Biogenetica, Cobeca13, Cristmed,
    # Dropharma, Emmanuelle, Gama, Intercontinental, Mastranto,
    # MastrantoB, MastrantoC, OPTIMA, VitalClinic)
    "A": {
        "columnas_requeridas": [
            "codigo_barras", "descripcion", "precio_unitario", "stock_disponible"
        ],
        "columnas_opcionales": [
            "laboratorio", "principio_activo", "concentracion"
        ],
        "reglas": [
            {"campo": "codigo_barras", "tipo": "not_null"},
            {"campo": "codigo_barras", "tipo": "length_between", "min": 3, "max": 50},
            {"campo": "precio_unitario", "tipo": "between", "min": 0, "max": 999999},
            {"campo": "stock_disponible", "tipo": "type_check", "expected": "numeric"},
        ],
    },
    # Variante B: 3 proveedores (DROCERCA, ITS, NENA)
    "B": {
        "columnas_requeridas": [
            "CodBar", "Descripcion", "Precio", "Existencia"
        ],
        "columnas_opcionales": ["Laboratorio"],
        "reglas": [
            {"campo": "CodBar", "tipo": "not_null"},
            {"campo": "Precio", "tipo": "between", "min": 0, "max": 999999},
            {"campo": "Existencia", "tipo": "type_check", "expected": "numeric"},
        ],
    },
    # Variante C: 3 proveedores (InsuamincaM, InsuamincaB, InsuamincaG)
    "C": {
        "columnas_requeridas": [
            "CODIGO", "DESCRIPCION", "PVP", "EXISTENCIA"
        ],
        "columnas_opcionales": ["LABORATORIO", "PRINCIPIO_ACTIVO"],
        "reglas": [
            {"campo": "CODIGO", "tipo": "not_null"},
            {"campo": "PVP", "tipo": "between", "min": 0, "max": 999999},
            {"campo": "EXISTENCIA", "tipo": "type_check", "expected": "numeric"},
        ],
    },
    # Variante D: 2 proveedores (Zakipharma, VitalClinic alt)
    "D": {
        "columnas_requeridas": [
            "ean", "nombre", "precio", "cantidad"
        ],
        "columnas_opcionales": ["marca", "laboratorio"],
        "reglas": [
            {"campo": "ean", "tipo": "not_null"},
            {"campo": "precio", "tipo": "between", "min": 0, "max": 999999},
            {"campo": "cantidad", "tipo": "type_check", "expected": "numeric"},
        ],
    },
    # Variante E: 1 proveedor (Email Ingestion)
    "E": {
        "columnas_requeridas": [
            "producto", "precio"
        ],
        "columnas_opcionales": ["stock", "codigo"],
        "reglas": [
            {"campo": "producto", "tipo": "not_null"},
            {"campo": "precio", "tipo": "between", "min": 0, "max": 999999},
        ],
    },
}

# Mapeo proveedor → variante
PROVEEDOR_VARIANTE = {
    "Andicar": "A", "Biogenetica": "A", "Cobeca13": "A", "Cristmed": "A",
    "Dropharma": "A", "Emmanuelle": "A", "Gama": "A", "Intercontinental": "A",
    "Mastranto": "A", "MastrantoB": "A", "MastrantoC": "A", "OPTIMA": "A",
    "BLV": "A",
    "DROCERCA": "B", "ITS": "B", "NENA": "B",
    "InsuamincaM": "C", "InsuamincaB": "C", "InsuamincaG": "C",
    "Zakipharma": "D", "VitalClinic": "D",
    "Email": "E",
}


def validate_provider_file(
    proveedor: str,
    df: pd.DataFrame,
    *,
    variante: Optional[str] = None,
    strict: bool = False,
) -> dict:
    """
    Valida un DataFrame de proveedor contra las reglas de su variante.
    
    Returns:
        {
            "valido": bool,
            "proveedor": str,
            "variante": str,
            "filas_total": int,
            "errores": [ { "regla": ..., "campo": ..., "detalle": ... }, ... ],
            "warnings": [ ... ],
            "estadisticas": { "nulls_por_campo": ..., "tipos_detectados": ... }
        }
    """
    if variante is None:
        variante = PROVEEDOR_VARIANTE.get(proveedor, "A")
    
    rules = VARIANT_RULES.get(variante, VARIANT_RULES["A"])
    errores = []
    warnings = []
    
    # ── Validación estructural: columnas requeridas ──
    cols_presentes = set(df.columns)
    cols_requeridas = set(rules["columnas_requeridas"])
    cols_faltantes = cols_requeridas - cols_presentes
    
    if cols_faltantes:
        errores.append({
            "regla": "columnas_requeridas",
            "campo": None,
            "detalle": f"Columnas faltantes: {sorted(cols_faltantes)}",
            "severidad": "CRITICO",
        })
        if strict:
            return _resultado(proveedor, variante, df, errores, warnings, valido=False)
    
    # ── Validación por regla ──
    for rule in rules["reglas"]:
        campo = rule["campo"]
        if campo not in df.columns:
            continue
        
        if rule["tipo"] == "not_null":
            n_nulls = df[campo].isna().sum()
            if n_nulls > 0:
                pct = n_nulls / len(df) * 100
                entry = {
                    "regla": "not_null",
                    "campo": campo,
                    "detalle": f"{n_nulls} valores NULL ({pct:.1f}%)",
                }
                if pct > 50:
                    entry["severidad"] = "CRITICO"
                    errores.append(entry)
                else:
                    entry["severidad"] = "WARNING"
                    warnings.append(entry)
        
        elif rule["tipo"] == "between":
            try:
                numeric_col = pd.to_numeric(df[campo], errors="coerce")
                below = (numeric_col < rule["min"]).sum()
                above = (numeric_col > rule["max"]).sum()
                non_numeric = numeric_col.isna().sum() - df[campo].isna().sum()
                
                if non_numeric > 0:
                    errores.append({
                        "regla": "between",
                        "campo": campo,
                        "detalle": f"{non_numeric} valores no numéricos",
                        "severidad": "CRITICO",
                    })
                if below > 0:
                    warnings.append({
                        "regla": "between",
                        "campo": campo,
                        "detalle": f"{below} valores bajo el mínimo ({rule['min']})",
                        "severidad": "WARNING",
                    })
                if above > 0:
                    warnings.append({
                        "regla": "between",
                        "campo": campo,
                        "detalle": f"{above} valores sobre el máximo ({rule['max']})",
                        "severidad": "WARNING",
                    })
            except Exception as e:
                errores.append({
                    "regla": "between",
                    "campo": campo,
                    "detalle": f"Error evaluando rango: {e}",
                    "severidad": "CRITICO",
                })
        
        elif rule["tipo"] == "length_between":
            lengths = df[campo].astype(str).str.len()
            too_short = (lengths < rule["min"]).sum()
            too_long = (lengths > rule["max"]).sum()
            if too_short > 0 or too_long > 0:
                warnings.append({
                    "regla": "length_between",
                    "campo": campo,
                    "detalle": (
                        f"{too_short} muy cortos (<{rule['min']}), "
                        f"{too_long} muy largos (>{rule['max']})"
                    ),
                    "severidad": "WARNING",
                })
        
        elif rule["tipo"] == "type_check":
            if rule["expected"] == "numeric":
                numeric_col = pd.to_numeric(df[campo], errors="coerce")
                n_bad = numeric_col.isna().sum() - df[campo].isna().sum()
                if n_bad > 0:
                    errores.append({
                        "regla": "type_check",
                        "campo": campo,
                        "detalle": f"{n_bad} valores no numéricos",
                        "severidad": "CRITICO",
                    })
    
    # ── Estadísticas ──
    valido = len([e for e in errores if e.get("severidad") == "CRITICO"]) == 0
    return _resultado(proveedor, variante, df, errores, warnings, valido=valido)


def _resultado(proveedor, variante, df, errores, warnings, valido):
    """Construye el resultado de validación."""
    nulls_por_campo = {col: int(df[col].isna().sum()) for col in df.columns}
    return {
        "valido": valido,
        "proveedor": proveedor,
        "variante": variante,
        "filas_total": len(df),
        "errores": errores,
        "warnings": warnings,
        "estadisticas": {
            "nulls_por_campo": nulls_por_campo,
            "columnas_detectadas": list(df.columns),
        },
        "timestamp": pd.Timestamp.now().isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# IMPUTACIÓN DE DATOS FALTANTES
# ══════════════════════════════════════════════════════════════

def impute_missing(
    df: pd.DataFrame,
    *,
    precio_col: str = "precio_unitario",
    stock_col: str = "stock_disponible",
    strategy: str = "knn",
) -> tuple[pd.DataFrame, dict]:
    """
    Imputa valores faltantes en un DataFrame de proveedor.
    
    Reglas de negocio:
      - stock NULL → 0 (pesimista: si no reportó, asumimos sin stock)
      - precio NULL → KNNImputer basado en productos similares
      - campos categóricos → NO se imputan (eso es trabajo de la IA)
    
    Returns:
        (df_imputado, reporte)
    """
    df = df.copy()
    reporte = {"imputaciones": [], "filas_afectadas": 0}
    
    # ── Stock NULL → 0 ──
    if stock_col in df.columns:
        n_stock_null = df[stock_col].isna().sum()
        if n_stock_null > 0:
            df[stock_col] = df[stock_col].fillna(0)
            reporte["imputaciones"].append({
                "campo": stock_col,
                "metodo": "regla_negocio_cero",
                "valores_imputados": int(n_stock_null),
                "razon": "NULL → 0: si el proveedor no reportó stock, asumimos sin stock",
            })
    
    # ── Precio NULL → KNN ──
    if precio_col in df.columns:
        n_precio_null = df[precio_col].isna().sum()
        if n_precio_null > 0 and n_precio_null < len(df) * 0.5:
            try:
                if strategy == "knn":
                    from sklearn.impute import KNNImputer
                    
                    # Usar columnas numéricas disponibles como features
                    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                    if precio_col in numeric_cols and len(numeric_cols) >= 2:
                        imputer = KNNImputer(n_neighbors=5, weights="distance")
                        df[numeric_cols] = imputer.fit_transform(df[numeric_cols])
                        
                        reporte["imputaciones"].append({
                            "campo": precio_col,
                            "metodo": "KNNImputer",
                            "valores_imputados": int(n_precio_null),
                            "features_usadas": numeric_cols,
                            "n_neighbors": 5,
                        })
                    else:
                        # Fallback: mediana si no hay suficientes features
                        mediana = df[precio_col].median()
                        df[precio_col] = df[precio_col].fillna(mediana)
                        reporte["imputaciones"].append({
                            "campo": precio_col,
                            "metodo": "mediana_fallback",
                            "valores_imputados": int(n_precio_null),
                            "mediana_usada": float(mediana),
                        })
                else:
                    mediana = df[precio_col].median()
                    df[precio_col] = df[precio_col].fillna(mediana)
                    reporte["imputaciones"].append({
                        "campo": precio_col,
                        "metodo": "mediana",
                        "valores_imputados": int(n_precio_null),
                    })
            except Exception as e:
                logger.error(f"Error en imputación de precio: {e}")
                reporte["imputaciones"].append({
                    "campo": precio_col,
                    "metodo": "error",
                    "detalle": str(e),
                })
        elif n_precio_null >= len(df) * 0.5:
            reporte["imputaciones"].append({
                "campo": precio_col,
                "metodo": "rechazado",
                "razon": f"Más del 50% de precios son NULL ({n_precio_null}/{len(df)}). No se imputa.",
            })
    
    reporte["filas_afectadas"] = sum(
        i.get("valores_imputados", 0) for i in reporte["imputaciones"]
    )
    
    return df, reporte
