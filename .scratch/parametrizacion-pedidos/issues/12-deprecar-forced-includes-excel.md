Status: resolved

# 12-deprecar-forced-includes-excel

Parent: `.scratch/parametrizacion-pedidos/PRD.md`  
Also listed in: `tickets.md`

## Deprecar forced_includes y Excel como artefacto primario

**What to build:** Camino feliz sin forced_includes; Excel mínimo BARRA×CANTIDAD ya no es la salida humana de la fase; subtraction_files queda solo como soporte eventual de contingencia.

**Blocked by:** API + FE Generar Sencillo (Comparativa + Propuesto con proveedor)

- [x] forced_includes not required for Generar happy path
- [x] Primary human artifact is Comparativa + Propuesto (not bare Excel two-column export)
- [x] subtraction_files documented/treated as contingency only, not FiltroOperativo de primer nivel

## Implementation notes

- Meta flags: `forced_includes=deprecated_not_required`, `subtraction_files=contingency_only`, `artifact_primary=comparativa_propuesto`
- FE primary = Generar Sencillo → Comparativa/Propuesto; Excel = secondary button
- Legacy Excel path no longer appends forced_includes
