# Procurement — Generación de Pedidos

Vocabulario de dominio para el motor de pedidos y su parametrización en Synapse-Procurement.
Fuente de diseño: `docs/intent/propuesta_parametrizacion_unificada.md` (original) y
`docs/intent/propuesta_parametrizacion_unificada_enmiendas_2026-07-10.md` (enmiendas).

## Language

**Necesidad:**
Cantidades a reponer por producto, sin asignar proveedor. Identidad técnica: código de barras (BARRA). Presentación al comprador: descripción del producto. El muestreo sale de los FiltrosOperativos + rotación.
_Avoid_: Pedido, export de solo dos columnas como única salida de UI

**PedidoBaseline:**
Cantidades **solo con rotación × cobertura − stock**, **sin motor de scoring**. La rotación/stock se agregan con los **mismos CriteriosAgrupacion** de la corrida (default: PA+FF+conc+cantidad_presentacion, o los editados en el FE). Comparte Cobertura y FiltrosOperativos; no aplica PriceOpportunity, pesos ni LeadTime.
_Avoid_: Baseline en rotación SKU mientras Propuesto usa Grupo de 5 attrs; aplicar amplificador al Baseline; llamar “perfil Lineal v3.2” al Baseline

**CriteriosAgrupacion:**
Lista de atributos MDM que definen el Grupo (whitelist `ATRIBUTOS_VALIDOS` / `RotacionGrupal_Atributos`, 10 campos). Default de sistema: `principio_activo`, `forma_farmaceutica`, `concentracion`, `cantidad_presentacion` — **no** incluye `contenido_neto` (ml/g; opcional en FE). Sobreescribible en el FE (subconjunto no vacío). El request siempre envía la lista efectiva; el catálogo carga los attrs de la whitelist. Ver ADR-0008 + ADR-0020.
_Avoid_: criterios_agrupamiento ignored del v3.2; mostrar attrs en FE sin columnas en catálogo; aceptar attrs fuera de whitelist; solo PA+FF+conc hardcodeado; Baseline SKU vs Propuesto grupal; default solo en localStorage sin default de sistema

**PedidoPropuesto:**
Primera salida del motor (mercado vivo, DistribucionParcial). Perfil **Sencillo**: preset + Cobertura + FiltrosOperativos + presupuesto opcional. Puede usar otras BARRAs del mismo Grupo. En el primer Generar se entrega **junto con** la ComparativaCantidades, con asignación a **proveedor**.
_Avoid_: Pedido definitivo; ocultar proveedor hasta el Definitivo; Intermedio obligatorio en el primer Generar

**PedidoDefinitivo:**
Regeneración tras ver la Comparativa y ajustar parámetros **Intermedio o Avanzado** (u overrides).
_Avoid_: Llamar “definitivo” al primer pase Sencillo

**Pedido:**
Asignación de Necesidad a ofertas de mercado. Flujo: Baseline (legacy, sin motor) → Propuesto (Sencillo) → Definitivo (reafinación Intermedio/Avanzado) vía ComparativaCantidades.
_Avoid_: Matriz de Decisión (no implementada)

**Elasticidad:**
Atributo de producto en escala 0–5 (`elasticidad_demanda`) que indica cuánto puede ceder/reemplazarse demanda dentro del Grupo. Suele ser menor que 5, así que no hay sustitución total a un solo ganador. Es **un input más** del motor, no el árbitro único del Propuesto.
_Avoid_: tratar elasticidad como única causa del delta; asumir elasticidad=5 como caso normal; gatillo S4 `elasticidad==0` como uso principal

**MontoMinimoPedidoUSD:**
Piso comercial en dólares por proveedor (`ProveedorConfig.MontoMinimoPedidoUSD`, nullable). No es `SAPROD.Minimo` ERP.
_Avoid_: confundir con MOQ en unidades del SplitLeadTime

