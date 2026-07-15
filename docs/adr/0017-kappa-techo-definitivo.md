# Kappa / techo cuadrático en Definitivo (ADR-0017)

Tras grill 2026-07-15: se reactiva `sust_kappa` / `quadratic_ceiling` **solo en Regenerar Definitivo**, como tope opt-in sobre cuánto del qty de una línea Baseline puede resolverse con una BARRA distinta (sucedáneo del Grupo). Generar Sencillo no aplica κ.

**Status:** accepted

## Behavior

1. Techo = fracción del **qty Baseline** de esa línea.
2. Si el mejor offer es otra BARRA y κ está activo:  
   `techo = quadratic_ceiling(max_sustitucion_base, desvio, kappa, amplificador=1.0)`  
   → `qty_sub = floor(techo × Q)` al sucedáneo; resto en BARRA baseline (split / `extra_legs`).
3. Misma BARRA → sin techo κ (100% como hoy).
4. **SplitLeadTime** tiene prioridad: si dispara, esa línea **no** aplica κ.
5. Opt-in: si `sust_kappa` **no** viene en overrides → off. Si viene → on (default UI sugerido 5.0).
6. `max_sustitucion_base` por mapa de elasticidad (abajo); override opcional solo Avanzado.
7. `amplificador_sucedaneo = 1.0` en el techo (v1) para no doble-contar el amplificador de qty.

### Mapa elasticidad → base

| elasticidad_demanda (redondeada) | max_sustitucion_base |
|----------------------------------|----------------------|
| ≤ 0 | 0.0 |
| 1 | 0.2 |
| 2 | 0.4 |
| 3 | 0.6 |
| ≥ 4 | 0.8 |

## UI

Intermedio + Avanzado exponen `sust_kappa` con label/ayuda en español. Avanzado también `max_sustitucion_base`. JustificacionDelta declara techo κ en splits.

## Consequences

- `sust_kappa` / `kappa` salen de knobs muertos; S4 sigue muerto.
- ADR-0003/0005: el aislamiento total de κ queda sustituido por este ADR para Definitivo.
- Calibración pendiente de uso real; valores del mapa son defaults explícitos, no verdad de negocio.
