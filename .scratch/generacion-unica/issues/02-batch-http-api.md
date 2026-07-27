Status: ready-for-agent

# 02-batch-http-api

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

An HTTP surface that exposes the batch contract so the productive FE can load Baseline + perfiles in one Generar action (single batch POST or orchestrated calls with injected/cached Baseline — choice documented in the issue comments).

## Acceptance criteria

- [ ] API returns `{ PedidoBaseline, perfiles: [{ id, label, knobs_efectivos, GenerarResult }] }` (shape may nest Baseline inside meta; FE can parse it)
- [ ] Callers cannot get three independent full Generars that re-sample Baseline
- [ ] Catalog/offers/backorder load is not tripled wastefully when using DB path
- [ ] Error handling fails the batch coherently (no silent half-grids)

## Blocked by

- 01-batch-engine-baseline-once

## Comments
