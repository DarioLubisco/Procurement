"""
Synapse Analytics Engine — Modelos Pydantic para Optimización v3.1
=================================================================
Define las estructuras de request/response para el motor de optimización
de compras. Todos los parámetros son configurables desde el frontend.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum
import uuid


# ══════════════════════════════════════════════════════════════
# PARÁMETROS CONFIGURABLES
# ══════════════════════════════════════════════════════════════

class AmplifierParams(BaseModel):
    """Parámetros de la función exponencial de amplificación.

    Calibración por defecto (scipy.optimize):
        -10% desvío -> 1.5x compra
        -20% desvío -> 2.0x compra
        -40% desvío -> 6.0x compra
    """
    a: float = Field(default=5.84, ge=0.1, le=20.0,
                     description="Amplitud de la curva exponencial")
    b: float = Field(default=1.29, ge=0.5, le=5.0,
                     description="Aceleración de la curva (b>1 = aceleración creciente)")
    max_increment_pct: float = Field(default=500.0, ge=50.0, le=2000.0,
                                     description="Tope de incremento en pct antes de MontoMaximo")
    floor_pct: float = Field(default=0.2, ge=0.0, le=1.0,
                             description="Piso mínimo para productos caros (20 pct del gap)")


class S4Params(BaseModel):
    """Parámetros para la reducción S4 de SKUs costosos con elasticidad=0."""
    enabled: bool = Field(default=False,
                          description="Checkbox activable en el frontend")
    porcentaje_base: float = Field(default=0.66, ge=0.1, le=1.0,
                                   description="Reducción base de cobertura (ej. 66 pct)")


class MontoMaximoParams(BaseModel):
    """Parámetros del gobernador global de monto máximo."""
    buffer_pct: float = Field(default=20.0, ge=0.0, le=100.0,
                              description="Buffer pct sobre el MontoEstimado")
    days_reduction_pct: float = Field(default=20.0, ge=5.0, le=50.0,
                                      description="Pct de reducción de días si total > MontoMaximo")
    monto_maximo_override: Optional[float] = Field(default=None, ge=0,
                                                    description="Override manual del MontoMaximo en USD")


class CoverageExtensionParams(BaseModel):
    """Parámetros para F5 — extensión de cobertura por oportunidad."""
    max_dias_extra: int = Field(default=21, ge=0, le=60,
                                description="Máximo de días adicionales de cobertura")
    umbral_extension: float = Field(default=-0.10, le=0.0,
                                    description="Desvío mínimo para activar extensión (ej. -10 pct)")
    eta: float = Field(default=4.0, ge=1.0, le=15.0,
                       description="Agresividad de la extensión no lineal")


class SubstitutionParams(BaseModel):
    """Parámetros para el techo móvil de sustitución."""
    kappa: float = Field(default=5.0, ge=1.0, le=20.0,
                         description="Expansión cuadrática del techo de sustitución")


class OpportunityScoreParams(BaseModel):
    """Parámetros para la función continua de oportunidad."""
    lambda_sensitivity: float = Field(default=1.0, ge=0.1, le=5.0,
                                      description="Sensibilidad de la curva de oportunidad")


# ══════════════════════════════════════════════════════════════
# PESOS DE LOS FACTORES
# ══════════════════════════════════════════════════════════════

class FactorWeights(BaseModel):
    """Pesos de los 5 factores de distribución.

    Deben sumar 1.0 (se normaliza automáticamente si no).
    """
    w1_elasticidad: float = Field(default=0.15, ge=0.0, le=1.0,
                                   description="Peso F1 — Elasticidad/Sustitución")
    w2_demanda: float = Field(default=0.25, ge=0.0, le=1.0,
                               description="Peso F2 — Demanda (velocidad de rotación)")
    w3_posicionamiento: float = Field(default=0.25, ge=0.0, le=1.0,
                                       description="Peso F3 — Posicionamiento (urgencia de stock)")
    w4_oportunidad: float = Field(default=0.20, ge=0.0, le=1.0,
                                   description="Peso F4 — Oportunidad histórica de precio")
    w5_extension: float = Field(default=0.15, ge=0.0, le=1.0,
                                 description="Peso F5 — Extensión de cobertura")

    def normalized(self) -> Dict[str, float]:
        """Devuelve los pesos normalizados a suma=1."""
        total = (self.w1_elasticidad + self.w2_demanda +
                 self.w3_posicionamiento + self.w4_oportunidad +
                 self.w5_extension)
        if total == 0:
            return {k: 0.2 for k in ["w1", "w2", "w3", "w4", "w5"]}
        return {
            "w1": self.w1_elasticidad / total,
            "w2": self.w2_demanda / total,
            "w3": self.w3_posicionamiento / total,
            "w4": self.w4_oportunidad / total,
            "w5": self.w5_extension / total,
        }


# ══════════════════════════════════════════════════════════════
# REQUEST
# ══════════════════════════════════════════════════════════════

class OptimizationRequestV2(BaseModel):
    """Solicitud de optimización de compras v3.1.

    El comprador envía:
    - Criterios de agrupamiento dinámico
    - Días de cobertura deseados
    - Pesos para los 5 factores
    - Parámetros de configuración (todos con defaults sensatos)
    """
    # --- Entrada del comprador ---
    criterios_agrupamiento: Dict[str, str] = Field(
        ...,
        description="Criterios dinámicos {atributo: valor}. Ej: {'principio_activo': 'Acetaminofen'}",
    )
    dias_cobertura: int = Field(
        default=21, ge=1, le=90,
        description="Días de cobertura para el pedido",
    )

    # --- Pesos ---
    pesos: FactorWeights = Field(default_factory=FactorWeights)

    # --- Parámetros configurables ---
    amplifier: AmplifierParams = Field(default_factory=AmplifierParams)
    s4: S4Params = Field(default_factory=S4Params)
    monto_maximo: MontoMaximoParams = Field(default_factory=MontoMaximoParams)
    extension: CoverageExtensionParams = Field(default_factory=CoverageExtensionParams)
    sustitucion: SubstitutionParams = Field(default_factory=SubstitutionParams)
    opportunity_score: OpportunityScoreParams = Field(default_factory=OpportunityScoreParams)


# ══════════════════════════════════════════════════════════════
# RESPONSE — LÍNEA DE PEDIDO
# ══════════════════════════════════════════════════════════════

class OrderLine(BaseModel):
    """Una línea del pedido optimizado."""
    codbarras: str
    descripcion: str
    codprod: Optional[str] = None
    proveedor: str
    cantidad: int = Field(ge=0)
    precio_unitario: float
    costo_total: float

    # --- Referencias de precio ---
    media_min_historico_sku: Optional[float] = None
    min_absoluto_sku: Optional[float] = None
    media_de_mediana_sku: Optional[float] = None
    precio_mediana_actual_sku: Optional[float] = None

    # --- Métricas del motor ---
    gap_base: float
    desvio_precio_pct: float
    score_oportunidad: float
    amplificador_aplicado: float
    dias_extra_aplicados: int = 0
    es_sustitucion: bool = False
    sku_principal_sustituido: Optional[str] = None

    # --- Factores desglosados ---
    factores_detalle: Dict[str, float] = Field(
        default_factory=dict,
        description="F1 a F5 desglosados",
    )

    # --- Justificación textual ---
    justificacion: str


# ══════════════════════════════════════════════════════════════
# RESPONSE — RESULTADO COMPLETO
# ══════════════════════════════════════════════════════════════

class OptimizationResult(BaseModel):
    """Resultado completo de la optimización."""
    pedido_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    grupo: str
    dias_cobertura: int

    # --- Montos (en Bolívares) ---
    monto_estimado_bs: float
    monto_maximo_bs: float
    buffer_pct: float
    monto_total_pedido_bs: float
    monto_sobrestock_oportunidad_bs: float = 0.0
    ahorro_vs_media_min_historico_pct: float = 0.0
    justificacion_sobrestock: Optional[str] = None

    # --- Sugerencia automática si excede MontoMaximo ---
    excede_monto_maximo: bool = False
    dias_sugeridos_reduccion: Optional[int] = None
    redistribucion_sugerida: Optional[str] = None

    # --- Pesos usados ---
    pesos: Dict[str, float]

    # --- Líneas del pedido ---
    lineas: List[OrderLine]

    # --- Métricas agregadas ---
    total_skus_procesados: int = 0
    total_proveedores_involucrados: int = 0
    r2_dinamica_grupo: float = 0.0
    pedido_total_grupo_unidades: float = 0.0
