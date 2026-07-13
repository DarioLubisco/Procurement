# Tickets: Parametrización unificada de pedidos

Tracer bullets para el Generar unificado (PedidoBaseline + PedidoPropuesto + ComparativaCantidades). Spec: `.scratch/parametrizacion-pedidos/PRD.md`.

Status: ready-for-agent

Work the **frontier**: any ticket whose blockers are all done. For a purely linear chain that means top to bottom.

## PedidoBaseline extraíble + parity en fixtures

**What to build:** Dado Cobertura, FiltrosOperativos y CriteriosAgrupacion, el sistema produce un PedidoBaseline (rotación × cobertura − stock) verificable offline, sin motor, sin PriceOpportunity ni LeadTime.

**Blocked by:** None — can start immediately.

- [x] Baseline qty matches legacy formula on fixture catalog for given Cobertura
- [x] FiltrosOperativos (categorías, genéricos/marcas, umbral, tope de líneas) restrict the sampled universe
- [x] Baseline lines include BARRA, descripción, cantidad (no proveedor)
- [x] No PriceOpportunity, pesos, SplitLeadTime, or F5 applied to Baseline

## Seam `generar_pedido` → GenerarResult (Baseline real + stubs)

**What to build:** Un solo contrato de orquestación `generar_pedido(PerfilPedido) → GenerarResult` que ya devuelve PedidoBaseline real más Propuesto/Comparativa en forma stub o identidad, inyectable sin HTTP/SQL vivos.

**Blocked by:** PedidoBaseline extraíble + parity en fixtures

- [x] `PerfilPedido` accepts cobertura, criterios_agrupacion, filtros_operativos, nivel, preset?, presupuesto_maximo?
- [x] `GenerarResult` exposes pedido_baseline, pedido_propuesto, comparativa_cantidades
- [x] Baseline in the result matches the extracted Baseline calculator on the same inputs
- [x] Fixture harness can call the seam without live DB

## CriteriosAgrupacion efectivos en DemandaGrupal y Baseline

**What to build:** La lista efectiva del request (default sistema: PA, FF, conc, cantidad_presentacion, contenido_neto) agrupa DemandaGrupal y PedidoBaseline; deja de mandar Molécula hardcodeada de tres attrs.

**Blocked by:** Seam `generar_pedido` → GenerarResult (Baseline real + stubs)

- [x] Request criterios_agrupacion changes Grupo membership for Baseline aggregation
- [x] Default five-attribute set used when no override provided
- [x] DemandaGrupal / gaps use the same effective list as Baseline
- [x] Hardcoded PA+FF+conc-only path is no longer the runtime authority

## Preset Conservador → Propuesto + ComparativaCantidades básica

**What to build:** Primer Generar Sencillo con PresetSencillo Conservador: PedidoPropuesto con proveedor, ComparativaCantidades anclada a BARRA Baseline, deltas mínimos vs Baseline, JustificacionDelta al menos por cantidad.

**Blocked by:** Seam `generar_pedido` → GenerarResult (Baseline real + stubs); CriteriosAgrupacion efectivos en DemandaGrupal y Baseline

- [x] Conservador maps to ADR-0010 knobs (amplifier off, ext_max_dias_extra 0, pesos almost only posicionamiento, soft LeadTime low)
- [x] Propuesto lines include proveedor and cantidad
- [x] Comparativa has one row per Baseline BARRA with qty Baseline and qty Propuesto
- [x] Controlled fixtures show near-minimal delta vs Baseline under Conservador
- [x] Optional presupuesto_maximo is accepted on Sencillo without requiring Avanzado

## DistribucionParcial multi-factor + sucedáneos en Comparativa

**What to build:** Cuotas parciales por línea Baseline según el motor completo (no winner-takes-all, no solo elasticidad); Propuesto puede usar otra BARRA del mismo Grupo; JustificacionDelta declara cambio de código cuando hay sucedáneo.

**Blocked by:** Preset Conservador → Propuesto + ComparativaCantidades básica

- [x] Within a Grupo, multiple Baseline lines can receive partial Propuesto quotas
- [x] Elasticidad alone does not dictate allocation when other motor factors conflict (e.g. LeadTime soft / price)
- [x] Propuesto may resolve a Grupo need with a different BARRA from mercado vivo
- [x] JustificacionDelta states code change when barra_propuesto ≠ barra_baseline
- [x] Comparativa qty_propuesto is the line quota, not the entire Grupo gap dumped on one row

## GapExtensionOferta (F5)

**What to build:** ExtensionCobertura dispara por Desvío bajo umbral; unidades extra refuerzan solo productos en oferta; tamaño Gap_ext = Gap_oferta + (Gap_grupo − Gap_oferta) × f con f ponderado por elasticidad×rotación entre no-oferta; JustificacionDelta audita f.

**Blocked by:** DistribucionParcial multi-factor + sucedáneos en Comparativa

