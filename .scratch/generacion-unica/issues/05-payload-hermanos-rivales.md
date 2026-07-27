Status: resolved

# 05-payload-hermanos-rivales

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

Comparativa/justificación (or adjacent payload) carries Original/hermanos and Rivales offer rows sized by `hermanos_top_n`, `rivales_top_n`, and `rivales_ofertas_por_rival`, enough for the replacement modal without a second market fetch.

## Acceptance criteria

- [x] Each rival can include up to `rivales_ofertas_por_rival` offers (desc, proveedor, precio)
- [x] Hermanos capped by `hermanos_top_n`; rivales by `rivales_top_n`
- [x] Fixture/assert cardinality changes when knobs change
- [x] No live Mercado round-trip required to open the modal for data already on the row

## Blocked by

- 03-knob-rivales-ofertas-por-rival

## Answer

`rivales_top_n` / `competencia_payload` now group by proveedor and attach `ofertas[]` (capped by `rivales_ofertas_por_rival`, default 2). Wired from knobs in `distribucion_parcial`. Tests: `test_competencia_ofertas_por_rival.py`. FE modal consumption is ticket 09.

## Comments
