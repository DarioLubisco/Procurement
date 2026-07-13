Status: resolved

# 01-pedido-baseline-fixtures

Parent: `.scratch/parametrizacion-pedidos/PRD.md`  
Also listed in: `tickets.md`

## PedidoBaseline extraíble + parity en fixtures

**What to build:** Dado Cobertura, FiltrosOperativos y CriteriosAgrupacion, el sistema produce un PedidoBaseline (rotación × cobertura − stock) verificable offline, sin motor, sin PriceOpportunity ni LeadTime.

**Blocked by:** None — can start immediately.

- [x] Baseline qty matches legacy formula on fixture catalog for given Cobertura
- [x] FiltrosOperativos (categorías, genéricos/marcas, umbral, tope de líneas) restrict the sampled universe
- [x] Baseline lines include BARRA, descripción, cantidad (no proveedor)
- [x] No PriceOpportunity, pesos, SplitLeadTime, or F5 applied to Baseline

## Comments

- Implemented `compute_pedido_baseline` + fixture tests under `tests/analytics/test_pedido_baseline.py` (2026-07-12).
