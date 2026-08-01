# Desvío Generar desde Mercado_Historico (media_de_mediana)

El motor de DistribucionParcial / amp / F5 / κ usa `desvio` en cada oferta, pero el loader de Generar solo leía `Analitica.Mercado_Vivo` (sin histórico). Decidimos cablear la señal de dominio:

\[
\text{desvío} = \frac{\text{precio} - \text{media\_de\_mediana}}{\text{media\_de\_mediana}}
\]

donde `media_de_mediana` = **AVG(`precio_mediana`)** por `codigo_barras` en `Analitica.Mercado_Historico` (ventana reciente).

**Status:** accepted

## Decision

1. En cada Generar / regenerar / ValidarMinimos load, tras Mercado_Vivo, agregar baselines históricas por barra (OPENJSON, misma estrategia que vivo).
2. Embebidos en cada offer row: `media_de_mediana`, `media_min_diario` (AVG `precio_min`, informativo — **no** base del desvío), `dias_hist`, `desvio`.
3. Si no hay histórico para la barra → `desvio` omitido / NaN tratado como 0 en scoring (comportamiento previo).
4. Ventana default: ~~últimos **90** días~~ → **superseded by ADR-0024**: **120 días** + fallback semanal si `dias_hist < 7`; ver `fuente_baseline`.
5. **No** usar `precio_min` de un solo día ni `Estadisticas_Producto.precio_min` como base del desvío (outliers / no representativo).

## Consequences

- Amp, F5, κ y score de oportunidad dejan de vivir con `desvio` siempre vacío en productivo.
- Panel rivales futuro puede reutilizar `media_de_mediana` / `media_min_diario` sin segundo fetch.
- Relacionado: tareas Notion de snapshot `media_min_historico` / fórmula sofisticada — este ADR es el cableado mínimo viable al Generar.
- Evolución: moneda USD (ADR-0023) + serie semanal / lookback 120d (ADR-0024).
