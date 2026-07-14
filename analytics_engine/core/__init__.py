# Analytics Engine Core
from .optimizer import run_optimization
from .nonlinear import (
    exponential_amplifier,
    continuous_opportunity_score,
    quadratic_ceiling,
    coverage_extension,
    s4_reduction_factor,
    calculate_price_deviation,
    estimate_order_amount,
    calculate_monto_maximo,
    stockout_probability,
    stockout_cost,
)
