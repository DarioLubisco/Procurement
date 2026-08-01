# Perfil del primer Generar vs regeneración

**Status:** accepted (amended 2026-07-26 — *generación única*; replaces the prior “first Generar = one Sencillo only” rule)

**PedidoBaseline** remains **sin motor**: rotación × cobertura − stock/backorder (legacy sampling), shared Cobertura / FiltrosOperativos / CriteriosAgrupacion. It never carries PriceOpportunity, F1–F5 weights, or soft LeadTime.

The first **Generar** may run **up to three** PerfilPedido slots in one batch (factory PresetSencillo and/or custom presets) against that **single shared Baseline**. Each slot yields its own PedidoPropuesto + ComparativaCantidades (same grain as ADR-0004). The comprador chooses a column, then may **regenerate Intermedio/Avanzado on the active perfil only**; Baseline stays put. ValidarMinimosProveedor and Guardar v1 apply to the chosen perfil, not inline for every batch sibling.

Spec: `.scratch/generacion-unica/PRD.md`.

## Consequences

- UI happy path: Generar → Baseline once + ≤3 perfiles → grilla → Comparativa del elegido → comparador (re-gen activo) / mínimos / Guardar solo ese perfil.
- Primary UI no longer requires the serial “pick one Sencillo → Generar → Regenerar Definitivo as the only compare story.”
- Paridad P1 del Baseline = Motor B clásico, not “perfil Lineal del v3.2”.

## Prior decision (historical)

Previously accepted text: first PedidoPropuesto used only nivel Sencillo (one preset); Intermedio/Avanzado unlocked only on regeneración. That single-preset-first rule is **superseded** by this amendment for the productive path.
