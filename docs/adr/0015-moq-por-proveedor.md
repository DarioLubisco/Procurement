# MOQ / mínimo por proveedor (no SAPROD.Minimo)

El mínimo de compra es **por proveedor comercial**, no `SAPROD.Minimo` ERP.

**Status:** accepted — comportamiento de validación en **ADR-0016**

## Fuente canónica

Tabla: `[Procurement].[ProveedorConfig]`

| Campo | Rol |
|-------|-----|
| **`ProveedorID`** `INT IDENTITY` UNIQUE | Identificador numérico de la **entidad comercial** (UI/API, agregación MOQ) |
| **`CodProv`** `VARCHAR` PK | Join a `Mercado_Vivo.proveedor` + FKs legacy (Horario, Backorder, Scorecard, BRNS) |
| **`MontoMinimoPedidoUSD`** | Mínimo comercial en dólares (nullable / 0 = no aplica); solo filas **Activo=1** |

Aliases de mercado → mismo comercial:

Tabla: `[Procurement].[ProveedorCodProvAlias]` (`CodProv` → `ProveedorID`)

- Varios strings de `Mercado_Vivo` (p.ej. `INSUAMINCA_G` / `_M`, `MASTRANTO_C`) mapean al mismo `ProveedorID`.
- Filas no-canónicas en `ProveedorConfig` quedan `Activo=0` (FKs intactas); el mínimo se lee del canónico Activo.
- Match de alias **case-insensitive** en el loader / ValidarMinimos.

Migraciones: `sql/008_…`, `sql/009_proveedor_config_proveedor_id.sql`, `sql/010_proveedor_cod_prov_alias.sql`.

**No hay FK a `dbo.SAPROV`** (CodProv fiscal `J-…` ≠ CodProv corto). Join del Generar: string mercado ↔ CodProv/alias.

`SAPROD.Minimo` / `ManejoStock.Minimo` siguen **prohibidos**.

## Consequences

- Identificar entidades comerciales por **`ProveedorID`**; `CodProv`/`NombreCorto` son etiquetas de join/display.
- ValidarMinimos agrega USD y encola **por `ProveedorID`** (un mínimo por lab), no por cada string de mercado.
- Flujo ValidarMinimos: **ADR-0016**.
