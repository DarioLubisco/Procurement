# Spec: Generación única de pedidos

Status: ready-for-agent

Feature: generacion-unica  
Sources: grill generación única (cerrado Sí), handoff `/tmp/handoff-ni63Aa.md`, `CONTEXT.md`, ADRs 0004/0007/0016/0018/0019 (reabrir 0007 en implementación)  
Seams agreed (2026-07-26):

1. **Primary (new):** `generar_pedido_batch(filtros_compartidos, perfiles[≤3]) → { PedidoBaseline, perfiles: [{ id, label, knobs_efectivos, GenerarResult }] }` — Baseline once, shared; each GenerarResult = ComparativaCantidades + PedidoPropuesto (same shape as today’s Sencillo). Transport may be one HTTP batch or 3× generar + cached baseline; tests bind to the contract.
2. **Re-gen (existing):** `regenerar_definitivo(nivel Intermedio|Avanzado, …) → GenerarResult` — mutates only the active profile; shared Baseline not recalculated.
3. **ValidarMinimosProveedor (existing, new timing):** same API/meta; fires after profile selection (alarm → modal), not inline in batch.
4. **FE choice:** post-Generar grid (`N (Δ −86)`, no top proveedor, no Δ-knobs card) → column click hydrates the single Comparativa + vertical comparator.

---

## Problem Statement

Hoy el comprador genera un PedidoPropuesto Sencillo (un preset), revisa la ComparativaCantidades contra PedidoBaseline, y luego regenera Definitivo con Intermedio/Avanzado. Eso obliga a un flujo serial y a “elegir preset a ciegas” antes de ver trade-offs. Además la UI mezcla el camino viejo Generar Sencillo → Regenerar Definitivo duplicado con la intención de comparar varios perfiles. El comprador necesita **una sola generación** que entregue Baseline fijo + varios perfiles en paralelo, elegir el perfil en una grilla, y solo entonces afinar o validar mínimos.

## Solution

Reestructurar Pedidos a **generación única**:

1. Un botón **Generar** calcula **PedidoBaseline** una vez (fijo, sin dropdown) y corre **hasta 3 perfiles** (presets de fábrica y/o custom del pool) con los mismos FiltrosOperativos / Cobertura / CriteriosAgrupacion / Backorder.
2. La salida primaria es una **grilla de resultados** por perfil con totales en forma `N (Δ −86)` respecto al Baseline — sin “versus”, sin top proveedor, sin card de Δ variables/knobs.
3. **Clic en columna** de un perfil hidrata la **ComparativaCantidades única** y el **comparador vertical** (card; dropdown Intermedio|Avanzado; re-gen solo del perfil activo).
4. **ValidarMinimosProveedor** se anuncia tras elegir perfil (alarma → botón → modal), no inline en el batch.
5. Reemplazo de línea: **clic derecho** en barra propuesta → modal bloques **Original | Rivales** (desc + proveedor + precio), con knobs `hermanos_top_n` (def 3), `rivales_top_n` (def 3), **`rivales_ofertas_por_rival` (def 2)** en Config Pedido.
6. Justificaciones: nombre + proveedor + precio primario; barra secundaria.
7. Guardar v1: solo el **perfil elegido**.
8. **Retirar** de la página principal el flujo duplicado Generar Sencillo → Regenerar Definitivo (sin borrar prototipos `prototype_compare_presets*`).

## User Stories

