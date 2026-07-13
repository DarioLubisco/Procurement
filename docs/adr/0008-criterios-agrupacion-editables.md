# CriteriosAgrupacion editables y default programable en FE

Antes del primer Generar, el comprador ve y puede editar los **CriteriosAgrupacion** del Grupo. El default de producto es:

`principio_activo`, `forma_farmaceutica`, `concentracion`, `cantidad_presentacion`, `contenido_neto`

Ese default vive en **dos capas**: default de sistema en BD (perfil/config) + preferencia de usuario en FE (override). El request envía siempre la lista efectiva. Baseline y Propuesto usan el mismo set de la corrida.

**Status:** accepted

## Consequences

- Los cinco attrs ya están en `ATRIBUTOS_VALIDOS`.
- Baseline y Propuesto usan el **mismo** set (Gap agregado + emparejamiento).
- CRUD/config de default de sistema (junto a OptimizerConfig o tabla hermana); FE guarda override de usuario.
- Optimizer consume CriteriosAgrupacion del request, no Molécula hardcodeada de 3 attrs.
