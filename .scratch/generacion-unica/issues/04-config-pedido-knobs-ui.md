Status: resolved

# 04-config-pedido-knobs-ui

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

Config Pedido lets the comprador set `hermanos_top_n`, `rivales_top_n`, and `rivales_ofertas_por_rival` with the agreed defaults visible.

## Acceptance criteria

- [x] Three controls visible in Config Pedido (not buried only in Avanzado dump)
- [x] Defaults shown: 3 / 3 / 2
- [x] Values flow into the next Generar/batch request knobs
- [x] Invalid input is clamped or rejected with clear FE feedback

## Blocked by

- 03-knob-rivales-ofertas-por-rival

## Answer

Config Pedido block with `hermanosTopN` / `rivalesTopN` / `rivalesOfertasPorRival` (defaults 3/3/2). FE `collectCompetenciaOverrides()` → `buildSencilloPayload().overrides`. Backend applies overrides on Sencillo via `apply_living_overrides`; batch merges shared `overrides`. Clamp 1–10 with alert.

## Comments
