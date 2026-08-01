Status: resolved

# 10-comparador-regen-activo

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

Vertical comparator card for the active perfil with Intermedio|Avanzado; regenerar updates only that slot and re-hydrates Comparativa; shared PedidoBaseline and sibling slots stay put.

## Acceptance criteria

- [x] Comparator card shows the active perfil summary
- [x] Dropdown Intermedio|Avanzado (and overrides as today) available on the card
- [x] Regenerar calls existing definitivo path against the active slot only
- [x] Sibling batch resultados unchanged after re-gen
- [x] PedidoBaseline in session unchanged after re-gen

## Blocked by

- 07-fe-clic-columna-comparativa

## Answer

`#comparadorActivoCard` wraps Intermedio|Avanzado + regenerar. `updateComparadorActivoCard` shows active label/`N (Δ)`. `applyRegenToActiveBatchSlot` replaces only `slot.result`, forces shared `lastBatchResult.pedido_baseline`, re-renders grid + hydrates Comparativa.

## Comments
