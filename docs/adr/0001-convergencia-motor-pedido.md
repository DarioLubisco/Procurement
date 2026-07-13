# Convergencia en un solo motor de pedido

Hoy coexisten el generador clásico (`backend/routers/pedidos.py`, UI productiva) y el Optimizer v3.2 (`analytics_engine`, API sin FE). Decidimos **convergir en v3.2** con un perfil `Lineal` que degenera la matemática hacia `rotación × días / 30 − stock`, y un **proxy** de `/api/pedidos/generate` que preserva el contrato operativo del Motor B (filtros, restas, export).

**Status:** accepted

## Considered Options

- **Dos adapters detrás de un seam** (legacy + market-driven): más seguro a corto plazo; retrasa la poda del dual-stack.
- **Convergencia en v3.2 + perfil Lineal** (elegida): un solo pipeline; exige demostrar paridad numérica y operativa con `compare_orders.py` antes de retirar el legado.
- **Reescribir desde cero con PuLP/MOQ:** contradice el código actual; los intent docs que lo prometen están desactualizados.

## Consequences

- La equivalencia Lineal↔clásico **no se declara**: se demuestra (cantidades + filtros + Excel).
- `RotacionGrupal` pasa a ser la única fuente de DemandaGrupal; se elimina el recálculo inline del optimizer.
- Detalle: `docs/intent/propuesta_parametrizacion_unificada_enmiendas_2026-07-10.md` §3.1 y §5.
