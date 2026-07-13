Status: ready-for-agent

# 02-seam-generar-pedido

Parent: `.scratch/parametrizacion-pedidos/PRD.md`  
Also listed in: `tickets.md`

## Seam `generar_pedido` → GenerarResult (Baseline real + stubs)

**What to build:** Un solo contrato de orquestación `generar_pedido(PerfilPedido) → GenerarResult` que ya devuelve PedidoBaseline real más Propuesto/Comparativa en forma stub o identidad, inyectable sin HTTP/SQL vivos.

**Blocked by:** PedidoBaseline extraíble + parity en fixtures

- [ ] `PerfilPedido` accepts cobertura, criterios_agrupacion, filtros_operativos, nivel, preset?, presupuesto_maximo?
- [ ] `GenerarResult` exposes pedido_baseline, pedido_propuesto, comparativa_cantidades
- [ ] Baseline in the result matches the extracted Baseline calculator on the same inputs
- [ ] Fixture harness can call the seam without live DB
