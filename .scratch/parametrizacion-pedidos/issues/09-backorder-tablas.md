Status: resolved

# 09-backorder-tablas

Parent: `.scratch/parametrizacion-pedidos/PRD.md`  
Also listed in: `tickets.md`

## Backorder desde tablas + resta igual en ambos lados

**What to build:** Backorder leído de tablas dedicadas del backend (schema a localizar/documentar en el ticket); misma resta en PedidoBaseline y PedidoPropuesto; subtraction_files no es requisito de paridad.

**Blocked by:** Seam `generar_pedido` → GenerarResult (Baseline real + stubs)

- [x] Backorder source tables identified and documented
- [x] Same backorder quantities subtract from Baseline and Propuesto
- [x] Comparativa deltas are not polluted by one-sided backorder
- [x] Happy path does not require subtraction_files

## Schema discovery (P1) — 2026-07-12

Searched `sql/`, `backend/`, `analytics_engine/`: **no dedicated Backorder / en-tránsito table** exists yet.

Legacy: Excel `subtraction_files` in `backend/routers/pedidos.py` (`BARRA`×`CANTIDAD`) — ADR-0009 contingency only.

### Injectable contract

`generar_pedido(..., backorder=DataFrame)` with columns `barra`, `cantidad`. Same map subtracted from Baseline (and thus Propuesto via Baseline ceiling). Module docstring in `analytics_engine/core/backorder.py` holds the full note for when ops names the physical tables.
