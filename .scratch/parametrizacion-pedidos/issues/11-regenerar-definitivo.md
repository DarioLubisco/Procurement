Status: ready-for-agent

# 11-regenerar-definitivo

Parent: `.scratch/parametrizacion-pedidos/PRD.md`  
Also listed in: `tickets.md`

## Regenerar PedidoDefinitivo (Intermedio/Avanzado)

**What to build:** Tras la Comparativa, el comprador regenera con controles Intermedio o Avanzado; se refrescan PedidoPropuesto y ComparativaCantidades juntos hacia PedidoDefinitivo. Knobs muertos (S4, kappa) no reaparecen.

**Blocked by:** API + FE Generar Sencillo (Comparativa + Propuesto con proveedor)

- [ ] Regenerar is distinct from first Generar Sencillo in UX/language
- [ ] Intermedio/Avanzado regeneration returns updated Propuesto + Comparativa
- [ ] Dead S4 / kappa knobs are not exposed in Pedido profile UI
- [ ] Overrides that are in living OptimizerConfig can affect Definitivo output
