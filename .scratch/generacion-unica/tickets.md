# Tickets: Generación única de pedidos

Source: `.scratch/generacion-unica/PRD.md`  
Seams: batch `generar_pedido_batch`, regenerar activo, ValidarMinimos post-elección, grilla FE.  
Work the **frontier**: any ticket whose blockers are all done.

ADR/CONTEXT amend is **last** (after the productive path ships).

## Batch engine: Baseline once + ≤3 perfiles

**What to build:** From the engine seam, one shared PedidoBaseline plus up to three perfil GenerarResults (same ComparativaCantidades + PedidoPropuesto shape as today), with fixture proof that Baseline BARRAs/qty are identical across perfiles.

**Blocked by:** None — can start immediately.

**Status:** resolved (see `issues/01-batch-engine-baseline-once.md`)

- [x] `generar_pedido_batch` (or equivalent) accepts shared filtros + ≤3 perfil descriptors
- [x] PedidoBaseline is computed once and reused; no per-perfil re-sample
- [x] Each perfil returns a GenerarResult compatible with current Comparativa/Propuesto consumers
- [x] Fixtures assert shared Baseline anchors and distinct Propuesto totals across perfiles

## Batch HTTP API

**What to build:** An HTTP surface that exposes the batch contract so the productive FE can load Baseline + perfiles in one Generar action (single batch POST or orchestrated calls with injected/cached Baseline — choice documented in the issue comments).

**Blocked by:** Batch engine: Baseline once + ≤3 perfiles

**Status:** resolved (see `issues/02-batch-http-api.md`)

- [x] API returns `{ PedidoBaseline, perfiles: [{ id, label, knobs_efectivos, GenerarResult }] }` (shape may nest Baseline inside meta; FE can parse it)
- [x] Callers cannot get three independent full Generars that re-sample Baseline
- [x] Catalog/offers/backorder load is not tripled wastefully when using DB path
- [x] Error handling fails the batch coherently (no silent half-grids)

## Knob `rivales_ofertas_por_rival` + schema

**What to build:** Preset/knob schema gains `rivales_ofertas_por_rival` (default 2); `hermanos_top_n` / `rivales_top_n` remain default 3 with existing clamp behaviour.

**Blocked by:** None — can start immediately.

**Status:** resolved (see `issues/03-knob-rivales-ofertas-por-rival.md`)

- [x] Knob exists on PresetKnobs (or successor) with default 2 and clamp range
- [x] Overrides schema / overrides-schema consumers expose the new knob
- [x] Factory presets do not break; missing key resolves to default 2
- [x] Unit tests cover clamp and default

## Config Pedido UI: hermanos / rivales / ofertas por rival

**What to build:** Config Pedido lets the comprador set `hermanos_top_n`, `rivales_top_n`, and `rivales_ofertas_por_rival` with the agreed defaults visible.

**Blocked by:** Knob `rivales_ofertas_por_rival` + schema

**Status:** resolved (see `issues/04-config-pedido-knobs-ui.md`)

- [x] Three controls visible in Config Pedido (not buried only in Avanzado dump)
- [x] Defaults shown: 3 / 3 / 2
- [x] Values flow into the next Generar/batch request knobs
- [x] Invalid input is clamped or rejected with clear FE feedback

## Payload hermanos + rivales honors knobs

**What to build:** Comparativa/justificación (or adjacent payload) carries Original/hermanos and Rivales offer rows sized by `hermanos_top_n`, `rivales_top_n`, and `rivales_ofertas_por_rival`, enough for the replacement modal without a second market fetch.

**Blocked by:** Knob `rivales_ofertas_por_rival` + schema

**Status:** resolved (see `issues/05-payload-hermanos-rivales.md`)

- [x] Each rival can include up to `rivales_ofertas_por_rival` offers (desc, proveedor, precio)
- [x] Hermanos capped by `hermanos_top_n`; rivales by `rivales_top_n`
- [x] Fixture/assert cardinality changes when knobs change
- [x] No live Mercado round-trip required to open the modal for data already on the row

## FE Generar → batch + grilla `N (Δ −86)`

**What to build:** Primary Generar calls the batch API and shows a results grid of perfiles with totals formatted `N (Δ −86)` vs PedidoBaseline — no top proveedor, no Δ-knobs/variables card.

**Blocked by:** Batch HTTP API

**Status:** resolved (see `issues/06-fe-grilla-batch-delta.md`)

- [x] One Generar action loads Baseline + ≤3 perfiles into session state
- [x] Grid shows per-perfil total as `N (Δ −86)` (sign and spacing per grill)
- [x] Grid omits top proveedor summary
- [x] Grid omits Δ knobs / variables card
- [x] Perfil slots reflect factory + custom pool selection agreed in config (up to 3)

## FE clic columna → Comparativa única

**What to build:** Clicking a perfil column hydrates the single ComparativaCantidades (and related summary) from that slot only.

**Blocked by:** FE Generar → batch + grilla `N (Δ −86)`

