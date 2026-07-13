# Spec: Parametrización unificada de pedidos

Status: ready-for-agent

Feature: parametrizacion-pedidos  
Sources: `CONTEXT.md`, ADRs 0001–0015 (grill 0004–0015 manda sobre enmiendas/`Lineal`), handoff 2026-07-12, conversación Grill: parametrización Pedido  
Seams agreed: primary `generar_pedido(PerfilPedido) → GenerarResult`; secondary pure math for GapExtensionOferta, SplitLeadTime, DemandaGrupal by CriteriosAgrupacion

---

## Problem Statement

Hoy el comprador genera pedidos desde una UI que solo habla con el generador legacy (Excel `BARRA`×`CANTIDAD`, sin proveedor ni explicación). En paralelo existe un Optimizer v3.2 con scoring, mercado vivo y más parámetros — pero sin FE y con criterios de agrupación ignorados, lead time que no parte cantidades, F5 que no refuerza ofertas como se acordó, y parámetros muertos en el schema. El comprador no puede comparar el pedido “solo rotación” con un propuesto del motor, ni reafinar Sencillo → Intermedio/Avanzado hacia un definitivo, ni ver por qué cambió una cantidad o un código de barras dentro del Grupo.

## Solution

Un solo flujo productivo **Generar** que, en la misma corrida y con los mismos CriteriosAgrupacion / Cobertura / FiltrosOperativos / Backorder:

1. Calcula **PedidoBaseline** (legacy por rotación, **sin motor**).
2. Calcula **PedidoPropuesto** (motor completo, perfil **Sencillo**: PresetSencillo + presupuesto opcional) con **proveedor**.
3. Entrega **ComparativaCantidades** (fila anclada a BARRA Baseline; Propuesto puede ser otra BARRA del Grupo; JustificacionDelta multi-factor).

Tras revisar la Comparativa, el comprador regenera con Intermedio/Avanzado hacia **PedidoDefinitivo**. `forced_includes` deprecado; Backorder desde tablas backend (mismo dato en Baseline y Propuesto); `subtraction_files` solo soporte eventual.

## User Stories

