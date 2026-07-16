# Desvío Generar desde Mercado_Historico (media_de_mediana)

El motor de DistribucionParcial / amp / F5 / κ usa `desvio` en cada oferta, pero el loader de Generar solo leía `Analitica.Mercado_Vivo` (sin histórico). Decidimos cablear la señal de dominio:

\[
\text{desvío} = \frac{\text{precio} - \text{media\_de\_mediana}}{\text{media\_de\_mediana}}
\]

donde `media_de_mediana` = **AVG(`precio_mediana`)** por `codigo_barras` en `Analitica.Mercado_Historico` (ventana reciente), con **fallback** a `Mercado_Historico_Semanal` si la cobertura diaria es insuficiente (ADR-0024).

**Status:** accepted

## Decision

1. En cada Generar / regenerar / ValidarMinimos load, tras Mercado_Vivo, agregar baselines históricas por barra (OPENJSON, misma estrategia que vivo).
2. Embebidos en cada offer row: `media_de_mediana`, `media_min_diario` (AVG `precio_min` en ventana 120d — informativo, **no** base del desvío), `dias_hist` / `semanas_hist`, `fuente_baseline`, `desvio`, `delta_vs_media_usd`.
3. Si no hay histórico para la barra → `desvio` omitido / NaN tratado como 0 en scoring (comportamiento previo).
4. Ventana default: últimos **120** días (`HISTORICO_DESVIO_LOOKBACK_DAYS`). Si `dias_hist` &lt; 7 → baseline semanal.
5. **No** usar `precio_min` de un solo día ni `Estadisticas_Producto.precio_min` como base del desvío (outliers / no representativo).
6. `media_min_historico` (Notion): cerrado vía semanal `media_precio_min` + loader `media_min_diario`.

## Consequences

- Amp, F5, κ y score de oportunidad dejan de vivir con `desvio` siempre vacío en productivo.
- Panel rivales / explicación UI reutiliza `media_de_mediana` / `media_min_diario` / Δ$ sin segundo fetch.
- Serie larga y snapshot USD: ver ADR-0024.
