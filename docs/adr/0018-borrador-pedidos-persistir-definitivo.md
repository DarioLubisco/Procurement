# BorradorPedidos: persistir PedidoDefinitivo

Tras grill 2026-07-15: `Procurement.BorradorPedidosCabecera` / `BorradorPedidosLineas` son la **persistencia de salida** del PedidoDefinitivo (gesto explícito «Guardar borrador»). **No** son Backorder (resta de tránsito; ADR-0009) ni entrada al Generar.

**Status:** accepted

## Behavior

1. **Qué:** solo el Definitivo en pantalla (no Sencillo).
2. **Cuándo:** botón FE «Guardar borrador» tras Regenerar Definitivo exitoso; se deshabilita si el comprador vuelve a Generar Sencillo.
3. **Grano:** 1 cabecera por proveedor comercial; N cabeceras por un Guardar.
4. **CodProv cabecera:** canónico vía `ProveedorCodProvAlias` / `ProveedorID` (misma idea que ValidarMinimos). Proveedor no resoluble → **omitir** esa cabecera (P1). Exigir ProveedorConfig sin omit (opción D del grill) queda aparcado.
5. **Replace:** borrar **todos** los `Estado=BORRADOR` de ese CodProv (líneas + cabeceras) e insertar el nuevo.
6. **Identidad línea:** `CodProd = barra` del Definitivo (en el seam, barra ≡ `SAPROD.CodProd`). Línea sin fila en SAPROD → omitir + reportar.
7. **Duplicados** mismo CodProd en un proveedor: una fila; `CantidadPropuesta = SUM`; `CostoCalculadoUSD` ponderado por qty si hay precios.
8. **Costos P1:** `CostoCalculadoUSD` desde `precio` de la línea Definitivo; `MontoTotalUSD` = suma; `CostoBaseBs` / inv / min / max / `TasaCambioBCV` = NULL o 0.
9. **Payload:** FE envía `pedido_propuesto` (con `precio`) + `parametros` (snapshot Definitivo: nivel, base_preset, cobertura, criterios, filtros, overrides, overrides_applied); el server **no** re-corre el motor ni reconsulta Mercado.
10. **Txn:** all-or-nothing. Proveedor que queda en 0 líneas tras filtros → no crear cabecera vacía; Guardar OK si queda ≥1 cabecera útil; si ninguna → error.
11. **ParametrosJson:** columna `NVARCHAR(MAX)` en cabecera; **mismo** JSON en cada cabecera del Guardar (auditoría por proveedor sin tabla batch).
12. **Fuera de P1:** listar/editar/borrar borradores; FTP/envío; leer borrador de vuelta al Generar.

## API / FE (P1)

- Extender Definitivo / `PropuestoLine` con `precio` (USD oferta).
- `POST /api/pedidos/guardar-borrador` (+ `parametros`) + botón FE + toast (cabeceras creadas / omisiones).
- Migración: `sql/011_borrador_parametros_json.sql`.

## Consequences

- Distingue Borrador (propuesta a enviar) de Backorder (ya pedido / pendiente).
- Depende de aliases canónicos (ADR-0015/0016) y de precio en el contrato Definitivo.
- Knobs/params del Definitivo quedan auditables en `ParametrosJson` (no solo las líneas).
- Tablas existentes + `ParametrosJson`; no hace falta batch-id en P1.