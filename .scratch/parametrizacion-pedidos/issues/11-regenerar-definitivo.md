Status: resolved

# 11-regenerar-definitivo

Parent: `.scratch/parametrizacion-pedidos/PRD.md`  
Also listed in: `tickets.md`

## Regenerar PedidoDefinitivo (Intermedio/Avanzado)

**What to build:** Tras la Comparativa, el comprador regenera con controles Intermedio o Avanzado; se refrescan PedidoPropuesto y ComparativaCantidades juntos hacia PedidoDefinitivo. Knobs muertos (S4, kappa) no reaparecen.

**Blocked by:** API + FE Generar Sencillo (Comparativa + Propuesto con proveedor)

- [x] Regenerar is distinct from first Generar Sencillo in UX/language
- [x] Intermedio/Avanzado regeneration returns updated Propuesto + Comparativa
- [x] Dead S4 / kappa knobs are not exposed in Pedido profile UI
- [x] Overrides that are in living OptimizerConfig can affect Definitivo output

## Implementation notes

- `run_regenerar_definitivo` + `POST /api/pedidos/regenerar-definitivo`
- Living overrides via `apply_living_overrides`; dead S4/kappa rejected
- FE: section “Regenerar Pedido Definitivo” after Comparativa
- Schema: `GET /api/pedidos/overrides-schema`
