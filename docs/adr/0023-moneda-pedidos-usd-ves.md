# Moneda Pedidos: desvío USD + pantalla USD|VES

**Status:** accepted

## Decision

1. **Comparativa vs histórico / desvío / amp / mínimos:** siempre en **USD**.
2. **`ProveedorConfig.MonedaOferta`:** `USD` | `VES` — moneda en que cotiza el lab en `Mercado_Vivo`. Si `VES`, el loader divide por `dbo.dolartoday.dolarbcv` antes del motor.
3. **`PedidoAppConfig.MonedaTrabajo`:** `USD` | `VES` — moneda de **pantalla**. Si `VES`, la UI reconvierte precios y Δ a bolívares (`× dolarbcv`).
4. Tasa canónica: `SELECT TOP 1 dolarbcv FROM dbo.dolartoday ORDER BY fecha DESC` (mismo ecosistema que `CUSTOM_PRECIO_EN_DOLAR`).

## Consequences

- Pedido Propuesto muestra Precio + Total (antes no se veían).
- Histórico: snapshot diario en USD (`SP_Snapshot_Mercado`) + serie semanal ISO desde 2021-10-01 (`Mercado_Historico_Semanal`). Desvío 120d con fallback semanal. Ver ADR-0024.
- Seed inicial VES: NENA, ZAKIPHARMA, DROCERCA, ITS, GAMA.
