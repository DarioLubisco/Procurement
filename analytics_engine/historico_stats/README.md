# Histórico USD / estadísticas de mercado

Proceso versionado en git para **depurar fuentes → construir estadísticas** (diario + semanal) usadas por desvío / Amp / futuras apps.

## Orden

0. **QA / depuración** (`python -m analytics_engine.historico_stats.run_qa`)
1. DDL `sql/015_*` + `sql/016_*` (+ migrate)
2. Snapshot diario USD (`sql/procs/SP_Snapshot_Mercado.sql`)
3. Backfill semanal dry-run → commit (`sql/rebuild_historico_semanal.py`)
4. Loader motor (120d + fallback semanal)

## Cortes y reglas

- Reconversión: **2021-10-01**
- Ventana motor desvío: **120 días**
- Semana: **ISO** (`anio_iso`, `semana_iso`)
- Desvío usa solo `media_de_mediana` (no `media_min`)
- `media_min`: acumulativa en semanal (`media_precio_min`) y en baseline 120d (`media_min_diario`)
- `SACOMP`/`SAITEMCOM`: solo **huecos** (sin obs de mercado esa semana/barra)
- Moneda: `ProveedorConfig.MonedaOferta` / explícita; heurística por barra al final

## Artefactos QA

Por defecto bajo `reports/historico_qa/`:

- `inventory.json` — conteos / cobertura
- `exclusiones.csv` — filas marcadas (BCV missing, outlier, dudoso)
- `qa_summary.html` — resumen (profiling opcional si `ydata-profiling` instalado)

Deps opcionales: `requirements-historico-qa.txt`.
