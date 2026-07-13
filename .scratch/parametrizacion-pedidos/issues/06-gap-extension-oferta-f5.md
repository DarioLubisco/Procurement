Status: resolved

# 06-gap-extension-oferta-f5

Parent: `.scratch/parametrizacion-pedidos/PRD.md`  
Also listed in: `tickets.md`

## GapExtensionOferta (F5)

**What to build:** ExtensionCobertura dispara por Desvío bajo umbral; unidades extra refuerzan solo productos en oferta; tamaño Gap_ext = Gap_oferta + (Gap_grupo − Gap_oferta) × f con f ponderado por elasticidad×rotación entre no-oferta; JustificacionDelta audita f.

**Blocked by:** DistribucionParcial multi-factor + sucedáneos en Comparativa

- [x] F5 does not add coverage days to non-offer Grupo members
- [x] F5 does not dump the full Gap_grupo onto offer SKUs
- [x] Gap_ext uses non-offer-only rotation denominator for f
- [x] Fixture matching ADR-0012 example semantics passes
- [x] JustificacionDelta mentions F5 / f when extension applied

## Comments

- Pure `compute_gap_extension_oferta` + wired when `ext_max_dias_extra > 0` and Desvío ≤ −0.10 (2026-07-12).