1. As a comprador, I want a single Generar to produce PedidoBaseline plus up to three perfiles, so that I can compare strategies without serial re-runs.
2. As a comprador, I want PedidoBaseline fixed (not a dropdown choice), so that every perfil is measured against the same rotación reference.
3. As a comprador, I want Baseline computed once and shared across perfiles, so that deltas are not polluted by sampling drift.
4. As a comprador, I want to pick which perfiles run from the factory PresetSencillo pool and my custom presets, so that the three slots match how I work.
5. As a comprador, I want Cobertura, FiltrosOperativos, CriteriosAgrupacion and Backorder shared across the batch, so that only perfil knobs differ.
6. As a comprador, I want a results grid after Generar, so that I can scan totals before opening detail.
7. As a comprador, I want each perfil total shown as `N (Δ −86)` vs Baseline, so that savings/cost are scannable without verbose “versus” copy.
8. As a comprador, I want no top-proveedor summary on the results grid, so that the grid stays about totals and deltas.
9. As a comprador, I want no Δ-knobs / variables card on the post-Generar grid, so that I am not distracted by knob diffs before choosing a perfil.
10. As a comprador, I want clicking a perfil column to hydrate the single ComparativaCantidades view, so that I drill into one candidate at a time.
11. As a comprador, I want the Comparativa to keep BARRA Baseline anchoring and Propuesto with proveedor, so that domain meaning from ADR-0004 stays intact.
12. As a comprador, I want a vertical comparator card for the active perfil, so that I can see that perfil’s summary without a second page.
13. As a comprador, I want Intermedio|Avanzado on the comparator to re-generate only the active perfil, so that other batch perfiles stay as first-pass references.
14. As a comprador, I want shared PedidoBaseline unchanged when I re-gen the active perfil, so that Δ language stays honest.
15. As a comprador, I want ValidarMinimosProveedor to appear only after I choose a perfil (alarm → button → modal), so that I do not resolve mínimos for three perfiles at once.
16. As a comprador, I want the existing ValidarMinimosProveedor behaviours (cola, %, Aceptar/Rechazar) on the chosen perfil, so that ADR-0016 still applies.
17. As a comprador, I want right-click on a propuesta BARRA to open a replacement modal with Original | Rivales blocks, so that I can swap without leaving Comparativa.
18. As a comprador, I want each rival block to show descripción, proveedor and precio, so that I can decide replacements commercially.
19. As a comprador, I want `hermanos_top_n` default 3 in Config Pedido, so that sibling BARRAs are bounded.
20. As a comprador, I want `rivales_top_n` default 3 in Config Pedido, so that rival offers are bounded.
21. As a comprador, I want `rivales_ofertas_por_rival` default 2 in Config Pedido, so that each rival can show more than one offer without flooding the modal.
22. As a comprador, I want JustificacionDelta primary line to show product name + proveedor + precio, so that the main cell is commercially readable.
23. As a comprador, I want secondary BARRA detail in JustificacionDelta, so that code changes remain auditable without crowding the primary line.
24. As a comprador, I want Guardar (v1) to persist only the chosen perfil as PedidoDefinitivo/BorradorPedidos, so that I do not save three drafts by accident.
25. As a comprador, I want the old Generar Sencillo → Regenerar Definitivo duplicate primary UI retired, so that there is one happy path.
26. As a comprador, I want prototype compare-presets artifacts left in the repo for later recycle, so that Alt1/Alt2/WF3 work is not lost.
27. As a procurement engineer, I want batch orchestration tested at `generar_pedido_batch` (or equivalent), so that Baseline-once + N perfiles is one contract regardless of HTTP shape.
28. As a procurement engineer, I want each perfil GenerarResult to reuse today’s Comparativa + Propuesto shape, so that FE hydration and PDF/Bandeja adapters stay stable.
29. As a procurement engineer, I want regenerar_definitivo to target only the active perfil state in the session, so that batch siblings are not overwritten.
30. As a QA engineer, I want fixtures asserting one Baseline qty set shared by three perfiles with distinct Propuesto totals, so that shared-baseline is regression-proof.
31. As a QA engineer, I want tests that ValidarMinimos is not invoked by batch completion alone, so that timing regressions are caught.
32. As a QA engineer, I want UI/contract tests that grid delta formatting is `N (Δ −86)` and omits top proveedor and Δ-knobs, so that grill UI rules stick.

## Implementation Decisions

