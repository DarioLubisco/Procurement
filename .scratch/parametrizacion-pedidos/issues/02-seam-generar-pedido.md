Status: resolved

# 02-seam-generar-pedido

Parent: `.scratch/parametrizacion-pedidos/PRD.md`  
Also listed in: `tickets.md`

## Seam `generar_pedido` → GenerarResult (Baseline real + stubs)

**What to build:** Un solo contrato de orquestación `generar_pedido(PerfilPedido) → GenerarResult` que ya devuelve PedidoBaseline real más Propuesto/Comparativa en forma stub o identidad, inyectable sin HTTP/SQL vivos.

**Blocked by:** PedidoBaseline extraíble + parity en fixtures

- [x] `PerfilPedido` accepts cobertura, criterios_agrupacion, filtros_operativos, nivel, preset?, presupuesto_maximo?
- [x] `GenerarResult` exposes pedido_baseline, pedido_propuesto, comparativa_cantidades
- [x] Baseline in the result matches the extracted Baseline calculator on the same inputs
- [x] Fixture harness can call the seam without live DB

## Comments

- Implemented `generar_pedido` with identity stubs for Propuesto/Comparativa (2026-07-12).
