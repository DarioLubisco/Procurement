# Intent: Optimización de Compras Multi-Proveedor (Motor Analítico)

> **Estado 2026-07-10:** Intent histórico. **No describe el código actual.**
> No hay PuLP ni MOQ en `analytics_engine`; no existe “Matriz de Decisión” como módulo.
> Diseño vigente: [`propuesta_parametrizacion_unificada.md`](./propuesta_parametrizacion_unificada.md) (original) y
> [`propuesta_parametrizacion_unificada_enmiendas_2026-07-10.md`](./propuesta_parametrizacion_unificada_enmiendas_2026-07-10.md);
> decisiones en `docs/adr/` y vocabulario en `CONTEXT.md`.

## Outcome
Un motor matemático (usando `pulp` para las restricciones rígidas y heurísticas para los pesos dinámicos) que cruza 9+ catálogos y escupe la distribución de compra más rentable.

## User
El equipo de compras de Pedidos-Synapse.

## Why now
Cruzar 9 proveedores manualmente considerando montos mínimos, tiempos de entrega y costo de oportunidad es humanamente imposible sin incurrir en ineficiencias financieras.

## Success Criteria
El sistema calcula en tiempo real qué comprar y a quién, logrando los montos mínimos obligatorios de los proveedores, o re-distribuyendo inteligentemente las compras basándose en un análisis de costo-beneficio del sobreprecio asociado.

## Constraints
- La elasticidad de presupuesto (ej. ±3%).
- Los pesos heurísticos (Urgencia vs. Precio).
- Ambos deben estar expuestos y ser modificables desde el Dashboard de React en tiempo real.

## Technical Requirements
- Utilizar las credenciales disponibles en N8N para acceder al recurso SAS, en caso de ser necesario.

## Out of Scope
- Conexión automática (escritura) a las APIs de los proveedores para efectuar el pago y la compra final de forma autónoma.
- El sistema termina en la generación de la "Matriz de Decisión" sugerida para aprobación humana.
