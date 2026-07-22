# ADR-0021: SAINSTA no-medicina alineada a Farma Pronto

## Context

El modal de categorías de Pedidos lee `dbo.SAINSTA` (`InsPadre` = padre; no hay
tabla `dbo.InsPadre`). El árbol legacy mezclaba raíces duplicadas y no coincidía
con el surtido no-medicamento de Farma Pronto. Medicinas ya tiene su propia
jerarquía Softland y no debe mutarse en esta fase.

## Decision

1. **Fuente de hojas:** nombres exactos de `product_cat` Farma Pronto, excluyendo
   ATC/medicamento/controlados.
2. **Padres sintéticos** (Cuidado Personal, Cabello, Hogar, …) solo para UI/árbol
   de 2 niveles vía `InsPadre`.
3. **IDs nuevos** en rangos 2100+ / 2200+; nodos viejos no-medicina se retiran bajo
   Anulados (`CodInst=27`) con prefijo `OLD::`.
4. **Remapeo de productos** `SAPROD.CodInst` por tabla semántica
   `legacy_name_to_new` en `sainsta_pronto_taxonomy.json`.
5. Migración como SQL transaccional generado + CLI dry-run; apply manual con backup.

## Consequences

- `GET /categories` mostrará el nuevo árbol tras el apply.
- Clasificación imperfecta de SKUs legacy hasta refinar el mapa o cruzar inventario.
- `Nivel` Softland puede quedar inconsistente (ya lo estaba); no es autoridad del FE.