- [ ] Column click sets the active perfil in session
- [ ] Comparativa table/body renders that perfil’s GenerarResult
- [ ] Switching columns swaps Comparativa without re-running the batch
- [ ] Baseline columns remain the shared PedidoBaseline

## Justificaciones: nombre + proveedor + precio

**What to build:** Primary JustificacionDelta presentation shows product name + proveedor + precio; BARRA detail is secondary.

**Blocked by:** FE clic columna → Comparativa única

- [ ] Primary cell/summary line is commercially readable (nombre, proveedor, precio)
- [ ] BARRA appears as secondary detail (hover/acordeón/secondary line)
- [ ] Structured `justificacion_factores` model from ADR-0019 is not flattened away
- [ ] Sucedáneo / code-change cases still declare the change

## Modal clic-derecho Original | Rivales

**What to build:** Right-click on a propuesta BARRA opens a modal with Original | Rivales blocks (desc + proveedor + precio) driven by knob-sized payload; comprador can apply a replacement on the active Comparativa.

**Blocked by:** Config Pedido UI: hermanos / rivales / ofertas por rival; Payload hermanos + rivales honors knobs; FE clic columna → Comparativa única

- [ ] Context menu / right-click on propuesta BARRA opens the modal
- [ ] Blocks show Original (hermanos/original) and Rivales with required commercial fields
- [ ] Offer counts respect the three knobs
- [ ] Applying a choice updates the active perfil Comparativa/Propuesto line coherently
- [ ] Left-click behaviour of the grid/Comparativa remains unchanged

## Comparador vertical + re-gen solo activo

**What to build:** Vertical comparator card for the active perfil with Intermedio|Avanzado; regenerar updates only that slot and re-hydrates Comparativa; shared PedidoBaseline and sibling slots stay put.

**Blocked by:** FE clic columna → Comparativa única

- [ ] Comparator card shows the active perfil summary
- [ ] Dropdown Intermedio|Avanzado (and overrides as today) available on the card
- [ ] Regenerar calls existing definitivo path against the active slot only
- [ ] Sibling batch resultados unchanged after re-gen
- [ ] PedidoBaseline in session unchanged after re-gen

## ValidarMinimos post-elección → alarma → modal

**What to build:** After choosing a perfil, an alarm/CTA offers ValidarMinimosProveedor; opening it runs the existing mínimo flow on that perfil only — never inline as part of batch completion.

**Blocked by:** FE clic columna → Comparativa única

- [ ] Batch completion does not force ValidarMinimos UI
- [ ] After profile selection, alarm/banner + button appear when mínimos apply
- [ ] Button opens the existing modal/panel flow (cola, %, Aceptar/Rechazar)
- [ ] Evaluar operates on the active perfil GenerarResult only
- [ ] ADR-0016 behaviours preserved

## Guardar v1 solo perfil elegido

**What to build:** Guardar persists only the active/chosen perfil (BorradorPedidos / PedidoDefinitivo path); batch siblings are not auto-saved.

**Blocked by:** FE clic columna → Comparativa única

- [ ] Guardar disabled or no-ops until a perfil is chosen
- [ ] Only the chosen perfil’s lines/knobs/Comparativa snapshot are persisted
- [ ] No second/third borrador created for sibling slots
- [ ] Knobs snapshot matches the chosen (possibly re-gen’d) perfil

## Retirar UI vieja Sencillo → Regenerar duplicado

**What to build:** Remove the primary-path duplicate Generar Sencillo → Regenerar Definitivo workflow from the productive page so generación única is the happy path; leave prototype_compare_presets artifacts untouched.

**Blocked by:** FE clic columna → Comparativa única; Comparador vertical + re-gen solo activo; ValidarMinimos post-elección → alarma → modal; Guardar v1 solo perfil elegido

- [ ] Primary UI no longer presents the old serial Sencillo-then-only-Regenerar compare story as the main path
- [ ] New Generar → grilla → Comparativa → comparador/mínimos/guardar path remains reachable
- [ ] `prototype_compare_presets.js`, `.wf3.js`, and NOTES are not deleted
- [ ] Smoke: one full happy path without using retired controls

## Enmendar ADR-0007 + CONTEXT

**What to build:** After the productive path ships, amend ADR-0007 (and CONTEXT Pedido / PerfilPedido wording) so domain docs match generación única: first Generar may run ≤3 perfiles; Baseline fixed/shared; Intermedio/Avanzado re-gen remains per active perfil.

**Blocked by:** Retirar UI vieja Sencillo → Regenerar duplicado

- [ ] ADR-0007 updated or superseded with explicit status and link to this PRD
- [ ] CONTEXT.md Pedido / PerfilPedido / PedidoPropuesto Avoid lines no longer mandate single-Sencillo-only first Generar
- [ ] PedidoBaseline “sin motor” and Comparativa grain (ADR-0004) remain intact in docs
- [ ] No silent contradiction left between ADR-0007 and shipped UI
