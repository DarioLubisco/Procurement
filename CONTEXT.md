# Procurement — Generación de Pedidos

Vocabulario de dominio para el motor de pedidos y su parametrización en Synapse-Procurement.
Fuente de diseño: `docs/intent/propuesta_parametrizacion_unificada.md` (original) y
`docs/intent/propuesta_parametrizacion_unificada_enmiendas_2026-07-10.md` (enmiendas).

## Language

**Necesidad:**
Cantidades a reponer por producto, sin asignar proveedor. Identidad técnica: código de barras (BARRA). Presentación al comprador: descripción del producto. El muestreo sale de los FiltrosOperativos + rotación.
_Avoid_: Pedido, export de solo dos columnas como única salida de UI

**PedidoBaseline:**
Cantidades **solo con rotación × cobertura − stock**, **sin motor de scoring**. La rotación/stock se agregan con los **mismos CriteriosAgrupacion** de la corrida (default: PA+FF+conc+cantidad_presentacion+contenido_neto, o los editados en el FE). Comparte Cobertura y FiltrosOperativos; no aplica PriceOpportunity, pesos ni LeadTime.
_Avoid_: Baseline en rotación SKU mientras Propuesto usa Grupo de 5 attrs; aplicar amplificador al Baseline; llamar “perfil Lineal v3.2” al Baseline

**CriteriosAgrupacion:**
Lista de atributos MDM que definen el Grupo (whitelist `RotacionGrupal`). Default de sistema: `principio_activo`, `forma_farmaceutica`, `concentracion`, `cantidad_presentacion`, `contenido_neto` — persistido en BD (perfil/config) y **sobreescribible** como preferencia de usuario en el FE; editable antes del primer Generar. Gobiernan **Baseline y Propuesto** en la misma corrida. El request siempre envía la lista efectiva al backend.
_Avoid_: criterios_agrupamiento ignored del v3.2; solo PA+FF+conc; columna `cantidad` suelta; Baseline SKU vs Propuesto grupal; default solo en localStorage sin default de sistema

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

**MOQ:**
Cantidad mínima de pedido **por proveedor** (por oferta). En SplitLeadTime: `mínimo_al_rápido = max(rot×LT, MOQ_proveedor)` si MOQ está cargado; si no, solo `rot×LT`. Ubicación física del dato se decide en P1; hasta entonces MOQ es nullable. **No** es `SAPROD.Minimo` del ERP.
_Avoid_: inventar MOQ fantasma; bloquear P1 por falta de tabla MOQ; usar SAPROD.Minimo como sustituto sin decisión

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
Artefacto de primer pase (grano: fila por BARRA Baseline). Convive en el mismo Generar con el PedidoPropuesto (líneas con proveedor). Columnas: BARRA/desc Baseline, BARRA/desc Propuesto, qty Baseline, qty Propuesto, JustificacionDelta (multi-factor).
_Avoid_: Matriz de Decisión; Excel solo BARRA×CANTIDAD; primer Generar sin ver proveedor; delta monocausal

**JustificacionDelta:**
Explica el delta Baseline vs Propuesto: misma BARRA con otra cantidad, o **reemplazo** por otra BARRA del Grupo, más PriceOpportunity, cobertura, presupuesto, etc.
_Avoid_: texto que no declare cambio de código cuando hubo sucedáneo

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
_Avoid_: subtraction_files como fuente primaria; restar backorder solo a un lado de la Comparativa

**SubtractionFiles:**
_(Soporte eventual / secundario.)_ Upload Excel `BARRA`×`CANTIDAD` del Motor B legacy. Queda como mecanismo de contingencia si hace falta; el camino feliz es Backorder desde tablas dedicadas.
_Avoid_: exigir subtraction_files en P1/paridad; tratarlo como FiltroOperativo de primer nivel

**ForcedInclude:**
_(Deprecado.)_ Antes: BARRAs bajo umbral forzadas al export. Sustituido por resolución vía sucedáneos del Grupo en el Propuesto.
_Avoid_: reintroducirlo como requisito de paridad

**Sustitución:**
Usar otra BARRA del mismo Grupo (oferta de mercado vivo) dentro del PedidoPropuesto/Definitivo. Ver ADR-0005. `kappa` sigue fuera del schema hasta calibración.
_Avoid_: kappa / techo cuadrático; forced_includes

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
Fracción `(precio − media_de_mediana) / media_de_mediana`. Negativo = más barato.
_Avoid_: descuento comercial del proveedor

**S4:**
Reducción de cobertura para SKUs costosos por elasticidad. No cableado; fuera del schema activo hasta reactivación.
_Avoid_: “activo con flag off”
