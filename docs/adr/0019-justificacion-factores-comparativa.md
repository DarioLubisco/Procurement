# JustificacionFactores en Comparativa (ADR-0019)

Tras grill 2026-07-15: la celda de justificación en ComparativaCantidades deja de ser un string concatenado monocausal. El motor emite **factores estructurados** + un **resumen corto** truncado; el detalle completo vive en hover y acordeón exclusivo.

**Status:** accepted

## Contrato

Cada fila de Comparativa lleva:

- `justificacion_delta` — resumen corto (títulos top-2 por prioridad + `+N` si hay más).
- `justificacion_factores` — lista `{codigo, titulo, detalle, datos}`.

Prioridad de celda (grill C): sucedáneo → SplitLT → κ → F5 → amplificador → oferta → delta → sin_* → Validar mínimos.

## Factores v1

`sucedaneo`, `delta_qty`, `split_lead_time`, `kappa`, `f5`, `amplificador`, `oferta`, `sin_oferta`, `sin_catalogo`, `validar_minimos`.

ValidarMinimos **no** concatena al string: append del factor `validar_minimos` y regenera el resumen vía `finalize`.

## UI

- Celda truncada + `title`/hover con todos los factores.
- Click: acordeón exclusivo (una fila abierta).
- Definitivo: knobs con `ⓘ` (`field.help` del schema); sin `<small>` denso.

## Consequences

- ADR-0016: traza VM pasa por factores, no por concatenación libre.
- FE cache-bust `?v=20260715-justificacion-factores`.
