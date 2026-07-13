# Presets Sencillo — Normal (cerrado)

Preset **Normal** del PedidoPropuesto = calibración v3.2 actual + LeadTime soft medio.

| Knob | Valor |
|------|--------|
| amplifier | ON — a=5.84, b=1.29, max_increment=500%, floor=0.2 |
| extensión F5 | max_dias_extra=21, umbral=−0.10, eta=4.0 |
| pesos | w1=0.15, w2=0.25, w3=0.25, w4=0.20, w5=0.15 |
| opp_lambda | 1.0 |
| presupuesto | solo si hay monto_maximo_override |
| LeadTime soft | penalización media |
| S4 | fuera |

**Status:** accepted (grill Q20 = A)

## Nota F5 (alcance) — supersede por ADR-0012

F5: refuerza **solo** productos en oferta; tamaño = Gap intermedio (oferta ↔ Grupo) según elasticidades de **no-oferta**. No Gap grupal entero ni +días a miembros fuera de oferta.