1. As a comprador, I want Generar to show Baseline and Propuesto side by side, so that I can see what the motor changed versus rotación pura.
2. As a comprador, I want each ComparativaCantidades row anchored to a Baseline BARRA, so that I can follow the sampling I already understand.
3. As a comprador, I want product descriptions on Baseline and Propuesto lines, so that I buy by description not by bare barcode.
4. As a comprador, I want JustificacionDelta when quantities differ, so that I know why the motor moved units.
5. As a comprador, I want JustificacionDelta to declare a code change when Propuesto uses another BARRA of the same Grupo, so that I notice sucedáneos.
6. As a comprador, I want Propuesto lines to include proveedor on first Generar, so that I can review purchase assignment without a second step.
7. As a comprador, I want the first Generar to use only PerfilPedido Sencillo, so that I am not forced into advanced knobs before seeing a Comparativa.
8. As a comprador, I want to pick PresetSencillo Conservador, Normal, or Agresivo, so that I control how much the motor bets on price opportunities.
9. As a comprador, I want an optional presupuesto máximo on Sencillo Generar, so that I can cap spend without opening Avanzado.
10. As a comprador, I want PedidoBaseline never to apply PriceOpportunity, pesos, or LeadTime soft, so that Baseline stays the honest legacy reference.
11. As a comprador, I want to edit CriteriosAgrupacion before first Generar, so that Grupo membership matches how I think about equivalents.
12. As a comprador, I want system default CriteriosAgrupacion = principio_activo, forma_farmaceutica, concentracion, cantidad_presentacion, contenido_neto, so that I start from the agreed product default.
13. As a comprador, I want my FE override of CriteriosAgrupacion to win over the system default for my session/request, so that my preference sticks without changing everyone else's default.
14. As a comprador, I want Baseline and Propuesto to use the same CriteriosAgrupacion in one run, so that ComparativaCantidades compares apples to apples at Grupo level.
15. As a comprador, I want FiltrosOperativos (categorías, genéricos/marcas, umbral de rotación, tope de líneas) to define Baseline sampling, so that Necesidad starts from the universe I filtered.
16. As a comprador, I want Propuesto to be allowed to resolve a Grupo need with a different BARRA from mercado vivo, so that stockouts or better offers can substitute without forced_includes.
17. As a comprador, I want forced_includes deprecated, so that I am not maintaining a parallel “force SKU” path.
18. As a comprador, I want DistribucionParcial multi-factor (not winner-takes-all, not elasticidad alone), so that quotas reflect the full motor including despacho timing and price.
19. As a comprador, I want Elasticidad to be one input among many, so that high elasticidad cannot override a bad LeadTime by itself.
20. As a comprador, I want regenerar after Comparativa with Intermedio or Avanzado knobs, so that I can produce PedidoDefinitivo without losing the first-pass context.
21. As a comprador, I want PedidoDefinitivo regeneration to refresh ComparativaCantidades and Propuesto together, so that deltas stay consistent with the new profile.
22. As a comprador, I want Cobertura (días) shared by Baseline and Propuesto, so that horizon differences do not fake a motor delta.
23. As a comprador, I want Backorder subtracted equally from Baseline and Propuesto, so that tránsito does not look like a motor effect in the Comparativa.
24. As a comprador, I want Backorder to come from dedicated backend tables, so that I do not depend on uploading Excel restas for the happy path.
25. As a comprador, I want subtraction_files available only as eventual contingency support, so that ops can still inject BARRA×CANTIDAD restas if tables fail.
26. As a comprador using Conservador, I want minimal delta vs Baseline (amplifier off, F5 days extra 0, pesos almost only posicionamiento, soft LeadTime low), so that I can trust a near-parity first pass.
27. As a comprador using Normal, I want v3.2-calibrated amplifier/F5/pesos and medium soft LeadTime, so that I get the current calibrated aggressiveness.
28. As a comprador using Agresivo, I want stronger PriceOpportunity, higher F5 caps, price-heavy pesos, and SplitLeadTime-aware behavior, so that I chase ofertas harder.
29. As a comprador, I want ExtensionCobertura (F5) to fire when Grupo offers breach the Desvío threshold, so that price opportunities extend coverage intentionally.
30. As a comprador, I want F5 extra units to reinforce only products on offer, so that non-offer Grupo members are not inflated by the extension.
31. As a comprador, I want GapExtensionOferta sized as Gap_oferta + (Gap_grupo − Gap_oferta) × f with f from non-offer elasticities weighted by their rotation share among non-offer members, so that extension is intermediate—not full group gap dumped on the offer.
32. As a comprador, I want SplitLeadTime when Existen < rotación_diaria × LT of the fast supplier, so that urgent cover is not left to the cheapest slow supplier alone.
33. As a comprador, I want SplitLeadTime minimum to the fast supplier = max(rot×LT, MOQ_proveedor) capped by that offer's stock_proveedor, so that the fast buy is feasible and MOQ-aware when MOQ exists.
34. As a comprador, I want the remainder of SplitLeadTime demand on the cheapest (worse LT) supplier, so that cost of opportunity is covered without buying everything expensive.
35. As a comprador, I want SplitLeadTime not to force a fast minimum when Existen already covers rot×LT, so that we do not over-buy fast stock.
36. As a comprador, I want MOQ to be per proveedor/oferta and nullable until P1 source exists, so that missing MOQ degrades to rot×LT only without blocking delivery.
37. As a comprador, I want MOQ never silently taken from SAPROD.Minimo ERP, so that ERP mínimo is not confused with purchase MOQ.
38. As a comprador, I want Propuesto to allow multiple lines for the same product with different proveedores when SplitLeadTime fires, so that the split is visible in the order.
39. As a comprador, I want JustificacionDelta to mention SplitLeadTime trigger, MOQ applied, and stock cap when relevant, so that multi-supplier splits are auditable.
40. As a comprador, I want JustificacionDelta to mention F5 f and non-offer rotation weights when extension applied, so that GapExtensionOferta is auditable.
41. As a comprador, I want Excel-only BARRA×CANTIDAD human output deprecated for this phase, so that the productive artifact is Comparativa + Propuesto con proveedor.
42. As a comprador, I want Necesidad (quantities without supplier) treated as distinct from Pedido, so that sampling language stays clear.
43. As a comprador, I want PriceOpportunity presented as one business idea (score / qty / días extra) rather than three unrelated F4/amp/F5 knobs in Sencillo UI, so that Intermedio language stays coherent (ADR-0002).
44. As a procurement engineer, I want a single orchestration contract generar_pedido, so that Baseline + Propuesto + Comparativa are not maintained as two generators forever.
45. As a procurement engineer, I want the productive FE to call the unified Generar path (preserving operational filters/export needs of Motor B where still required), so that UI and motor stop being split-brain.
46. As a procurement engineer, I want Optimizer to consume CriteriosAgrupacion from the request instead of hardcoded PA+FF+conc, so that ADR-0008 is real in runtime.
47. As a procurement engineer, I want DemandaGrupal aggregation aligned with CriteriosAgrupacion (prefer RotacionGrupal as demand source over duplicate inline catalog math), so that Baseline and Propuesto share demand semantics.
48. As a procurement engineer, I want PresetSencillo mapped to OptimizerConfig knobs per ADR-0010/0011/0013, so that UI presets are not free-text config dumps.
49. As a procurement engineer, I want system default CriteriosAgrupacion persisted in BD (profile/config) with FE override, so that defaults are not only localStorage.
50. As a procurement engineer, I want apply_lead_time_split to allocate quantities (not only annotate stockout cost), so that ADR-0014 is implemented.
51. As a procurement engineer, I want GapExtensionOferta implemented as specified (not per-offer-only coverage_extension and not whole-group days to everyone), so that ADR-0012 is implemented.
52. As a procurement engineer, I want DistribucionParcial to emit per-Baseline-BARRA proposed quotas for ComparativaCantidades, so that rows are not winner-takes-all group dumps.
53. As a procurement engineer, I want S4 and kappa/quadratic_ceiling kept out of active Pedido schema until explicit reactivation, so that dead knobs do not reappear in UI.
54. As a QA engineer, I want golden fixtures of known Grupos asserting Baseline qty, Propuesto allocation, and Comparativa pairing including sucedáneo cases, so that regressions are caught without live DB.
55. As a QA engineer, I want pure-function tests for GapExtensionOferta and SplitLeadTime math, so that ADR formulas are locked independent of orchestration.
56. As a QA engineer, I want Conservador runs to show near-minimal deltas vs Baseline on controlled fixtures, so that preset intent is verifiable.
57. As an ops user, I want locating/documenting Backorder table schema in P1 without blocking the rest of generar_pedido, so that table discovery does not stall the unified flow.
58. As a comprador, I want regenerating Definitivo not to be called “first Generar”, so that language stays honest about Sencillo vs reafinación.
59. As a comprador, I want umbral/tope filters not to guarantee the same BARRA set in Propuesto, so that I understand substitutes can enter from mercado vivo.
60. As a product owner, I want ADR-0001’s “perfil Lineal ≡ Excel” reinterpreted as Baseline = real legacy math outside the motor + Propuesto = motor, so that we do not fake Lineal parity as the Baseline story.

