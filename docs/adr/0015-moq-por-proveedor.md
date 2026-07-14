# MOQ / mínimo por proveedor (no SAPROD.Minimo)

El mínimo de compra es **por proveedor**, no `SAPROD.Minimo` ERP.

**Status:** accepted — comportamiento de validación en **ADR-0016**

## Fuente canónica

Tabla: `[Procurement].[ProveedorConfig]`  
Columna: **`MontoMinimoPedidoUSD`** `DECIMAL(18,2) NULL`  
Migración: `sql/008_proveedor_config_monto_minimo_usd.sql`.

Join: `ProveedorConfig.CodProv` ↔ `Mercado_Vivo.proveedor`.

`SAPROD.Minimo` / `ManejoStock.Minimo` siguen **prohibidos**.

## Consequences

- Monto en **USD** (no unidades). El MOQ en unidades del SplitLeadTime (`OfferLeg.moq`) es concepto aparte.
- Flujo de validación / UX: ver **ADR-0016**.
