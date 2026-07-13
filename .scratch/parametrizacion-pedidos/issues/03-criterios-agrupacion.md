Status: resolved

# 03-criterios-agrupacion

Parent: `.scratch/parametrizacion-pedidos/PRD.md`  
Also listed in: `tickets.md`

## CriteriosAgrupacion efectivos en DemandaGrupal y Baseline

**What to build:** La lista efectiva del request (default sistema: PA, FF, conc, cantidad_presentacion, contenido_neto) agrupa DemandaGrupal y PedidoBaseline; deja de mandar Molécula hardcodeada de tres attrs.

**Blocked by:** Seam `generar_pedido` → GenerarResult (Baseline real + stubs)

- [x] Request criterios_agrupacion changes Grupo membership for Baseline aggregation
- [x] Default five-attribute set used when no override provided
- [x] DemandaGrupal / gaps use the same effective list as Baseline
- [x] Hardcoded PA+FF+conc-only path is no longer the runtime authority

## Comments

- `resolve_criterios_agrupacion` + `compute_demanda_grupal` are the Generar-path authority; optimizer Molécula-3 remains legacy until later tickets wire Propuesto to this resolver (2026-07-12).
