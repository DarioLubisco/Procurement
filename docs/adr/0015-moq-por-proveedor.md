# MOQ / mínimo por proveedor (no SAPROD.Minimo)

El mínimo de compra es **por proveedor**, no `SAPROD.Minimo` ERP.

**Status:** accepted (grill Q28=B, Q29=C; fuente schema 2026-07-14)

## Fuente canónica (2026-07-14)

Tabla: `[Procurement].[ProveedorConfig]`  
Columna: **`MontoMinimoPedidoUSD`** `DECIMAL(18,2) NULL`  
Unidad: **dólares** (mínimo de pedido monetario), no unidades de SKU.  
Migración: `sql/008_proveedor_config_monto_minimo_usd.sql`.

`Analitica.Mercado_Vivo` sigue sin MOQ por oferta. `SAPROD.Minimo` / `ManejoStock.Minimo` siguen **prohibidos** como sustituto.

## Consequences

- Hasta que haya valor cargado, el campo es NULL (DROCERCA hoy = NULL).
- El SplitLeadTime histórico usa `moq` en **unidades** (`max(rot×LT, MOQ)`). Un monto USD requiere regla distinta (p.ej. convertir con precio de oferta, o validar `sum(qty×precio) ≥ MontoMinimoPedidoUSD` por proveedor). **Cableado al motor: pendiente de grill.**
- No reactivar `SAPROD.Minimo` como MOQ sin nueva decisión.
