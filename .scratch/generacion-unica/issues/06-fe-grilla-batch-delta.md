Status: ready-for-agent

# 06-fe-grilla-batch-delta

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

Primary Generar calls the batch API and shows a results grid of perfiles with totals formatted `N (Δ −86)` vs PedidoBaseline — no top proveedor, no Δ-knobs/variables card.

## Acceptance criteria

- [ ] One Generar action loads Baseline + ≤3 perfiles into session state
- [ ] Grid shows per-perfil total as `N (Δ −86)` (sign and spacing per grill)
- [ ] Grid omits top proveedor summary
- [ ] Grid omits Δ knobs / variables card
- [ ] Perfil slots reflect factory + custom pool selection agreed in config (up to 3)

## Blocked by

- 02-batch-http-api

## Comments
