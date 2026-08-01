# CriteriosAgrupacion editables y default programable en FE

Antes del primer Generar, el comprador ve y puede editar los **CriteriosAgrupacion** del Grupo. El default de producto es:

`principio_activo`, `forma_farmaceutica`, `concentracion`, `cantidad_presentacion` (Presentación = unidades en el empaque).

`contenido_neto` (ml/g) sigue en la whitelist y se puede marcar a mano; **no** es default de sistema (grill 2026-07-22).

Ese default vive en **dos capas**: default de sistema en código/`RotacionGrupal_Atributos.es_base` + preferencia de usuario en FE (override). El request envía siempre la lista efectiva. Baseline y Propuesto usan el mismo set de la corrida.

**Status:** accepted

## Consequences

- Los attrs del default ⊆ `ATRIBUTOS_VALIDOS`; Presentación es `es_base`, Contenido neto no.
- Baseline y Propuesto usan el **mismo** set (Gap agregado + emparejamiento).
- CRUD/config de default de sistema (junto a OptimizerConfig o tabla hermana); FE guarda override de usuario.
- Optimizer consume CriteriosAgrupacion del request, no Molécula hardcodeada de 3 attrs.