# MOQ por proveedor (no SAPROD.Minimo)

El MOQ de SplitLeadTime es **por proveedor/oferta**, no `SAPROD.Minimo` ERP. **Ubicación del dato: decidir en P1.** Hasta entonces MOQ es nullable y el split usa solo `rot×LT` cuando falta.

**Status:** accepted (grill Q28=B, Q29=C)

## Discovery 2026-07-14

Searched SQL Server (`Procurement`, `Analitica`, `Proveedores`, `dbo`):

- `Analitica.Mercado_Vivo` — **no** tiene columna MOQ / pedido mínimo.
- Tablas `Proveedores.*` — sin MOQ por proveedor.
- `SAPROD.Minimo` / `ManejoStock.Minimo` existen pero son **mínimos ERP de farmacia**, no MOQ de compra al proveedor (prohibidos por este ADR).

**Decisión operativa:** seguir con MOQ nullable. No cablear SAPROD.Minimo. Cuando ops publique tabla/campo `moq` en ofertas o maestro de proveedores, mapear a `OfferLeg.moq` / columna `moq` en `market_offers`.

## Consequences

- P1 no se bloquea por schema MOQ.
- Cuando exista la fuente, enchufar a `max(rot×LT, MOQ)` sin cambiar la regla de dominio.
- No reactivar SAPROD.Minimo como MOQ sin nueva decisión.
