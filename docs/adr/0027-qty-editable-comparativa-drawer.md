# Qty editable en Comparativa + drawer de contexto

**Status:** accepted  
**Grill:** 2026-07-20  
**Related:** ADR-0004 (Comparativa), ADR-0009 (Backorder), ADR-0018 (Borrador), ADR-0019 (justificación)

## Context

El comprador necesita ajustar `qty_propuesto` a mano (flechas/input) viendo demanda, stock propio, backorder, stock oferta, total del Grupo y competidores — sin re-correr el motor. Preparado para migración FE React / Graph async.

## Decision

1. **Override local (FE):** editar `qty_propuesto` no re-optimiza; sincroniza `pedido_propuesto` y alimenta Guardar borrador.
2. **Editor** en columna Qty Propuesto de Comparativa (`input type=number` min=0 step=1).
3. **Caps informativos:** no bloquean; warning si qty fila > `qty_baseline` **o** Σ qty propuesto del Grupo > Σ `qty_baseline` del Grupo.
4. **Drawer al foco** con tres bloques: (a) línea — baseline neto BO, qty, `existen`, backorder crudo, stock oferta; (b) Grupo — Σ propuesto / Σ baseline; (c) competencia — rivales/hermanos de justificación.
5. **P1 payload:** enriquecer cada fila Comparativa con `proveedor`, `existen`, `backorder_qty`, `stock_oferta`, `grupo_key`, `grupo_sum_baseline`, `grupo_sum_propuesto`, `extra_legs_qty`. Evolución: `GET /contexto-linea` lazy (Notion).
6. **Clave override:** `barra_propuesto` + `proveedor`.
7. **Tras Generar/Regenerar:** prompt Descartar / Reaplicar overrides.
8. **«Solo cambios»:** fila editada cuenta como cambio + badge `editado`.
9. **SplitLeadTime:** el delta ajusta solo la pierna primaria (`qty − extra_legs_qty`); `extra_legs` fijas.
10. **Qty 0:** sale del Propuesto; Comparativa muestra 0.
11. **Gráfico** en drawer: aplazado (Notion).

## Consequences

- `ComparativaRow` / JSON Comparativa ganan campos de contexto (contrato estable para React).
- Motor intacto; overrides viven en `lastGenerarResult` hasta el próximo Generar.
- Guardar borrador usa qtys ya syncadas en `pedido_propuesto`.