**MOQ (unidades):**
Cantidad mínima por oferta en SplitLeadTime: `max(rot×LT, MOQ)` si viene en la oferta; nullable. Distinto de MontoMinimoPedidoUSD.
_Avoid_: usar SAPROD.Minimo; tratar el mínimo USD como uds sin conversión explícita

**ValidarMinimosProveedor:**
Paso explícito post-Generar. Proveedores bajo `MontoMinimoPedidoUSD` en **cola serie** (mayor déficit USD primero). Modal % extra (default +50%) → recálculo solo sus SKUs. Tras 1er fallo: panel (ahorro, costo rechazo, reemplazos Grupo) antes de más %; Aceptar / Rechazar / Probar otro % (ilimitado). Rechazo reasigna (barra→Grupo) o huérfano y **re-encola** destinos bajo mínimo. Trazas: `JustificacionDelta` por línea **y** `meta.validar_minimos`. `NULL` config = omitir.
_Avoid_: mutar cobertura en el primer Generar; inventar qty para llegar a $; sin traza en Comparativa

**LeadTime (LT):**
Tiempo de despacho/entrega del proveedor (días/horas). Ver SplitLeadTime.
_Avoid_: confundir con Cobertura

**SplitLeadTime:**
Partir la compra del mismo producto entre proveedores. **Disparo:** Existen (stock farmacia) menor que `rotación_diaria × días_LeadTime` del proveedor rápido. **Mínimo al rápido:** `max(rot×LT, MOQ si existe)`, topeado por `stock_proveedor` de esa oferta. **Resto** al más barato (LeadTime malo). Si Existen ya cubre rot×LT, no forzar mínimo al rápido.
_Avoid_: todo-al-más-barato; todo-al-más-rápido; usar solo stock_proveedor para el disparo; mínimo sin tope de stock de oferta

**DistribucionParcial:**
Cada línea Baseline del Grupo recibe/cede cuota del PedidoPropuesto según el **motor completo** (Elasticidad, PriceOpportunity, pesos, presupuesto, LeadTime/SplitLeadTime, stock, F5/GapExtensionOferta, etc.) sin dejar factores fuera.
_Avoid_: prorrateo ciego; winner-takes-all; “solo elasticidad”; delta monocausal

**ComparativaCantidades:**
Artefacto de primer pase (grano: fila por BARRA Baseline). Convive en el mismo Generar con el PedidoPropuesto (líneas con proveedor). Columnas: BARRA/desc Baseline, BARRA/desc Propuesto, qty Baseline, qty Propuesto (editable FE, override local), JustificacionDelta (multi-factor). Drawer de contexto al editar qty (demanda/stock/BO/grupo/competencia). Ver ADR-0004, ADR-0027.
_Avoid_: Matriz de Decisión; Excel solo BARRA×CANTIDAD; primer Generar sin ver proveedor; delta monocausal; re-correr motor en cada flecha de qty

**JustificacionDelta:**
Explica el delta Baseline vs Propuesto con **factores estructurados** (`justificacion_factores`) + resumen corto en celda (`justificacion_delta`). Hover/acordeón muestran detalle. Ver ADR-0019.
_Avoid_: texto que no declare cambio de código cuando hubo sucedáneo; concatenar ValidarMinimos al string sin factor

**Grupo:**
Conjunto de productos equivalentes según **CriteriosAgrupacion** activos. Mercado vivo puede ofertar sucedáneos del mismo Grupo; Baseline y Propuesto no tienen por qué compartir BARRA.
_Avoid_: usar “grupo” y Molécula como sinónimos sin declarar criterios; R2 ambiguo; asumir siempre solo PA+FF+conc

**Molécula:**
Caso histórico de Grupo = PA + FF + concentración. Ya no es el único default de negocio (ver CriteriosAgrupacion).
_Avoid_: cluster, R2 (ambiguo)

