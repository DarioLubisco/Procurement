# Intent: Optimizador de Distribución de Compras v2.0

> Confirmado por el usuario el 2026-06-18.  
> Actualizado con comentarios detallados del 2026-06-18.
>
> **Nota 2026-07-10:** Superado en parte por la propuesta unificada y enmiendas
> (`propuesta_parametrizacion_unificada*.md`). El motor real es heurístico v3.2
> (sin PuLP). Ver `CONTEXT.md` y `docs/adr/0001-convergencia-motor-pedido.md`.

## Outcome

Un motor de optimización de compras que reciba criterios de agrupamiento dinámicos + días de cobertura + pesos de **5 factores**, y devuelva una **distribución de compra justificada** entre productos equivalentes y proveedores, explicando visualmente por qué se sugirió cada línea.

## User

El comprador de la farmacia, quien opera desde el frontend y necesita entender la lógica para dar feedback y ajustar los pesos.

## Why Now

La farmacia compra "a ojo" o por hábito. Hay dinero perdido en:
1. Comprar más caro sin comparar proveedores.
2. Perder ventas por stockout (costo de oportunidad no calculado).
3. No aprovechar oportunidades de precio históricamente bajo.
4. Comprar demasiado de productos caros e inelásticos.

## Success

El comprador abre el sistema, selecciona un agrupamiento, pone N días de cobertura, ajusta los 5 pesos, y recibe una tabla con justificación clara que puede cuestionar y refinar.

## Constraint

- Pesos de los 5 factores aún no están definidos con valores por defecto.
- Parámetros de funciones exponencial y cuadrática por definir.
- Primero se crea el marco conceptual, después la fórmula, después el código.
- Arquitectura extensible a más criterios y factores.

## Out of Scope (por ahora)

- Scraper de catálogo de productos nuevos (tarea separada al backlog)
- Desviación estándar temporal (sigma corto/largo plazo) — requiere acumular snapshots
- Frontend React (se hace después del motor)

---

## Cambios Clave del v2.0 vs v1.0

| Concepto | v1.0 | v2.0 (corregido) |
|---|---|---|
| Gap negativo | Se truncaba a 0 | Se suma al total del grupo (reduce pedido) |
| Min/Max | SAPROD.Minimo/Maximo del ERP | Dinámico: rotación × días (Max) y ~70% del Max (Min) |
| Precio de referencia | Histórico por proveedor | Media de la mediana de TODOS los proveedores (único por SKU) |
| Función de oportunidad | Lineal | Exponencial no lineal (parametrizable) |
| Techo de sustitución | Fijo (elasticidad/5) | Móvil: cuadrático cuando la oportunidad es muy alta |
| Factores | 4 | 5 (nuevo: F5 extensión de cobertura) |
| S4 | No existía | Reducción de cobertura para SKUs inelásticos costosos |
| RotacionGrupal | "Futuro" | Ya disponible (R1 + R2) |
| "Caro" y "Barato" | No definido | Matemático: basado en σ del precio histórico |
