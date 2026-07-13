Status: resolved

# 07-split-leadtime-moq

Parent: `.scratch/parametrizacion-pedidos/PRD.md`  
Also listed in: `tickets.md`

## SplitLeadTime + MOQ nullable

**What to build:** Si Existen < rotación_diaria × LT del proveedor rápido, mínimo al rápido = max(rot×LT, MOQ_proveedor?) topeado por stock_proveedor de esa oferta; resto al más barato; si Existen ya cubre rot×LT, no forzar mínimo; MOQ nullable sin usar SAPROD.Minimo; JustificacionDelta explica el split.

**Blocked by:** DistribucionParcial multi-factor + sucedáneos en Comparativa

- [x] Split fires only when Existen < rot × LT_fast
- [x] Fast leg qty = max(rot×LT, MOQ) when MOQ present, else rot×LT, capped by offer stock
- [x] Remainder goes to cheapest worse-LT supplier
- [x] No forced fast minimum when Existen already covers rot×LT
- [x] PedidoPropuesto can show 2+ lines same product different proveedores
- [x] Missing MOQ does not block; SAPROD.Minimo is never used as MOQ

## Implementation notes

- Pure seam: `analytics_engine/core/split_lead_time.py` (`compute_split_lead_time`)
- Wired into `distribute_parcial` → `generar_pedido` (extra Propuesto legs; one Comparativa row)
- MOQ via nullable `moq` on offer rows; never SAPROD.Minimo
