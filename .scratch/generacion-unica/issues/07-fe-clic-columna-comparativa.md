Status: resolved

# 07-fe-clic-columna-comparativa

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

Clicking a perfil column hydrates the single ComparativaCantidades (and related summary) from that slot only.

## Acceptance criteria

- [x] Column click sets the active perfil in session
- [x] Comparativa table/body renders that perfil’s GenerarResult
- [x] Switching columns swaps Comparativa without re-running the batch
- [x] Baseline columns remain the shared PedidoBaseline

## Blocked by

- 06-fe-grilla-batch-delta

## Answer

`hydrateComparativaFromBatchSlot(perfilId)` sets `activeBatchPerfilId`, marks `.is-active`, and `stashGenerarResult` with slot.result + shared `pedido_baseline` from the batch. Column click/Enter/Space; no second `generar-batch` call.

## Comments
