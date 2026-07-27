Status: resolved

# 06-fe-grilla-batch-delta

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

Primary Generar calls the batch API and shows a results grid of perfiles with totals formatted `N (Δ −86)` vs PedidoBaseline — no top proveedor, no Δ-knobs/variables card.

## Acceptance criteria

- [x] One Generar action loads Baseline + ≤3 perfiles into session state
- [x] Grid shows per-perfil total as `N (Δ −86)` (sign and spacing per grill)
- [x] Grid omits top proveedor summary
- [x] Grid omits Δ knobs / variables card
- [x] Perfil slots reflect factory + custom pool selection agreed in config (up to 3)

## Blocked by

- 02-batch-http-api

## Answer

Primary Generar → `POST /api/pedidos/generar-batch`. Config has 3 perfil slots (factory Conservador/Normal/Agresivo + custom presets with overrides). `stashBatchResult` + `renderBatchResultsGrid` show `formatTotalWithDelta` (`938 (Δ −86)`). No top proveedor / Δ-knobs. Column click → Comparativa is ticket 07.

## Comments
