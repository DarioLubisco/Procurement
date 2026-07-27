Status: ready-for-agent

# 05-payload-hermanos-rivales

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

Comparativa/justificación (or adjacent payload) carries Original/hermanos and Rivales offer rows sized by `hermanos_top_n`, `rivales_top_n`, and `rivales_ofertas_por_rival`, enough for the replacement modal without a second market fetch.

## Acceptance criteria

- [ ] Each rival can include up to `rivales_ofertas_por_rival` offers (desc, proveedor, precio)
- [ ] Hermanos capped by `hermanos_top_n`; rivales by `rivales_top_n`
- [ ] Fixture/assert cardinality changes when knobs change
- [ ] No live Mercado round-trip required to open the modal for data already on the row

## Blocked by

- 03-knob-rivales-ofertas-por-rival

## Comments
