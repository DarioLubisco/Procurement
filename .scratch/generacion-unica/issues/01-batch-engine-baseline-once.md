Status: resolved

# 01-batch-engine-baseline-once

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

From the engine seam, one shared PedidoBaseline plus up to three perfil GenerarResults (same ComparativaCantidades + PedidoPropuesto shape as today), with fixture proof that Baseline BARRAs/qty are identical across perfiles.

## Acceptance criteria

- [x] `generar_pedido_batch` (or equivalent) accepts shared filtros + ≤3 perfil descriptors
- [x] PedidoBaseline is computed once and reused; no per-perfil re-sample
- [x] Each perfil returns a GenerarResult compatible with current Comparativa/Propuesto consumers
- [x] Fixtures assert shared Baseline anchors and distinct Propuesto totals across perfiles

## Blocked by

None — can start immediately.

## Answer

Implemented `FiltrosCompartidos`, `PerfilDescriptor`, `generar_pedido_batch` in `analytics_engine/core/generar_pedido.py`. Baseline via `_compute_shared_baseline` once; each slot reuses the same `pedido_baseline` list. Tests: `tests/analytics/test_generar_pedido_batch.py`.

## Comments
