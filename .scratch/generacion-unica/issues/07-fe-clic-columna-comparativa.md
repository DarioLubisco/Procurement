Status: ready-for-agent

# 07-fe-clic-columna-comparativa

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

Clicking a perfil column hydrates the single ComparativaCantidades (and related summary) from that slot only.

## Acceptance criteria

- [ ] Column click sets the active perfil in session
- [ ] Comparativa table/body renders that perfil’s GenerarResult
- [ ] Switching columns swaps Comparativa without re-running the batch
- [ ] Baseline columns remain the shared PedidoBaseline

## Blocked by

- 06-fe-grilla-batch-delta

## Comments
