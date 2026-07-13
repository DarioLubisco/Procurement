# MOQ por proveedor (no SAPROD.Minimo)

El MOQ de SplitLeadTime es **por proveedor/oferta**, no `SAPROD.Minimo` ERP. **Ubicación del dato: decidir en P1.** Hasta entonces MOQ es nullable y el split usa solo `rot×LT` cuando falta.

**Status:** accepted (grill Q28=B, Q29=C)

## Consequences

- P1 no se bloquea por schema MOQ.
- Cuando exista la fuente, enchufar a `max(rot×LT, MOQ)` sin cambiar la regla de dominio.
- No reactivar SAPROD.Minimo como MOQ sin nueva decisión.
