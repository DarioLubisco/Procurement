# Mercado histórico USD + serie semanal (ADR-0024)

**Status:** accepted  
**Updated:** 2026-07-16 — hybrid C (LOTES weekly backfill + market daily forward)

## Context

`Mercado_Historico` mezclaba USD y VES en medianas diarias; el desvío mentía. Hacía falta serie larga (desde reconversión) sin hinchar la DB, puente mientras madura el diario limpio, y `media_min` acumulativa (Notion / ADR-0021).

El gap-fill vía `SAITEMCOM.Costo` también contaminaba (costo a menudo en Bs). La fuente limpia de **costo USD** es `dbo.CUSTOM_LOTES.[Precio$ (per unit)]` (= `SALOTE.Costo / dolarbcv`) enlazada por `SAITEMCOM.NroUnicoL` → `CUSTOM_LOTES.NroUnico`. No existe `dbo.LOTES`; la tabla Profit es `dbo.SALOTE`.

## Decision

1. **Diario** `Analitica.Mercado_Historico`: solo **forward** vía `SP_Snapshot_Mercado` (Mercado_Vivo → USD con `MonedaOferta` ÷ BCV). Auditoría: `n_obs`, `fuente`, `moneda_snapshot`. Tras wipe híbrido, el diario arranca vacío/semilla del día y madura noche a noche.
2. **Semanal** `Analitica.Mercado_Historico_Semanal`: ISO week desde **2021-10-01**; caja `p25`, `mediana`, `p75`, `min`, **`media_precio_min`**, `n_obs`.
3. **Backfill híbrido (C):** wipe diario+semanal sucios; **reconstruir semanal desde costo USD** (`CUSTOM_LOTES` vía `NroUnicoL`). Percentiles reales en Python (`historico_stats.weekly_aggregate`) en el one-shot; rollup nightly mercado→semana puede seguir con puente SQL `MIN/AVG/MAX` si hace falta memoria.
3b. **`SP_Snapshot_Mercado`:** además de `MonedaOferta=VES`, convierte si `precio_raw >= BCV` o `precio_raw >= 20×` media costo LOTES USD de la barra (corrige labs mal etiquetados USD). Descarta medianas aún `>= BCV` tras normalizar.
4. **`media_min`**: acumulativa — semanal (`media_precio_min`) + baseline loader 120d (`media_min_diario`). **No** base del desvío.
5. Ventana motor: **120 días**. Si `dias_hist` &lt; 7 → fallback semanal (`fuente_baseline` = `semanal`|`mixto`).
6. **Huecos compras:** solo semanas **sin** fila de mercado. Precio = `CUSTOM_LOTES.[Precio$ (per unit)]` — **nunca** `SAITEMCOM.Costo` crudo. Mercado **gana** sobre costo en la misma barra+semana.
7. **Significado de `fuente_baseline`:**
   - `diario` — oferta vs mediana de **mercado** (días limpios)
   - `semanal` / `mixto` — oferta vs mediana de **costo de compra USD** (puente hasta madurar el diario)
8. Moneda mercado: `ProveedorConfig` / explícita; BCV en `CUSTOM_LOTES` para costo.
9. UI: cabecera `precio · media hist · Δ$ · %` (USD) + badge fuente; rivales `precio · %`.
10. Nightly: SQL Agent only (`SP_Refresh_Mercado_Historico_Noche`); N8N snapshot off.

## Consequences

- Desvío con badge `semanal`/`mixto` compara oferta vs **costo histórico**, no vs ofertas de mercado pasadas — aceptado como puente.
- SKUs nunca comprados no tendrán semana LOTES (~18% líneas sin join `NroUnicoL`).
- Scripts: `sql/rebuild_historico_from_lotes.py` (wipe+backfill; dry-run default); `sql/procs/SP_Refresh_Historico_Semanal.sql` (gaps LOTES).
- Relacionado: ADR-0021 (fórmula), ADR-0023 (moneda pedidos).
