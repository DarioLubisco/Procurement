Status: ready-for-agent

# 10-api-fe-generar-sencillo

Parent: `.scratch/parametrizacion-pedidos/PRD.md`  
Also listed in: `tickets.md`

## API + FE Generar Sencillo (Comparativa + Propuesto con proveedor)

**What to build:** UI productiva Generar usa el seam unificado: muestra ComparativaCantidades y PedidoPropuesto con proveedor; permite Cobertura, FiltrosOperativos, CriteriosAgrupacion editables, PresetSencillo y presupuesto opcional. Excel BARRA×CANTIDAD deja de ser la salida humana primaria de esta fase.

**Blocked by:** DistribucionParcial multi-factor + sucedáneos en Comparativa; Presets Normal y Agresivo; Backorder desde tablas + resta igual en ambos lados

- [ ] Productive Generar calls unified path (not legacy-only Excel generator)
- [ ] Comprador sees Comparativa columns: Baseline BARRA/desc/qty, Propuesto BARRA/desc/qty, JustificacionDelta
- [ ] Comprador sees Propuesto with proveedor on first Generar
- [ ] First Generar UI is Sencillo only (preset + cobertura + filtros + criterios + optional budget)
- [ ] CriteriosAgrupacion editable before Generar; effective list sent on request
