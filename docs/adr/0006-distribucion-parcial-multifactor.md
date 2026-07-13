# DistribucionParcial multi-factor (no solo elasticidad)

Dentro de un Grupo, el PedidoPropuesto reparte cantidades de forma **parcial por línea**. La decisión usa el **motor completo** (Elasticidad, PriceOpportunity, pesos, presupuesto, lead time/días de despacho, stock de oferta, y demás parámetros activos). Ningún factor se declara “fuera” del delta. Ejemplo de negocio: mayor elasticidad no prevalece si el proveedor despacha demasiado tarde.

**Status:** accepted

## Considered Options

- Winner-takes-all por Grupo — rechazado (elasticidad típica menor que 5).
- Solo elasticidad reparte qty — rechazado (incompleto).
- Motor completo decide cuota y reemplazo por línea (elegida); rotación/Gap siguen anclando la Necesidad Baseline.

## Consequences

- JustificacionDelta es multi-causal.
- LeadTime: además de factor soft de score, **SplitLeadTime** (ADR-0014) — mínimo al rápido, resto al barato.
- El código actual que solo anota lead time debe cambiar para score **y** split de cantidades.
- Paridad Baseline sigue midiendo el muestreo legacy; Propuesto no se exige 1:1 en BARRA ni en qty.
