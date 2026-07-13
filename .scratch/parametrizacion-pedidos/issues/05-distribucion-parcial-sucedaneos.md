Status: ready-for-agent

# 05-distribucion-parcial-sucedaneos

Parent: `.scratch/parametrizacion-pedidos/PRD.md`  
Also listed in: `tickets.md`

## DistribucionParcial multi-factor + sucedáneos en Comparativa

**What to build:** Cuotas parciales por línea Baseline según el motor completo (no winner-takes-all, no solo elasticidad); Propuesto puede usar otra BARRA del mismo Grupo; JustificacionDelta declara cambio de código cuando hay sucedáneo.

**Blocked by:** Preset Conservador → Propuesto + ComparativaCantidades básica

- [ ] Within a Grupo, multiple Baseline lines can receive partial Propuesto quotas
- [ ] Elasticidad alone does not dictate allocation when other motor factors conflict (e.g. LeadTime soft / price)
- [ ] Propuesto may resolve a Grupo need with a different BARRA from mercado vivo
- [ ] JustificacionDelta states code change when barra_propuesto ≠ barra_baseline
- [ ] Comparativa qty_propuesto is the line quota, not the entire Grupo gap dumped on one row
