"""
Synapse Analytics Engine — Funciones No Lineales v3.1
=====================================================
Funciones matemáticas puras para el motor de optimización de compras.
Sin dependencias de BD — operan sobre valores numéricos puros.

Calibración por defecto del amplificador:
    -10% desvío → 1.5× compra
    -20% desvío → 2.0× compra
    -40% desvío → 6.0× compra
"""
import math
import logging
from typing import Tuple

logger = logging.getLogger("AnalyticsEngine.NonLinear")


# ══════════════════════════════════════════════════════════════
# F4 — AMPLIFICADOR EXPONENCIAL DE OPORTUNIDAD
# ══════════════════════════════════════════════════════════════

def exponential_amplifier(
    desvio: float,
    a: float = 5.84,
    b: float = 1.29,
    max_increment_pct: float = 500.0,
    floor_pct: float = 0.2,
) -> float:
    """Amplificador no lineal de cantidad basado en desvío de precio.

    Usa f(d) = e^(a × |d|^b) para desvío negativo (barato).
    La aceleración es CRECIENTE: cada 10% adicional de descuento
    incrementa mucho más que el anterior.

    Args:
        desvio: Desvío de precio como fracción (ej. -0.10 = 10% bajo la media).
                Negativo = barato, positivo = caro.
        a: Amplitud de la curva (default 4.3).
        b: Aceleración (default 1.6, >1 = aceleración creciente).
        max_increment_pct: Tope de incremento antes de MontoMaximo (default 500%).
        floor_pct: Piso mínimo para productos caros (default 0.2 = 20% del gap).

    Returns:
        Multiplicador de cantidad: 1.0 = sin cambio, 1.5 = +50%, 0.5 = -50%.
    """
    if desvio == 0:
        return 1.0

    abs_d = abs(desvio)

    if desvio < 0:
        # Barato → amplificar compra
        raw = math.exp(a * (abs_d ** b))
        # Acotar por max_increment
        max_multiplier = 1 + max_increment_pct / 100.0
        return min(raw, max_multiplier)
    else:
        # Caro → reducir compra
        raw = math.exp(-a * (abs_d ** b))
        return max(raw, floor_pct)


def calibrate_amplifier_params(
    points: list,
    tolerance: float = 0.05,
) -> Tuple[float, float]:
    """Encuentra los parámetros (a, b) que mejor ajustan los puntos de calibración.

    Usa scipy.optimize para encontrar (a, b) tal que e^(a × |d|^b) ≈ target
    para cada (desvio, target) en los puntos dados.

    Args:
        points: Lista de (desvio, target_multiplier).
                Ej: [(-0.10, 1.5), (-0.20, 2.0), (-0.40, 6.0)]

    Returns:
        (a, b) calibrados.
    """
    from scipy.optimize import minimize

    def objective(params):
        a, b = params
        error = 0
        for d, target in points:
            predicted = math.exp(a * (abs(d) ** b))
            error += (predicted - target) ** 2
        return error

    result = minimize(objective, x0=[4.0, 1.5], bounds=[(0.1, 50), (0.5, 5)])
    return round(result.x[0], 2), round(result.x[1], 2)


# ══════════════════════════════════════════════════════════════
# F4 — SCORE CONTINUO DE OPORTUNIDAD
# ══════════════════════════════════════════════════════════════

def continuous_opportunity_score(
    desvio: float,
    sigma: float,
    lambda_sensitivity: float = 1.0,
) -> float:
    """Score continuo de oportunidad entre -1.0 (caro) y +1.0 (oportunidad).

    NO usa bandas categóricas σ — cada punto del desvío tiene un score
    único. Un producto a -0.9σ se trata diferente que uno a -0.5σ.

    Args:
        desvio: Desvío de precio (fracción).
        sigma: Desviación estándar del precio del SKU.
        lambda_sensitivity: Sensibilidad de la curva (default 1.0).

    Returns:
        Score entre -1.0 (muy caro) y +1.0 (oportunidad excepcional).
        0.0 = precio justo.
    """
    if sigma <= 0:
        return 0.0

    normalized = desvio / sigma

    if desvio < 0:
        # Barato → score positivo (oportunidad)
        return 1 - math.exp(lambda_sensitivity * normalized)
    elif desvio > 0:
        # Caro → score negativo
        return -(1 - math.exp(-lambda_sensitivity * normalized))
    else:
        return 0.0


