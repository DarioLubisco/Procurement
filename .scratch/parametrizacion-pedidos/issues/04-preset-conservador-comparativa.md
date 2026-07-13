Status: ready-for-agent

# 04-preset-conservador-comparativa

Parent: `.scratch/parametrizacion-pedidos/PRD.md`  
Also listed in: `tickets.md`

## Preset Conservador → Propuesto + ComparativaCantidades básica

**What to build:** Primer Generar Sencillo con PresetSencillo Conservador: PedidoPropuesto con proveedor, ComparativaCantidades anclada a BARRA Baseline, deltas mínimos vs Baseline, JustificacionDelta al menos por cantidad.

**Blocked by:** Seam `generar_pedido` → GenerarResult (Baseline real + stubs); CriteriosAgrupacion efectivos en DemandaGrupal y Baseline

- [ ] Conservador maps to ADR-0010 knobs (amplifier off, ext_max_dias_extra 0, pesos almost only posicionamiento, soft LeadTime low)
- [ ] Propuesto lines include proveedor and cantidad
- [ ] Comparativa has one row per Baseline BARRA with qty Baseline and qty Propuesto
- [ ] Controlled fixtures show near-minimal delta vs Baseline under Conservador
- [ ] Optional presupuesto_maximo is accepted on Sencillo without requiring Avanzado