- **Orchestration:** Introduce `generar_pedido_batch` (name flexible) as the primary seam. Inputs: shared filtros (cobertura, CriteriosAgrupacion, FiltrosOperativos, presupuesto opcional si aplica al batch, catalog/offers/backorder injection), plus an ordered list of up to 3 perfil descriptors (factory PresetSencillo name and/or custom preset id + resolved knobs). Output: one PedidoBaseline + array of perfil results each with id, label, effective knobs, and GenerarResult.
- **Baseline once:** Sampling + PedidoBaseline runs a single time; each perfil motor run consumes that Baseline (and shared market/catalog/backorder). Do not re-sample per perfil.
- **HTTP:** Prefer either (a) one `POST` batch endpoint returning the full payload, or (b) FE/orchestrator that computes Baseline once then fans out 3× existing generar with injected baseline. Choose the option that keeps the batch seam testable without duplicating DB load; document the choice in the implementing ticket. Callers and tests must not depend on “three independent full Generars” for Baseline equality.
- **Re-gen:** Keep `POST /regenerar-definitivo` (or successor) for Intermedio/Avanzado on the **active** perfil only. Session/UI state holds the three first-pass results; re-gen replaces only the active slot’s GenerarResult and re-hydrates Comparativa. PedidoBaseline in session stays put.
- **ValidarMinimos:** No change to core ValidarMinimosProveedor contract; UI gating moves to post-selection. Batch response must not require mínimos resolution to complete.
- **Config knobs:** Expose `hermanos_top_n` (default 3), `rivales_top_n` (default 3), and new `rivales_ofertas_por_rival` (default 2) on Config Pedido / preset schema as appropriate; clamp ranges consistent with existing top-N helpers.
- **Replacement modal:** Right-click on propuesta BARRA → modal sections Original | Rivales; content driven by hermanos/rivales data already (or newly) attached to Comparativa/justificación payloads — extend payload only as needed for `rivales_ofertas_por_rival`.
- **Justificaciones:** Primary display = nombre + proveedor + precio; secondary = BARRA. Align with ADR-0019 structured factors; adjust presentation, not the multi-factor model.
- **Guardar v1:** Persist only the chosen perfil (BorradorPedidos / PedidoDefinitivo path per ADR-0018). Do not auto-save batch siblings.
- **UI retirement:** Remove primary-path controls that force “pick one Sencillo preset → Generar → later Regenerar Definitivo as the only compare story.” Do not delete `frontend/js/prototype_compare_presets.js`, `.wf3.js`, or NOTES — recycle later.
- **Domain / ADR:** This flow **contradicts ADR-0007** (“first Generar = Sencillo only; Intermedio/Avanzado only on regenerate”) insofar as three Sencillo (or preset-equivalent) perfiles run on first Generar. Implementation must amend or supersede ADR-0007 (and update CONTEXT.md Pedido / PerfilPedido wording) via `/grill-with-docs` or a focused ADR update in the same effort — do not silently diverge.
- **Glossary pressure:** Consider adding terms if needed when docs are updated: e.g. batch first-pass “perfiles de generación” vs PedidoDefinitivo; keep PedidoBaseline / ComparativaCantidades / ValidarMinimosProveedor vocabulary as-is.

## Testing Decisions

- Prefer testing **external behaviour** at the highest agreed seam (`generar_pedido_batch`), not internal HTTP fan-out details.
- Assert: one Baseline; N≤3 perfiles; each GenerarResult shape compatible with current Comparativa + Propuesto consumers; Baseline BARRAs/qty identical across perfiles’ Comparativa anchors.
- Assert: regenerar on active perfil leaves sibling slots and Baseline unchanged.
- Assert: ValidarMinimos not required to finish batch; can run on chosen perfil GenerarResult.
- Assert: knob `rivales_ofertas_por_rival` affects rival offer cardinality in replacement payload/modal data.
- Prior art: `.scratch/parametrizacion-pedidos` tickets / `tests/analytics/` for generar_sencillo, validar_minimos, presets; FE patterns in `app_pedidos.js` Comparativa + mínimos panels.
- Good tests: fixture-driven, no live DB for core batch invariants; avoid asserting ephemeral CSS class names unless a dedicated UI contract test exists.

## Out of Scope

- Redesigning Wireframe 3 / Alt1–Alt2 preset comparison prototypes as the primary UX (may recycle later).
- Saving all three perfiles or multi-draft Guardar.
- Showing top proveedor or Δ-knobs on the results grid.
- Re-running ValidarMinimos inline for every batch perfil.
- Deleting prototype_compare_presets artifacts.
- Changing EnvioPedidos / BandejaPedidos / FTP ACK flows beyond “Guardar only chosen perfil.”
- Reopening the preset UI grill except where this spec’s knobs/modal require it.

## Further Notes

- Grill generación única is **closed**; do not re-litigate UI preset wireframes.
- Implement via tracer tickets (`/to-tickets` → `/implement` one frontier ticket at a time).
- Prototypes under `frontend/js/prototype_compare_presets*.js` are secondary; productive FE is `modulo_pedidos` + `app_pedidos.js`.
- When amending ADR-0007 / CONTEXT, keep PedidoBaseline “sin motor” and Comparativa grain rules from ADR-0004 intact.
