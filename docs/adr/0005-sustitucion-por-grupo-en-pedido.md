# Sustitución dentro del Pedido por Grupo (reabre ADR-0003)

El comprador depreca `forced_includes`. Los FiltrosOperativos definen el **muestreo** evaluado por rotación (Baseline). El PedidoPropuesto puede resolver la misma Necesidad de **Grupo** con otras BARRAs del mercado vivo (sucedáneos que comparten criterios de agrupación). La ComparativaCantidades empareja por **Grupo**, no solo por BARRA.

**Status:** accepted — supersedes the “aislada del Pedido” part of ADR-0003 for product replacement inside Propuesto/Definitivo.

## Considered Options

- Sustitución solo como API adyacente, nunca en el Pedido (ADR-0003 original) — schema limpio, pero contradice el flujo Comparativa con reemplazos.
- Reemplazo dentro del PedidoPropuesto por ofertas del mismo Grupo (elegida) — alinea mercado vivo con la comparación Baseline vs Propuesto.
- Mantener forced_includes para “traer el SKU original” — deprecado; el motor elige sucedáneo del Grupo.

## Consequences

- `kappa` / `quadratic_ceiling` siguen muertos hasta calibración explícita; “puede reemplazar” no implica reactivar ese knob.
- Paridad P1: Baseline vs Motor B sobre el muestreo filtrado; Propuesto no se exige 1:1 en BARRA.
- JustificacionDelta debe declarar cambio de código cuando el Propuesto no usa la BARRA del Baseline.
- El módulo `substitution_engine` puede alimentar el Propuesto o quedar como implementación detrás del mismo concepto Grupo; ya no se trata como dominio ajeno al Pedido.
