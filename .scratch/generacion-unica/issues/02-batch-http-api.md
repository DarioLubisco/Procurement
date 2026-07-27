Status: resolved

# 02-batch-http-api

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

An HTTP surface that exposes the batch contract so the productive FE can load Baseline + perfiles in one Generar action (single batch POST or orchestrated calls with injected/cached Baseline — choice documented in the issue comments).

## Acceptance criteria

- [x] API returns `{ PedidoBaseline, perfiles: [{ id, label, knobs_efectivos, GenerarResult }] }` (shape may nest Baseline inside meta; FE can parse it)
- [x] Callers cannot get three independent full Generars that re-sample Baseline
- [x] Catalog/offers/backorder load is not tripled wastefully when using DB path
- [x] Error handling fails the batch coherently (no silent half-grids)

## Blocked by

- 01-batch-engine-baseline-once

## Answer

`POST /api/pedidos/generar-batch` → `run_generar_pedido_batch` → `generar_pedido_batch`. Response: top-level `pedido_baseline` + `perfiles[].{id,label,knobs_efectivos,result}` (serialized GenerarResult). Tests: `test_generar_pedido_batch_api.py`, `test_generar_batch_endpoint.py`.

## Comments

**Transport choice:** single `POST /api/pedidos/generar-batch` that loads catalog/offers/backorder **once** via `_load_catalog_offers_backorder`, then calls the engine batch seam. Rejected alternative: FE orchestrating 3× `/generar-sencillo` (would re-sample Baseline and triple DB load).