## Implementation Decisions

1. **Primary seam / orchestration** — Introduce (or evolve the existing optimizer orchestration into) a single contract `generar_pedido(PerfilPedido) → GenerarResult` that returns PedidoBaseline, PedidoPropuesto, and ComparativaCantidades in one call. This is the product surface for Generar; HTTP adapters (legacy generate proxy / v2 optimize) sit outside the seam.

2. **PerfilPedido / GenerarResult shape** (decision-rich contract; not a working demo):

```
PerfilPedido:
  cobertura: int
  criterios_agrupacion: list[str]   # effective list always sent
  filtros_operativos: { categorias, genericos_marcas, umbral_rotacion, num_rows }
  nivel: Sencillo | Intermedio | Avanzado
  preset?: Conservador | Normal | Agresivo   # required for Sencillo
  presupuesto_maximo?: float
  overrides?: ...                    # Intermedio/Avanzado only; exact knobs not fully grilled

GenerarResult:
  pedido_baseline: [{ barra, descripcion, cantidad }]
  pedido_propuesto: [{ barra, descripcion, proveedor, cantidad, ... }]
  comparativa_cantidades: [{
    barra_baseline, desc_baseline, qty_baseline,
    barra_propuesto, desc_propuesto, qty_propuesto,
    justificacion_delta
  }]
```

3. **PedidoBaseline** — Computed with legacy rotación × Cobertura − stock (− Backorder), aggregated with the run’s CriteriosAgrupacion. Does **not** enter PriceOpportunity, scoring pesos, SplitLeadTime, or F5. Reinterprets ADR-0001: do not implement Baseline as “perfil Lineal inside v3.2”; Baseline is the legacy path folded into the orchestrator.

4. **PedidoPropuesto** — Full motor: Elasticidad, PriceOpportunity (ADR-0002 unification may be gradual behind the interface), pesos, presupuesto, LeadTime soft **and** SplitLeadTime qty allocation, stock de oferta, GapExtensionOferta/F5 per ADR-0012, DistribucionParcial multi-factor (ADR-0006). May substitute BARRAs within Grupo (ADR-0005).

5. **ComparativaCantidades** — One row per Baseline BARRA; Propuesto qty is the partial quota for that line (or paired substitute BARRA), not the entire Grupo total dumped on one row (ADR-0004).

6. **CriteriosAgrupacion** — Default five attrs in BD; FE override; request always sends effective list; Baseline + Propuesto + DemandaGrupal use it. Drop hardcoded three-attr Molécula as the only runtime grouping.

7. **Presets** — Map Conservador / Normal / Agresivo exactly per ADR-0010 / 0011 / 0013. Baseline never consumes presets.

8. **Backorder** — Reader from dedicated backend tables (names/schema to resolve in P1). Same subtraction on Baseline and Propuesto. `subtraction_files` optional contingency only (ADR-0009).

