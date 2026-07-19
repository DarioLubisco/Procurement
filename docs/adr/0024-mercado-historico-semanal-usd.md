# Mercado histórico semanal USD + fallback del desvío

ADR-0021 cableó el desvío a `AVG(precio_mediana)` diario, pero la cobertura diaria era corta/sucia (moneda mixta, huecos). Necesitamos una serie larga en USD y un fallback cuando el diario 120d no alcanza.

**Status:** accepted  
**Supersedes (partially):** ADR-0021 §Decision.4 (ventana 90d diario-only)  
**Related:** ADR-0023 (moneda), `sql/015_*`, `sql/016_*`, `analytics_engine/historico_stats/`

## Decision

1. **Fórmula intacta (ADR-0021):**  
   \(\text{desvío} = (\text{precio\_usd} - \text{media\_de\_mediana}) / \text{media\_de\_mediana}\).
2. **Ventana motor:** **120 días** (`HISTORICO_DESVIO_LOOKBACK_DAYS`).
3. **Cobertura mínima diaria:** si `dias_hist < 7` (`MIN_DIAS_DIARIO_COBERTURA`) → baseline desde `Analitica.Mercado_Historico_Semanal` (AVG de `precio_mediana` semanal en la misma ventana).
4. **Exponer** `fuente_baseline` ∈ {`diario`,`semanal`,`mixto`}, más `dias_hist` / `semanas_hist`, `media_min_diario` (AVG `precio_min` o `media_precio_min` — **informativo, no base del desvío**).
5. **Serie semanal ISO** desde **2021-10-01** (reconversión): PK `(codigo_barras, anio_iso, semana_iso)`; caja `p25/mediana/p75/min/media_precio_min/n_obs`. En SQL Agent el box semanal puede ser MIN/AVG/MAX de medianas diarias (bridge por memoria) — no confundir con `PERCENTILE_CONT` verdadero.
6. **SACom / CUSTOM_LOTES (hybrid C):** solo **rellenan huecos** (semana/barra sin obs de mercado). Nunca sobrescribir una semana de mercado existente 1:1.
7. **Nightly:** SQL Agent job `Synapse_Refresh_Mercado_Historico_Noche` @ 06:00 (`SP_Refresh_Mercado_Historico_Noche` → diario luego semanal). **No** reactivar N8N `[CRON] Snapshot Diario de Mercado` mientras el Agent esté on.
8. **UI (misma entrega):** cabecera elegida `precio · media hist · Δ$ · %` (USD) + badge `[fuente_baseline]`; rivales `precio · %`.

## Consequences

- Hasta acumular ≥7 días diarios limpios, casi todos los SKUs salen `mixto`/`semanal` — esperado, no bug.
- Diario histórico pasado puede seguir sucio; el SP limpia **hacia adelante**. Cleanup DML del pasado requiere dry-run + backup (sql-safety).
- Rebuild: `sql/rebuild_historico_semanal.py` (prefer SP/job en régimen).
