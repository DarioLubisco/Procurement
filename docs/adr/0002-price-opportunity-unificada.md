# Unificar oportunidad de precio en PriceOpportunity

F4 (`continuous_opportunity_score`), el amplificador exponencial y F5 (`coverage_extension`) — y de forma adyacente el anomaly detector — reaccionan al mismo **Desvío** con curvas distintas y knobs independientes. Decidimos colapsarlos en un módulo **PriceOpportunity(desvío, σ) → {score, qty_mult, dias_extra, is_anomaly?}** detrás de una interface pequeña.

**Status:** accepted

## Considered Options

- **Mantener knobs separados** (`amp_*`, `ext_*`, `opp_lambda`) en el schema y en UI Intermedio/Avanzado: más control fino, pero acoplamiento conceptual y calibración frágil.
- **Colapsar en PriceOpportunity** (elegida): locality de calibración; FE Sencillo/Intermedio habla de “intensidad / umbral / días extra”; Avanzado puede exponer parámetros internos de la curva unificada, no tres familias.

## Consequences

- El grupo UI “Oportunidad” deja de listar a, b, η, λ como conceptos de negocio de primer nivel.
- `anomaly_detector` puede reutilizar la misma señal o marcar `is_anomaly` sin un cuarto modelo de “precio raro”.
- Implementación puede ser gradual (P1 flags + P4 refactor interno) sin cambiar el contrato `PerfilPedido`.
