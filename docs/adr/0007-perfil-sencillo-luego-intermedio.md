# Perfil del primer Generar vs regeneración

El **PedidoBaseline** no usa el motor: es el pedido legacy por rotación (muestreo + Cobertura + FiltrosOperativos). El primer **PedidoPropuesto** usa solo nivel **Sencillo** (preset Conservador/Normal/Agresivo + Cobertura + FiltrosOperativos + presupuesto máximo opcional). Tras la ComparativaCantidades, el comprador puede regenerar con controles **Intermedio o Avanzado** hacia el **PedidoDefinitivo**.

**Status:** accepted

## Consequences

- Baseline nunca lleva PriceOpportunity, pesos F1–F5 ni LeadTime soft.
- UI: primer Generar = Sencillo (+ presupuesto opcional); Intermedio/Avanzado desbloqueados o enfatizados en el paso de reafinación.
- Paridad P1 del Baseline = Motor B clásico, no “perfil Lineal del v3.2”.