# ══════════════════════════════════════════════════════════════
# F1/F4 — TECHO MÓVIL DE SUSTITUCIÓN
# ══════════════════════════════════════════════════════════════

def quadratic_ceiling(
    max_sustitucion_base: float,
    desvio_sucedaneo: float,
    kappa: float = 5.0,
    amplificador_sucedaneo: float = 1.0,
) -> float:
    """Techo móvil de sustitución: se expande cuando la oportunidad es alta.

    El techo base (dado por elasticidad) se multiplica cuadráticamente
    cuando el sucedáneo está significativamente más barato.

    Args:
        max_sustitucion_base: Fracción máxima sustituible base (ej. 0.40 para elast=2).
        desvio_sucedaneo: Desvío de precio del sucedáneo (negativo = barato).
        kappa: Parámetro de expansión cuadrática (default 5.0).
        amplificador_sucedaneo: Amplificador ya calculado para el sucedáneo.

    Returns:
        Techo de sustitución ajustado (0.0 a 1.0).
    """
    if max_sustitucion_base <= 0:
        return 0.0

    # Expansión cuadrática por oportunidad de precio
    expansion = max_sustitucion_base * (1 + kappa * desvio_sucedaneo ** 2) * amplificador_sucedaneo

    # Nunca más del 100% del gap del principal
    return min(expansion, 1.0)


# ══════════════════════════════════════════════════════════════
# F5 — EXTENSIÓN DE COBERTURA POR OPORTUNIDAD
# ══════════════════════════════════════════════════════════════

def coverage_extension(
    desvio: float,
    max_dias_extra: int = 21,
    eta: float = 4.0,
    umbral: float = -0.10,
) -> int:
    """Días extra de cobertura por oportunidad de precio.

    También es NO LINEAL — mientras más barato, MUCHO más se extiende.

    Args:
        desvio: Desvío de precio (fracción, negativo = barato).
        max_dias_extra: Máximo de días adicionales (default 21).
        eta: Agresividad de la extensión (default 4.0).
        umbral: Desvío mínimo para activar extensión (default -0.10 = -10%).

    Returns:
        Días extra de cobertura (0 a max_dias_extra).
    """
    if desvio > umbral:
        # No suficiente descuento → no extender
        return 0

    # Función no lineal: 1 - e^(eta × desvio)
    # desvio es negativo, así que eta × desvio es negativo → e^(...) < 1
    fraction = 1 - math.exp(eta * desvio)
    dias = int(max_dias_extra * fraction)

    return max(0, min(dias, max_dias_extra))


# ══════════════════════════════════════════════════════════════
# S4 — FACTOR DE REDUCCIÓN NO LINEAL
# ══════════════════════════════════════════════════════════════

def s4_reduction_factor(
    desvio: float,
    porcentaje_base: float = 0.66,
    amplifier_params: tuple = (5.84, 1.29),
) -> float:
    """Factor de reducción S4 para SKUs costosos con elasticidad=0.

    La reducción es NO LINEAL — modulada por el desvío de precio.
    Si el SKU costoso está barato → reducir MENOS la cobertura (comprar más).
    Si está al precio normal o caro → aplicar reducción completa.

    Args:
        desvio: Desvío de precio del SKU costoso.
        porcentaje_base: Reducción base de cobertura (default 0.66 = 66%).
        amplifier_params: Tuple (a, b) del amplificador.

    Returns:
        Factor multiplicativo para dias_cobertura.
        Valores típicos: 0.66 (caro) a 1.32+ (barato, comprar más).
    """
    a, b = amplifier_params
    amplifier = exponential_amplifier(desvio, a=a, b=b)
    return porcentaje_base * amplifier


# ══════════════════════════════════════════════════════════════
# UTILIDAD: Cálculo de Desvío de Precio
# ══════════════════════════════════════════════════════════════

