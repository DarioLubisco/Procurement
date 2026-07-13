Status: ready-for-agent

# 03-criterios-agrupacion

Parent: `.scratch/parametrizacion-pedidos/PRD.md`  
Also listed in: `tickets.md`

## CriteriosAgrupacion efectivos en DemandaGrupal y Baseline

**What to build:** La lista efectiva del request (default sistema: PA, FF, conc, cantidad_presentacion, contenido_neto) agrupa DemandaGrupal y PedidoBaseline; deja de mandar Molécula hardcodeada de tres attrs.

**Blocked by:** Seam `generar_pedido` → GenerarResult (Baseline real + stubs)

- [ ] Request criterios_agrupacion changes Grupo membership for Baseline aggregation
- [ ] Default five-attribute set used when no override provided
- [ ] DemandaGrupal / gaps use the same effective list as Baseline
- [ ] Hardcoded PA+FF+conc-only path is no longer the runtime authority
