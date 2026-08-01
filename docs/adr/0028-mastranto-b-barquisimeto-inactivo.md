# MASTRANTO_B (Barquisimeto) inactivo; Centro canónico

**Status:** accepted  
**Date:** 2026-07-21  
**Related:** ADR-0015 (MOQ / ProveedorConfig), ADR-0016 (ValidarMinimos)

## Context

`Mercado_Vivo` marca `MASTRANTO_B` con `sucursal=BARQUISIMETO` y `MASTRANTO_C` con `CENTRO`. El comprador desactiva Barquisimeto.

`ProveedorConfig.Activo` solo afecta grupos comerciales (mínimos / borrador). **No** filtra ofertas de `Mercado_Vivo` en Generar.

## Decision

1. `MASTRANTO_B` → `Activo=0` (ProveedorID 11).
2. `MASTRANTO_C` → `Activo=1`, `NombreCorto='Mastranto Centro'` (ProveedorID 12); alias `MASTRANTO_C` → 12.
3. Generar excluye `MASTRANTO_B` vía `MERCADO_PROVEEDORES_EXCLUIDOS` en `map_mercado_vivo_dataframe`.
4. Backup: `ProveedorConfig_BKP_20260721_1147`, `ProveedorCodProvAlias_BKP_20260721_1147`.

## Consequences

- Validar mínimos / Guardar borrador usan solo Centro.
- Ofertas Barquisimeto no entran al motor hasta quitar el CodProv de `MERCADO_PROVEEDORES_EXCLUIDOS` y reactivar config.