**FiltrosOperativos:**
Filtros base del **muestreo** evaluado por rotación (universo Baseline/Necesidad): categorías, genéricos/marcas, umbral de rotación, tope de líneas. No garantizan el mismo set de BARRAs en el Propuesto. Las restas por Excel (`subtraction_files`) **no** son filtro base de esta fase.
_Avoid_: forced_includes (deprecado); subtraction_files como requisito de paridad; “modo lineal” como si bastara amp=1

**Backorder:**
Cantidades ya comprometidas / en tránsito / pendientes desde **tablas dedicadas en el backend**. Se resta en **Baseline y Propuesto** por igual (mismo dato), para que la ComparativaCantidades no mezcle tránsito con efecto del motor.
_Avoid_: subtraction_files como fuente primaria; restar backorder solo a un lado de la Comparativa; confundir con BorradorPedidos

**BorradorPedidos:**
Persistencia explícita del **PedidoDefinitivo** (y propuestas IA) en `BorradorPedidosCabecera`/`Lineas` (1 cabecera por CodProv canónico), con snapshot de knobs en `ParametrosJson` y Comparativa en tabla hija (`BorradorPedidosComparativa` + `Revision`/`Hash`). No resta necesidad ni alimenta Generar. Ver ADR-0018. Envío: ADR-0029. Bandeja/TTL/análisis: ADR-0030.
_Avoid_: usar Borrador como Backorder; auto-guardar en cada Regenerar; Guardar desde Sencillo; olvidar knobs o snapshot Comparativa; celebrar envío sin ACK FTP/API; purgar `ENVIADO`

**EnvioPedidos:**
Pipeline único: Borrador (`PropuestaID`) → aprobación (FE Enviar o Telegram AMC_Administrativo) → n8n FTP/API (3×3=9, backoff largo entre ciclos) → ACK → `ENVIADO`/`FALLIDO_ENVIO`. PDF con sección exhaustiva de desvíos vs Sencillo. P1 solo labs con formato documentado. Ver ADR-0029 + ADR-0030.
_Avoid_: segundo approve en Telegram tras Enviar FE; payload embebido como fuente de verdad; inventar TXT de Nena/ITS sin spec; notificar al canal genérico; aprobar Telegram con hash desactualizado

**BandejaPedidos:**
Modal en `modulo_pedidos` (sidebar + `?bandeja=1`): tabs Por enviar / Por aprobar (IA) / Historial. Analizar = hidratar Comparativa (qty solo web). Ver ADR-0030.
_Avoid_: análisis = solo totales/PDF; re-correr motor al Analizar; multi-send P1; TTL 24 h sobre `ENVIADO`

**SubtractionFiles:**
_(Soporte eventual / secundario.)_ Upload Excel `BARRA`×`CANTIDAD` del Motor B legacy. Queda como mecanismo de contingencia si hace falta; el camino feliz es Backorder desde tablas dedicadas.
_Avoid_: exigir subtraction_files en P1/paridad; tratarlo como FiltroOperativo de primer nivel

**ForcedInclude:**
_(Deprecado.)_ Antes: BARRAs bajo umbral forzadas al export. Sustituido por resolución vía sucedáneos del Grupo en el Propuesto.
_Avoid_: reintroducirlo como requisito de paridad

**Sustitución:**
Usar otra BARRA del mismo Grupo (oferta de mercado vivo) dentro del PedidoPropuesto/Definitivo. Ver ADR-0005. κ / techo cuadrático en Definitivo (opt-in): ADR-0017.
_Avoid_: S4 coverage reduction; forced_includes; κ en Generar Sencillo

**PresetSencillo:**
Conservador — ADR-0010. Normal — ADR-0011. Agresivo — ADR-0013. LeadTime vía SplitLeadTime — ADR-0014.
_Avoid_: aplicar presets al Baseline

