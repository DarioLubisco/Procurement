# Handoff — Parametrización Pedidos / Generar unificado

**Fecha:** 2026-07-14  
**Branch / tip:** `origin/main` (local `master` → `HEAD:main`)  
**Estado:** P1 tracer tickets **01–12 done**; smoke live + UI checklist **PASS**

## Qué quedó listo

- Seam `generar_pedido` → Baseline + Propuesto + Comparativa (Sencillo + Regenerar Definitivo).
- MDM attrs vía `LEFT JOIN Procurement.por_aprobacion_equivalencias` (`pedidos.sql`).
- Mercado_Vivo en **chunks** (prioridad necesidad + hermanos MDM); no truncar a 200 fijos.
- Backorder desde `Procurement.BackorderPedidosCabecera/Lineas` (abiertos); hoy DB solo tiene CERRADO → resta vacía.
- `GET /categories` cursor + retry (sin pandas Gaps).
- FE Definitivo: knobs desde `/overrides-schema` (Intermedio 12 / Avanzado 17).

## Diferidos (no inventar)

| Tema | Notas |
|------|--------|
| **MOQ / mínimo USD** | Columna `MontoMinimoPedidoUSD` lista. Flujo ValidarMinimosProveedor: **ADR-0016** (grill cerrado; impl pendiente). |
| **Latencia Generar** | ~~12–23s~~ → **~2.5s** load (`OPENJSON` join a Mercado_Vivo; IN parametrizado era el cuello). |
| **BorradorPedidos** | Existe; no es Backorder abierto. No cableado al Generar. |

## Smoke reciente (referencia)

- Categories ×10 OK; Conservador/Normal 20/20/20; Regenerar Intermedio/Avanzado con overrides OK; `s4_enabled` → 400.
- FE: hard-refresh tras deploys (`app_pedidos.js?v=…`).

## No reabrir

Grill cerrado (Necesidad vs Pedido, Baseline sin motor, Comparativa grain B, F5, SplitLeadTime, presets, MOQ nullable). Ver ADRs `docs/adr/0001`–`0015` + `CONTEXT.md`.

## Próximo agente

1. Si ops publica MOQ → mapear a `market_offers.moq` / `OfferLeg.moq`.
2. ~~Si piden velocidad → perfilar chunks Mercado_Vivo~~ — hecho: OPENJSON (~0.5s) + fallback full-scan.
3. ~~Cache categories + meta `load_ms` / `offers_unique` / `backorder_rows`~~ — hecho 2026-07-14.
