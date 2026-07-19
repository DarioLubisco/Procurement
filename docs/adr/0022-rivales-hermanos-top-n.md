# Rivales top-N y hermanos reemplazables en Comparativa

El FE solo veía la oferta ganadora (`score`). Embebemos top-N rivales (mismo Grupo, ranking por score) y top-N hermanos (otras barras MDM con su mejor oferta) en `justificacion_factores[].datos`, sin re-query a Mercado.

**Status:** accepted

## Decision

1. Knobs `rivales_top_n` / `hermanos_top_n` (default **3**, clamp 1–10) en Intermedio y Avanzado.
2. Payload en factor `oferta` (y hermanos también en `sucedaneo`): `rivales[]`, `hermanos_reemplazables[]`, `top_n_*`, `n_candidatos`.
3. UI: al expandir justificación, lista humana «¿Por qué esta oferta?» + «Hermanos reemplazables».
4. No endpoint lazy en v1 — el top-N ya viaja con Generar (bajo costo vs mercado completo).

## Consequences

- Amp/F5/κ siguen usando la elegida; el top-N es trazabilidad UX.
- Contrato estable para futuro React / Graph.