def calculate_price_deviation(
    precio_actual: float,
    media_de_mediana: float,
) -> float:
    """Calcula el desvío de precio respecto a la media de la mediana.

    Args:
        precio_actual: Precio del proveedor actual.
        media_de_mediana: Media temporal de las medianas diarias del SKU.

    Returns:
        Desvío como fracción: negativo = barato, positivo = caro.
        Ej: -0.10 = 10% más barato.
    """
    if media_de_mediana <= 0:
        return 0.0
    return (precio_actual - media_de_mediana) / media_de_mediana


# ══════════════════════════════════════════════════════════════
# UTILIDAD: Monto Estimado y MontoMaximo
# ══════════════════════════════════════════════════════════════

def estimate_order_amount(
    rotaciones_diarias: list,
    precios_medianos: list,
    dias: int,
) -> float:
    """Calcula el MontoEstimado para N días de pedido.

    MontoEstimado = Σ(rotacion_diaria × dias × precio_mediana)

    Args:
        rotaciones_diarias: Lista de rotaciones diarias por SKU.
        precios_medianos: Lista de precios medianos por SKU (misma longitud).
        dias: Días de cobertura del pedido.

    Returns:
        Monto estimado en USD.
    """
    if len(rotaciones_diarias) != len(precios_medianos):
        raise ValueError("rotaciones_diarias y precios_medianos deben tener la misma longitud")

    total = sum(
        rot * dias * precio
        for rot, precio in zip(rotaciones_diarias, precios_medianos)
        if rot > 0 and precio > 0
    )
    return round(total, 2)


def calculate_monto_maximo(
    monto_estimado: float,
    buffer_pct: float = 20.0,
    override: float = None,
) -> float:
    """Calcula el MontoMaximo (gobernador global).

    Args:
        monto_estimado: Monto estimado base en USD.
        buffer_pct: Buffer porcentual (default 20%).
        override: Valor manual opcional que anula el cálculo.

    Returns:
        MontoMaximo en USD.
    """
    if override is not None and override > 0:
        return override
    return round(monto_estimado * (1 + buffer_pct / 100.0), 2)


# ══════════════════════════════════════════════════════════════
# UTILIDAD: Probabilidad de Stockout (Poisson)
# ══════════════════════════════════════════════════════════════

def stockout_probability(
    rotacion_diaria: float,
    lead_time_dias: float,
    stock_actual: int,
) -> float:
    """Calcula la probabilidad de stockout durante el lead time usando Poisson.

    P(stockout) = 1 - Σ[k=0..stock] (λ^k × e^-λ / k!)
    donde λ = rotación_diaria × lead_time

    Args:
        rotacion_diaria: Unidades vendidas por día.
        lead_time_dias: Días de despacho del proveedor.
        stock_actual: Unidades en inventario.

    Returns:
        Probabilidad de stockout entre 0.0 (imposible) y 1.0 (seguro).
    """
    lambda_lt = rotacion_diaria * lead_time_dias

    if lambda_lt <= 0:
        return 0.0
    if stock_actual <= 0:
        return 1.0

    # CDF de Poisson: P(X ≤ stock) = Σ[k=0..stock] (λ^k × e^-λ / k!)
    cumulative = 0.0
    for k in range(stock_actual + 1):
        log_prob = k * math.log(lambda_lt) - lambda_lt - math.lgamma(k + 1)
        cumulative += math.exp(log_prob)

    prob_stockout = 1.0 - cumulative
    return max(0.0, min(prob_stockout, 1.0))


def stockout_cost(
    prob_stockout: float,
    rotacion_diaria: float,
    lead_time_dias: float,
    margen_unitario: float,
) -> float:
    """Costo de oportunidad por stockout durante el lead time.

    Args:
        prob_stockout: Probabilidad de stockout (0-1).
        rotacion_diaria: Unidades/día.
        lead_time_dias: Días de despacho.
        margen_unitario: Ganancia por unidad (precio_venta - precio_compra).

    Returns:
        Costo de oportunidad en USD.
    """
    return prob_stockout * rotacion_diaria * lead_time_dias * margen_unitario
