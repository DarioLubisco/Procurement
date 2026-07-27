Status: ready-for-agent

# 10-comparador-regen-activo

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

Vertical comparator card for the active perfil with Intermedio|Avanzado; regenerar updates only that slot and re-hydrates Comparativa; shared PedidoBaseline and sibling slots stay put.

## Acceptance criteria

- [ ] Comparator card shows the active perfil summary
- [ ] Dropdown Intermedio|Avanzado (and overrides as today) available on the card
- [ ] Regenerar calls existing definitivo path against the active slot only
- [ ] Sibling batch resultados unchanged after re-gen
- [ ] PedidoBaseline in session unchanged after re-gen

## Blocked by

- 07-fe-clic-columna-comparativa

## Comments