**ExtensionCobertura (F5):**
Mecanismo para aprovechar ofertas de precio dentro de un Grupo. **Dispara** cuando hay oferta(s) bajo umbral de Desvío. Las unidades extra **solo refuerzan el producto o productos en oferta** — no aumentan la compra de los demás miembros del Grupo en la distribución, y tampoco asignan el Gap grupal entero a la(s) oferta(s).
_Avoid_: F5 = +días al Grupo entero repartido a todos; F5 = Gap grupal completo volcado a la oferta; F5 solo por línea ignorando el resto del Grupo

**GapExtensionOferta:**
Gap intermedio para F5: `Gap_ext = Gap_oferta + (Gap_grupo − Gap_oferta) × f`. `f` = suma de `(e_i/5) × (rot_i / Σ rot_no_oferta)` sobre miembros **no-oferta** (denominador = solo su rotación, no la del Grupo entero). Refuerza solo productos en oferta.
_Avoid_: media simple; denom = rot_grupo total; reforzar no-oferta; Gap_grupo entero a la oferta

**PerfilPedido:**
Contrato por nivel de UI. Primer Generar (Propuesto): solo **Sencillo** (PresetSencillo + Cobertura + FiltrosOperativos + presupuesto opcional). Regenerar Definitivo: puede abrir **Intermedio/Avanzado**. Baseline no consume PerfilPedido del motor.
_Avoid_: OptimizerConfig crudo como API de UI; Avanzado obligatorio en el primer Generar

**Gap:**
Unidades faltantes que alimentan la Necesidad: demanda del horizonte menos stock, a nivel SKU o Grupo/Molécula según criterios de agrupación.
_Avoid_: CANTIDAD como concepto de dominio, Pedido

**DemandaGrupal:**
Rotación y stock agregados por Grupo/Molécula, materializados en `Procurement.RotacionGrupal`.
_Avoid_: r2_total del optimizer (suma SKU), rot_base informal

**Cobertura:**
Horizonte en días para el Gap (`dias_cobertura` / legacy `pedido_days`).
_Avoid_: lead time (entrega del proveedor, no horizonte de compra)

**PriceOpportunity:**
Señal unificada del Desvío de precio: score, multiplicador de cantidad y días extra.
_Avoid_: F4, amplificador y F5 como tres conceptos de negocio en UI sencilla

**Desvío:**
Fracción `(precio_usd − media_de_mediana) / media_de_mediana`. Negativo = más barato. Ventana motor **120d** sobre `Mercado_Historico`; si `dias_hist < 7` → fallback `Mercado_Historico_Semanal`. `fuente_baseline` ∈ {diario, semanal, mixto}. `media_min` / `media_precio_min` informativos — no base del desvío. UI: precio · media hist · Δ$ · % (USD) + badge fuente. Ver ADR-0021 / ADR-0024.
_Avoid_: descuento comercial del proveedor; usar `precio_min` como base; mezclar SACom 1:1 sobre semanas de mercado ya existentes

**MonedaPedidos:**
Motor siempre USD. `MonedaOferta` por lab (USD|VES→BCV). `MonedaTrabajo` solo display. Ver ADR-0023.
_Avoid_: scoring en bolívares; asumir VES sin `MonedaOferta`

**PDR:**
Probabilidad de Disponibilidad Real (`Mercado_Vivo_PDR`). `NO_CONFIABLE` → fuera del pool; `BAJA` → no topear qty con stock + `score×max(0.5,pdr)`. Gate Generar: stock≤N y PPP&lt;umbral → acción (default NO_CONFIABLE); knobs FE. Pesos scoring en `PDR_Config` (0.45/0.30/0.25). Ver ADR-0025, ADR-0026.
_Avoid_: confiar stock bajo a ciegas; filtrar labs enteros por un SKU; gate con umbral 0.001 sin tope de stock

**S4:**
Reducción de cobertura para SKUs costosos por elasticidad. No cableado; fuera del schema activo hasta reactivación.
_Avoid_: “activo con flag off”
