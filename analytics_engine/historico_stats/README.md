# Histórico USD / estadísticas de mercado

Proceso versionado en git para **depurar fuentes → construir estadísticas** (diario + semanal) usadas por desvío / Amp / futuras apps.

## Actualización automática (SQL Agent — no N8N)

Cada noche **06:00** el job `Synapse_Refresh_Mercado_Historico_Noche` ejecuta:

1. `Analitica.SP_Snapshot_Mercado` — lista del día (USD; heurística BCV/LOTES si lab mal etiquetado)
2. `Analitica.SP_Refresh_Historico_Semanal` — lista semanal (+ huecos `CUSTOM_LOTES` vía `NroUnicoL`)

One-shot wipe+backfill: `python sql/rebuild_historico_from_lotes.py --commit --backup --seed-today`  
(DDL de SPs: `python sql/apply_historico_agent_job.py` con **pyodbc autocommit**, no el pool de `database.py`.)

**Apagar** el flujo N8N `[CRON] Snapshot Diario de Mercado` para no duplicar el snapshot.

## Cortes y reglas

- Reconversión: **2021-10-01**
- Ventana motor desvío: **120 días**
- Semana: **ISO** (`anio_iso`, `semana_iso`)
- Desvío usa solo `media_de_mediana` (no `media_min`)
- `media_min`: acumulativa en semanal (`media_precio_min`) y en baseline 120d (`media_min_diario`)
- Huecos compras: solo semanas **sin** fila mercado; USD desde `CUSTOM_LOTES.[Precio$ (per unit)]` vía `SAITEMCOM.NroUnicoL` (nunca `SAITEMCOM.Costo` crudo)
- Backfill híbrido C: wipe + semanal desde LOTES; diario solo forward (`SP_Snapshot_Mercado`)
- Moneda mercado: `ProveedorConfig.MonedaOferta` / BCV; costo: BCV en `CUSTOM_LOTES`

## Artefactos QA

Por defecto bajo `reports/historico_qa/`:

- `inventory.json` — conteos / cobertura
- `exclusiones.csv` — filas marcadas (BCV missing, outlier, dudoso)
- `qa_summary.html` — resumen (profiling opcional si `ydata-profiling` instalado)

Deps opcionales: `requirements-historico-qa.txt`.