9. **MOQ** — Nullable field on offer/proveedor; SplitLeadTime uses `max(rot×LT, MOQ)` when present else `rot×LT`. Physical source decided in P1; do not use SAPROD.Minimo (ADR-0015).

10. **Secondary seams** — Pure functions for `GapExtensionOferta`, SplitLeadTime quantity split, and DemandaGrupal/gap calculation parameterized by CriteriosAgrupacion. Keep them thin; orchestration remains the behavior seam under test for user-visible Generar.

11. **API / FE** — Productive Generar UI must consume the unified result (Comparativa + Propuesto with proveedor). Preserve needed operational concerns from Motor B (FiltrosOperativos, eventual export) via adapter around `generar_pedido`, not a second generator. Exact Intermedio vs Avanzado knob lists were not fully grilled — expose Sencillo fully; Intermedio/Avanzado may pass through living OptimizerConfig fields excluding dead S4/kappa until a follow-up grill.

12. **PriceOpportunity** — Target unified module (ADR-0002); may land gradually if Preset mapping and F5 semantics (ADR-0012) land first, without changing PerfilPedido.

13. **Deprecations** — `forced_includes` out of happy path; Excel-only BARRA×CANTIDAD as human primary output out for this phase; do not reintroduce kappa ceilings.

14. **Demand source** — Prefer `RotacionGrupal` / shared DemandaGrupal for group gaps under active CriteriosAgrupacion rather than maintaining a divergent catalog SQL path in the optimizer (aligns with ADR-0001 consequences, tempered by Baseline-outside-motor decision).

## Testing Decisions

1. **Good tests** assert observable Generar behavior: Baseline quantities, Propuesto lines (BARRA, proveedor, qty), Comparativa pairing and JustificacionDelta content signals (code change, F5, SplitLeadTime)—not internal helper call order or private score intermediates.

2. **Primary seam under test:** `generar_pedido` / GenerarResult with injected DataFrames (catalog, market offers, stock, optional backorder, lead times, nullable MOQ)—pattern pioneered by the offline CSV harness used for optimizer dry runs. No requirement that first tests hit HTTP or live SQL.

3. **Secondary pure tests:** GapExtensionOferta formula (including non-offer rotation-weighted f); SplitLeadTime trigger / min-to-fast / remainder-to-cheap / stock cap / nullable MOQ; DemandaGrupal gaps under alternate CriteriosAgrupacion lists.

4. **Fixture cases (minimum):** (a) Conservador near-Baseline; (b) sucedáneo BARRA change within Grupo; (c) F5 reinforces only offer SKUs with intermediate Gap_ext; (d) SplitLeadTime fires and does not fire; (e) Backorder equal subtraction; (f) CriteriosAgrupacion override changes Grupo membership and both sides.

5. **Prior art:** offline CSV injection scripts around group gap + distribute_within_group; exploratory compare scripts for order diffs. Prefer consolidating into proper automated tests against the new seam rather than growing ad-hoc scripts. Repo `tests/` is mostly empty for pedidos—greenfield for this feature’s suite is expected.

6. **Parity note:** Baseline vs historic Motor B sampling is a valid golden check; Propuesto is **not** required 1:1 BARRA or qty vs Baseline (ADR-0005/0006).

## Out of Scope

- Reactivating S4 coverage reduction or sustitución kappa / quadratic_ceiling in Pedido schema/UI.
- Full Matriz de Decisión product (explicitly avoided in CONTEXT).
- Mandating subtraction_files for P1 parity.
- Exact Intermedio vs Avanzado UI control inventory (only Sencillo + “can regenerate with Intermedio/Avanzado” is closed).
- Fixed copy template for JustificacionDelta (multi-factor required; wording plantilla not closed).
- Choosing/creating the physical MOQ table/column beyond nullable plumbing (P1 decision).
- Naming discovery of Backorder tables beyond “dedicated backend tables” (P1).
- Performance vectorization of scoring loops (historical FASE 3 notes)—not part of this product unification spec.
- Rewriting the optimizer as PuLP/ILP from scratch.
- Chatwoot / CRM / unrelated Synapse modules.

## Further Notes

- Grill closed with shared understanding; do not re-open: Necesidad vs Pedido; Baseline without motor; Comparativa grain B; F5 only reinforces offers; SplitLeadTime D+C; presets A; MOQ=B location=C—without explicit user reopen.
- ADR-0003 is superseded for in-Pedido substitution by ADR-0005; kappa isolation still stands until calibration.
- ADR-0001 remains “converge on one motor pipeline” but the Baseline story from grill **overrides** treating Lineal-inside-v3.2 as Baseline.
- Next skill after this PRD: `/to-tickets` (tracer bullets with blocking edges), then `/implement` per ticket in clean sessions.
- Suggested scratch layout for tickets: `.scratch/parametrizacion-pedidos/issues/NN-*.md`.
