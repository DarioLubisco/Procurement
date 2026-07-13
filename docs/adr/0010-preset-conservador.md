# Presets Sencillo — Conservador (cerrado)

Preset **Conservador** del PedidoPropuesto (primer Generar, nivel Sencillo). Objetivo: delta mínimo vs PedidoBaseline; motor casi no apuesta por precio.

| Knob | Valor |
|------|--------|
| amplifier_enabled | 0 (qty_mult = 1) |
| ext_max_dias_extra | 0 |
| pesos | w3_posicionamiento = 1.0; w1=w2=w4=w5 ≈ 0 |
| opp_lambda | default (inactivo en la práctica) |
| presupuesto | solo si hay monto_maximo_override |
| LeadTime soft | penalización baja |
| S4 | fuera del schema |

**Status:** accepted (grill Q19 = A)

Baseline no consume este preset. Normal y Agresivo se fijan en ADRs siguientes o en la misma serie.