- [ ] F5 does not add coverage days to non-offer Grupo members
- [ ] F5 does not dump the full Gap_grupo onto offer SKUs
- [ ] Gap_ext uses non-offer-only rotation denominator for f
- [ ] Fixture matching ADR-0012 example semantics passes
- [ ] JustificacionDelta mentions F5 / f when extension applied

## SplitLeadTime + MOQ nullable

**What to build:** Si Existen < rotación_diaria × LT del proveedor rápido, mínimo al rápido = max(rot×LT, MOQ_proveedor?) topeado por stock_proveedor de esa oferta; resto al más barato; si Existen ya cubre rot×LT, no forzar mínimo; MOQ nullable sin usar SAPROD.Minimo; JustificacionDelta explica el split.

**Blocked by:** DistribucionParcial multi-factor + sucedáneos en Comparativa

- [ ] Split fires only when Existen < rot × LT_fast
- [ ] Fast leg qty = max(rot×LT, MOQ) when MOQ present, else rot×LT, capped by offer stock
- [ ] Remainder goes to cheapest worse-LT supplier
- [ ] No forced fast minimum when Existen already covers rot×LT
- [ ] PedidoPropuesto can show 2+ lines same product different proveedores
- [ ] Missing MOQ does not block; SAPROD.Minimo is never used as MOQ

## Presets Normal y Agresivo

**What to build:** PresetSencillo Normal y Agresivo mapeados a ADR-0011/0013; en fixtures se distinguen de Conservador (amplifier/F5/pesos/split según preset).

**Blocked by:** Preset Conservador → Propuesto + ComparativaCantidades básica; GapExtensionOferta (F5); SplitLeadTime + MOQ nullable

- [ ] Normal maps to ADR-0011 (calibrated amp/F5/pesos, medium soft LeadTime)
- [ ] Agresivo maps to ADR-0013 (stronger amp/F5/price pesos; SplitLeadTime-aware)
- [ ] Same fixture inputs yield materially different Propuesto/Comparativa across the three presets
- [ ] Baseline remains unchanged when only the preset changes

## Backorder desde tablas + resta igual en ambos lados

**What to build:** Backorder leído de tablas dedicadas del backend (schema a localizar/documentar en el ticket); misma resta en PedidoBaseline y PedidoPropuesto; subtraction_files no es requisito de paridad.

**Blocked by:** Seam `generar_pedido` → GenerarResult (Baseline real + stubs)

- [ ] Backorder source tables identified and documented
- [ ] Same backorder quantities subtract from Baseline and Propuesto
- [ ] Comparativa deltas are not polluted by one-sided backorder
- [ ] Happy path does not require subtraction_files

## API + FE Generar Sencillo (Comparativa + Propuesto con proveedor)

**What to build:** UI productiva Generar usa el seam unificado: muestra ComparativaCantidades y PedidoPropuesto con proveedor; permite Cobertura, FiltrosOperativos, CriteriosAgrupacion editables, PresetSencillo y presupuesto opcional. Excel BARRA×CANTIDAD deja de ser la salida humana primaria de esta fase.

**Blocked by:** DistribucionParcial multi-factor + sucedáneos en Comparativa; Presets Normal y Agresivo; Backorder desde tablas + resta igual en ambos lados

- [ ] Productive Generar calls unified path (not legacy-only Excel generator)
- [ ] Comprador sees Comparativa columns: Baseline BARRA/desc/qty, Propuesto BARRA/desc/qty, JustificacionDelta
- [ ] Comprador sees Propuesto with proveedor on first Generar
- [ ] First Generar UI is Sencillo only (preset + cobertura + filtros + criterios + optional budget)
- [ ] CriteriosAgrupacion editable before Generar; effective list sent on request

## Regenerar PedidoDefinitivo (Intermedio/Avanzado)

**What to build:** Tras la Comparativa, el comprador regenera con controles Intermedio o Avanzado; se refrescan PedidoPropuesto y ComparativaCantidades juntos hacia PedidoDefinitivo. Knobs muertos (S4, kappa) no reaparecen.

**Blocked by:** API + FE Generar Sencillo (Comparativa + Propuesto con proveedor)

- [ ] Regenerar is distinct from first Generar Sencillo in UX/language
- [ ] Intermedio/Avanzado regeneration returns updated Propuesto + Comparativa
- [ ] Dead S4 / kappa knobs are not exposed in Pedido profile UI
- [ ] Overrides that are in living OptimizerConfig can affect Definitivo output

## Deprecar forced_includes y Excel como artefacto primario

**What to build:** Camino feliz sin forced_includes; Excel mínimo BARRA×CANTIDAD ya no es la salida humana de la fase; subtraction_files queda solo como soporte eventual de contingencia.

**Blocked by:** API + FE Generar Sencillo (Comparativa + Propuesto con proveedor)

- [ ] forced_includes not required for Generar happy path
- [ ] Primary human artifact is Comparativa + Propuesto (not bare Excel two-column export)
- [ ] subtraction_files documented/treated as contingency only, not FiltroOperativo de primer nivel
