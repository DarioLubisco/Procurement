Status: ready-for-agent

# 09-backorder-tablas

Parent: `.scratch/parametrizacion-pedidos/PRD.md`  
Also listed in: `tickets.md`

## Backorder desde tablas + resta igual en ambos lados

**What to build:** Backorder leído de tablas dedicadas del backend (schema a localizar/documentar en el ticket); misma resta en PedidoBaseline y PedidoPropuesto; subtraction_files no es requisito de paridad.

**Blocked by:** Seam `generar_pedido` → GenerarResult (Baseline real + stubs)

- [ ] Backorder source tables identified and documented
- [ ] Same backorder quantities subtract from Baseline and Propuesto
- [ ] Comparativa deltas are not polluted by one-sided backorder
- [ ] Happy path does not require subtraction_files
