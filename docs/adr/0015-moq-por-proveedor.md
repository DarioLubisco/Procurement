# MOQ / mínimo por proveedor (no SAPROD.Minimo)

El mínimo de compra es **por proveedor**, no `SAPROD.Minimo` ERP.

**Status:** accepted — comportamiento de validación en **ADR-0016**

## Fuente canónica

Tabla: `[Procurement].[ProveedorConfig]`

| Campo | Rol |
|-------|-----|
| **`ProveedorID`** `INT IDENTITY` UNIQUE | Identificador numérico estable (uso preferido en UI/API) |
| **`CodProv`** `VARCHAR` PK | Alias operativo = `Mercado_Vivo.proveedor` (y FKs legacy: Horario, Backorder, Scorecard) |
| **`MontoMinimoPedidoUSD`** | Mínimo comercial en dólares (nullable / 0 = no aplica) |

Migraciones: `sql/008_…`, `sql/009_proveedor_config_proveedor_id.sql`.

**No hay FK a `dbo.SAPROV`** (CodProv fiscal `J-…` ≠ CodProv corto). Join del Generar: `CodProv` ↔ mercado.

`SAPROD.Minimo` / `ManejoStock.Minimo` siguen **prohibidos**.

## Consequences

- Identificar proveedores por **`ProveedorID`**; `CodProv`/`NombreCorto` son etiquetas de join/display.
- Flujo ValidarMinimos: **ADR-0016** (match de ofertas sigue por string `proveedor` del mercado = `CodProv`).
