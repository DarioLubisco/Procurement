# Moneda pedidos USD / VES

Pedidos mezclaba precios en USD y VES (ofertas vivo, mínimos, UI). Sin moneda explícita por lab, el desvío y los mínimos se corrompen. Decidimos un eje de moneda claro: **motor siempre USD**; display opcional en VES vía BCV.

**Status:** accepted  
**Related:** ADR-0021 (desvío), ADR-0024 (histórico USD), `sql/013_*`, `sql/014_*`

## Decision

1. **Motor / scoring / desvío / mínimos:** siempre en **USD**.
2. `Procurement.ProveedorConfig.MonedaOferta` (`CHAR(3)`, default `USD`): moneda en que publica el lab en mercado vivo. Si `VES` → convertir ÷ `dolartoday.dolarbcv` antes de persistir o comparar.
3. `Procurement.PedidoAppConfig` key-value: `MonedaTrabajo` ∈ {`USD`,`VES`} = **solo display** en UI Pedidos. El desvío y Δ$ siguen en USD; si UI pide Bs, reconvertir con BCV de sesión.
4. Snapshot diario (`SP_Snapshot_Mercado`) escribe `Mercado_Historico` ya normalizado a USD (`moneda_snapshot='USD'`).
5. API: `/api/pedidos/moneda-config` (GET) + PUT trabajo / PUT oferta por `ProveedorID` (`backend/routers/pedido_moneda.py`).
6. BCV: ecosistema `dbo.dolartoday` vía `backend/services/fx_bcv.py` — no inventar tasas.

## Consequences

- Labs mal etiquetados (VES como USD) siguen siendo riesgo de datos; la heurística de magnitud vive en QA (`historico_stats.currency`), no en el hot path de Generar.
- Mínimos (`MontoMinimoPedidoUSD`) y Amp/F5 hablan la misma unidad que el desvío.
- Sin `MonedaOferta` en un entorno fresco, apply `sql/013` + `014` antes de usar moneda UI.
