"""
Synapse Analytics Engine — FastAPI Application
================================================
Microservicio de cálculos pesados para el ecosistema Pharmacy API.

Módulos:
  - /api/v1/optimize         — Optimización de pedidos (PuLP)
  - /api/v1/substitutes      — Motor de sustitución inteligente
  - /api/v1/anomalies        — Detección de anomalías de precio
  - /api/v1/validate         — Validación de calidad de datos ETL
  - /api/v1/scorecard        — Calificación de proveedores
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
from dotenv import load_dotenv

# Cargar variables de entorno globalmente al arrancar
load_dotenv("/home/synapse/source/Pedidos/.env", override=True)


# Configurar logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("AnalyticsEngine")

app = FastAPI(
    title="Synapse Analytics Engine",
    description="Microservicio de análisis avanzado para Farmacia Americana",
    version="2.0.0",
)


# ══════════════════════════════════════════════════════════════
# MODELOS PYDANTIC
# ══════════════════════════════════════════════════════════════

class OptimizationRequest(BaseModel):
    items: List[Dict[str, Any]]
    constraints: Dict[str, Any]

class SubstituteRequest(BaseModel):
    codbarras: str
    max_results: int = Field(default=20, le=100)
    incluir_mismo_proveedor: bool = True
    solo_con_stock: bool = True

class AnomalyRequest(BaseModel):
    proveedor: Optional[str] = None
    contamination: float = Field(default=0.05, ge=0.01, le=0.5)
    zscore_threshold: float = Field(default=3.0, ge=1.0, le=10.0)

class ValidateRequest(BaseModel):
    proveedor: str
    data: List[Dict[str, Any]]
    variante: Optional[str] = None
    strict: bool = False

class ScorecardRequest(BaseModel):
    weights: Optional[Dict[str, float]] = None


# ══════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "analytics_engine",
        "version": "2.0.0",
        "modules": [
            "optimizer", "substitution_engine",
            "anomaly_detector", "data_quality", "supplier_scorer",
        ],
    }


# ── Optimización (legacy — mantiene compatibilidad) ──
@app.post("/api/v1/optimize")
async def optimize_inventory(payload: OptimizationRequest):
    from .core.optimizer import run_optimization
    logger.info(f"Optimización legacy: {len(payload.items)} items")
    result = run_optimization({"items": payload.items, "constraints": payload.constraints})
    return result


# ── Optimización v3.1 (nuevo) ──
@app.post("/api/v2/optimize")
async def optimize_v2(payload: dict):
    """Motor de optimización v3.1 con 5 factores no lineales.

    Acepta OptimizationRequestV2 con:
    - criterios_agrupamiento: Dict[str, str]
    - dias_cobertura: int (default 21)
    - pesos: FactorWeights
    - amplifier, s4, monto_maximo, extension, sustitucion, opportunity_score
    """
    from .core.optimizer import run_optimization
    logger.info(f"Optimización v3.1: {payload.get('criterios_agrupamiento', {})}")
    try:
        result = run_optimization(payload)
        return result
    except Exception as e:
        logger.error(f"Error en optimización v3.1: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Motor de Sustitución ──
@app.post("/api/v1/substitutes")
async def find_substitutes(payload: SubstituteRequest):
    """Busca sustitutos para un producto por código de barras."""
    from .core.substitution_engine import find_substitutes as _find
    logger.info(f"Sustitución: codbarras={payload.codbarras}")
    try:
        result = _find(
            payload.codbarras,
            max_results=payload.max_results,
            incluir_mismo_proveedor=payload.incluir_mismo_proveedor,
            solo_con_stock=payload.solo_con_stock,
        )
        return result
    except Exception as e:
        logger.error(f"Error en sustitución: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/substitutes/{codbarras}")
async def find_substitutes_get(
    codbarras: str,
    max_results: int = 20,
    solo_con_stock: bool = True,
):
    """GET endpoint para sustitutos (conveniencia)."""
    from .core.substitution_engine import find_substitutes as _find
    try:
        return _find(
            codbarras,
            max_results=max_results,
            solo_con_stock=solo_con_stock,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Detección de Anomalías ──
@app.post("/api/v1/anomalies")
async def detect_anomalies(payload: AnomalyRequest):
    """Detecta precios anómalos en el mercado."""
    from .core.anomaly_detector import detect_anomalies as _detect
    logger.info(f"Anomalías: proveedor={payload.proveedor}")
    try:
        result = _detect(
            proveedor=payload.proveedor,
            contamination=payload.contamination,
            zscore_threshold=payload.zscore_threshold,
        )
        return result
    except Exception as e:
        logger.error(f"Error en detección de anomalías: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/anomalies")
async def detect_anomalies_get(proveedor: Optional[str] = None):
    """GET endpoint para anomalías (conveniencia)."""
    from .core.anomaly_detector import detect_anomalies as _detect
    try:
        return _detect(proveedor=proveedor)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Validación de Calidad de Datos ──
@app.post("/api/v1/validate")
async def validate_data(payload: ValidateRequest):
    """Valida un lote de datos de un proveedor."""
    import pandas as pd
    from .core.data_quality import validate_provider_file, impute_missing
    
    logger.info(f"Validación: proveedor={payload.proveedor}, filas={len(payload.data)}")
    try:
        df = pd.DataFrame(payload.data)
        
        # Paso 1: Validar
        validation = validate_provider_file(
            payload.proveedor, df,
            variante=payload.variante,
            strict=payload.strict,
        )
        
        # Paso 2: Si es válido, imputar
        imputation_report = None
        if validation["valido"]:
            _, imputation_report = impute_missing(df)
        
        return {
            "validation": validation,
            "imputation": imputation_report,
        }
    except Exception as e:
        logger.error(f"Error en validación: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Scorecard de Proveedores ──
@app.post("/api/v1/scorecard")
async def compute_scorecard(payload: ScorecardRequest):
    """Calcula el scorecard de todos los proveedores."""
    from .core.supplier_scorer import score_suppliers
    logger.info("Calculando scorecard de proveedores")
    try:
        result = score_suppliers(weights=payload.weights)
        return result
    except Exception as e:
        logger.error(f"Error en scorecard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/scorecard")
async def get_scorecard():
    """GET endpoint para scorecard."""
    from .core.supplier_scorer import score_suppliers
    try:
        return score_suppliers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
