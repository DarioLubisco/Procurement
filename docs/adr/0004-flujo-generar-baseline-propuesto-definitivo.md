# Flujo Generar: ComparativaCantidades → Definitivo

El botón productivo «Generar» entrega una **ComparativaCantidades** (primer pase) y permite regenerar el **PedidoDefinitivo** tras reafinación. El Excel mínimo `BARRA`×`CANTIDAD` queda **deprecado** como salida humana de esta fase. `forced_includes` queda **deprecado**.

**Status:** accepted

## ComparativaCantidades

**Grano:** una fila por BARRA del Baseline.

| Columna | Significado |
|---------|-------------|
| BARRA + descripción Baseline | Producto del muestreo/rotación |
| BARRA + descripción Propuesto | Misma u otra del Grupo (sucedáneo) |
| Cantidad Baseline | Rotación × cobertura − stock |
| Cantidad Propuesto | **Cuota parcial** de esa línea (Elasticidad + factores del motor), no el total del Grupo en una sola fila |
| JustificacionDelta | Incluye elasticidad, precio, reemplazo de código |

**No** winner-takes-all y **no** “solo elasticidad”: la cuota Propuesto por línea la decide el **motor completo** (elasticidad, precio/Desvío, pesos, presupuesto, lead time/despacho, stock de oferta, etc.). JustificacionDelta debe reflejar los factores que realmente movieron esa fila.

> **Nota código:** hoy F1 rankea con elasticidad y la qty usa `gap × amplificador × rot_share`; lead time solo anota, no asigna. Alinear el pipeline a DistribucionParcial multi-factor es trabajo de implementación explícito.

## Artefactos del primer Generar

1. **ComparativaCantidades** (delta Baseline vs Propuesto + JustificacionDelta)
2. **PedidoPropuesto** con **proveedor** (listo para revisar compra, no solo cantidades)

El Definitivo regenera ambos tras Intermedio/Avanzado.
