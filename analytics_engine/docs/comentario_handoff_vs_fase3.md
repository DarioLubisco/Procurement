# Comentario: Agente 1 (handoff) vs Agente 2 (FASE 3 performance)

**Fecha:** 2026-07-10  
**Alcance:** comentario crítico; no implica cambios de código.

> Canvas visual (abrir al lado del chat):  
> [`handoff-vs-fase3-comentario.canvas.tsx`](/home/synapse/.cursor/projects/home-synapse-source-Synapse-Procurement-analytics-engine/canvases/handoff-vs-fase3-comentario.canvas.tsx)

---

## Diferencia en una frase

| | **Agente 1 — Handoff** | **Agente 2 — FASE 3** |
|--|------------------------|------------------------|
| Pregunta | ¿Qué piezas hay y qué hacemos con cada una? | ¿Cómo acelerar el scoring en `optimizer.py:772-829`? |
| Unidad | Sistema entero (S4, kappa, gap×4, UI, RotacionGrupal, paridad…) | Un loop Python |
| Salida | Matriz de decisión + evidencia `archivo:línea` | Vectorizar / merge / (mal) `Estadisticas_Producto` |
| ¿Cambia el producto? | Sí — define destinos y roadmap | No — solo velocidad de v3.2 |
| Artefacto en este repo | **No** — solo anunció “voy a redactar” | **No** — solo un fragmento en el chat |

**No compiten.** El 1 es proceso/decisiones. El 2 es micro-optimización. El 2 **no sustituye** al 1.

---

## Por qué “no se abría nada”

1. El plan de Cursor (`.plan.md`) no es un entregable de producto; a veces no abre como archivo útil fuera del panel de planes.
2. El Agente 1 **no dejó** un handoff escrito en `docs/` — solo el anuncio.
3. El Agente 2 **no dejó** un doc “FASE 3” — solo el párrafo que pegaste.

Lo que **sí** puedes abrir (sustituto del handoff vacío):

- [docs/intent/propuesta_parametrizacion_unificada.md](../../docs/intent/propuesta_parametrizacion_unificada.md) — original
- [docs/intent/propuesta_parametrizacion_unificada_enmiendas_2026-07-10.md](../../docs/intent/propuesta_parametrizacion_unificada_enmiendas_2026-07-10.md) — enmiendas + P0–P4
- [CONTEXT.md](../../CONTEXT.md)
- [docs/adr/0001-convergencia-motor-pedido.md](../../docs/adr/0001-convergencia-motor-pedido.md)
- [docs/adr/0002-price-opportunity-unificada.md](../../docs/adr/0002-price-opportunity-unificada.md)
- [docs/adr/0003-sustitucion-aislada-del-pedido.md](../../docs/adr/0003-sustitucion-aislada-del-pedido.md)

*(Rutas relativas desde `analytics_engine/docs/`; en el monorepo viven bajo `Synapse-Procurement/`.)*

---

## Agente 1 — qué hizo bien / qué falta

**Bien (método):**
- Diagnóstico neutral antes de prescribir.
- Matriz por pieza (mejor que “reescribir el optimizer”).
- Exigir evidencia exacta (evita el error de marcar S4 como Activo).

**Falta:**
- Sin artefacto, no se valida ejecución vs anuncio.
- Debe citar original vs enmiendas y ADR-0001/2/3.
- Debe incluir paridad operativa (filtros/export), no solo fórmula Gap.

**Veredicto:** método sólido; valor = calidad de la matriz. Aquí no hay matriz que auditar.

---

## Agente 2 — qué hizo bien / qué está mal

**Evidencia real:** en `analytics_engine/core/optimizer.py` líneas 772–829 hay loop fila a fila; lookup `hist_df[hist_df["codbarras"]==…]` por fila es anti-patrón. `hist_df` ya se carga en batch (~698–709).

| Idea | Juicio |
|------|--------|
| `merge` sobre el mismo `hist_df` | Correcto, bajo riesgo semántico |
| Desvíos en batch | Correcto |
| Usar `Estadisticas_Producto` | **Incorrecto** como drop-in: es mediana de `Mercado_Vivo`, no histórico 90d → cambia F4/F5/amplificador |
| “10–50x” / “ALTO IMPACTO” | Marketing sin perfil; v3.2 no tiene UI productiva |

**Vectorización segura (misma semántica):**

```text
group_offers.merge(hist_df, on="codbarras", how="left")
→ desvio, F4, amplificador, F5 en Series
→ F3 constante por grupo
```

Sin tocar `Estadisticas_Producto`.

---

## Orden recomendado

1. Decisiones del Agente 1 **o** las enmiendas ya escritas (P1/P2 paridad + proxy).
2. Después, si el wall-clock lo pide, vectorizar como el Agente 2 (solo `merge(hist_df)`).

Acelerar v3.2 antes de paridad no arregla el split-brain (UI sigue en `pedidos.py`).
