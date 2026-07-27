Status: ready-for-agent

# 04-config-pedido-knobs-ui

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

Config Pedido lets the comprador set `hermanos_top_n`, `rivales_top_n`, and `rivales_ofertas_por_rival` with the agreed defaults visible.

## Acceptance criteria

- [ ] Three controls visible in Config Pedido (not buried only in Avanzado dump)
- [ ] Defaults shown: 3 / 3 / 2
- [ ] Values flow into the next Generar/batch request knobs
- [ ] Invalid input is clamped or rejected with clear FE feedback

## Blocked by

- 03-knob-rivales-ofertas-por-rival

## Comments
