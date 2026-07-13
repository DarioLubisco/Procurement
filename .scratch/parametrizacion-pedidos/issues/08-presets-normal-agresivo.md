Status: ready-for-agent

# 08-presets-normal-agresivo

Parent: `.scratch/parametrizacion-pedidos/PRD.md`  
Also listed in: `tickets.md`

## Presets Normal y Agresivo

**What to build:** PresetSencillo Normal y Agresivo mapeados a ADR-0011/0013; en fixtures se distinguen de Conservador (amplifier/F5/pesos/split según preset).

**Blocked by:** Preset Conservador → Propuesto + ComparativaCantidades básica; GapExtensionOferta (F5); SplitLeadTime + MOQ nullable

- [ ] Normal maps to ADR-0011 (calibrated amp/F5/pesos, medium soft LeadTime)
- [ ] Agresivo maps to ADR-0013 (stronger amp/F5/price pesos; SplitLeadTime-aware)
- [ ] Same fixture inputs yield materially different Propuesto/Comparativa across the three presets
- [ ] Baseline remains unchanged when only the preset changes
