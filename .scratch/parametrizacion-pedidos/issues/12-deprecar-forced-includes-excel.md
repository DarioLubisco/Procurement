Status: ready-for-agent

# 12-deprecar-forced-includes-excel

Parent: `.scratch/parametrizacion-pedidos/PRD.md`  
Also listed in: `tickets.md`

## Deprecar forced_includes y Excel como artefacto primario

**What to build:** Camino feliz sin forced_includes; Excel mínimo BARRA×CANTIDAD ya no es la salida humana de la fase; subtraction_files queda solo como soporte eventual de contingencia.

**Blocked by:** API + FE Generar Sencillo (Comparativa + Propuesto con proveedor)

- [ ] forced_includes not required for Generar happy path
- [ ] Primary human artifact is Comparativa + Propuesto (not bare Excel two-column export)
- [ ] subtraction_files documented/treated as contingency only, not FiltroOperativo de primer nivel
