# PDR gate (stock×PPP) con knobs FE + pesos suaves

**Status:** accepted  
**Grill:** 2026-07-18  
**Related:** ADR-0025 (semáforos en Generar), `Analitica.PDR_Config`

## Context

Repesar PPP solo (p.ej. 0.40/0.25/0.35) **casi no crea** `NO_CONFIABLE` (umbrales 0.80/0.50/0.20); solo degrada ALTA→MODERADA y algo a BAJA. Stock=1 con VC+CMP altos sigue en MODERADA y Generar sigue topeando qty. Un gate duro con `umbral_ppp=0.001` solo expulsaría ~casi todo el mercado.

## Decision

1. **Pesos PDR_Config (global):** `peso_vc=0.45`, `peso_cmp=0.30`, `peso_ppp=0.25` (suave vs agresivo 0.40/0.25/0.35). `umbral_ppp` scoring sigue en **0.001**.
2. **Gate en Generar (por corrida), no en la vista:**
   - Si `pdr_gate_enabled` y `stock_proveedor ≤ pdr_gate_stock_max` y `ppp < pdr_gate_umbral_ppp` → aplicar `pdr_gate_action`.
   - `NO_CONFIABLE` (default): fuera del pool (ADR-0025).
   - `BAJA`: techo semáforo (sin tope de stock + score×pdr).
3. **Defaults knobs:** enabled=`true`, stock_max=`2`, umbral_ppp=`0.001`, action=`NO_CONFIABLE`.
4. **FE:** knobs living en Definitivo — Intermedio: enabled + stock_max; Avanzado: + umbral + action.
5. **Fail-open:** sin columna `ppp` o stock ausente → no gate.
6. Loader expone `ppp` (`peso_producto_en_proveedor` de `Mercado_Vivo_PDR`).

## Consequences

- Sencillo aplica gate con defaults (sin UI).
- Definitivo puede apagar o aflojar el gate sin tocar `PDR_Config`.
- Pesos globales afectan reportes/vista PDR; el gate solo Generar.
- Applied 2026-07-18: `PDR_Config` updated; backup `Analitica.PDR_Config_BKP_20260719_0317`.
