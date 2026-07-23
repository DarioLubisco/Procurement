# Bandeja de pedidos: ver / analizar / aprobar / enviar

**Status:** accepted  
**Grill:** 2026-07-23  
**Related:** ADR-0018 (BorradorPedidos), ADR-0027 (qty editable Comparativa), ADR-0029 (Envío FTP/Telegram)

## Context

Tras Guardar borrador y con propuestas IA en camino, el comprador necesita un **menú independiente** para listar cabeceras, **analizar** (Comparativa real, no solo totales), editar qtys en web, aprobar/rechazar y enviar — sin re-correr el motor. ADR-0029 dejaba “listar borradores en FE” como P2; este ADR lo trae a P1 y fija snapshot, TTL y UX.

## Decision

### Superficie

- Nombre: **Bandeja de pedidos**.
- Entrada **C**: ítem sidebar + atajo en `modulo_pedidos`.
- Un solo HTML: `modulo_pedidos.html?bandeja=1` (o `#bandeja`) abre el modal; el atajo del módulo abre el mismo.
- Badges en sidebar/atajo: **dos** contadores — por enviar | por aprobar.

### Tabs

1. **Por enviar** — `BORRADOR` + `FALLIDO_ENVIO`
2. **Por aprobar (IA)** — `PENDIENTE_APROBACION`
3. **Historial** — `ENVIADO` + `RECHAZADO` (y metadatos de envío)

### Análisis = Comparativa (obligatorio para “analizar”)

- **Analizar** hidrata la Comparativa principal de `modulo_pedidos` (mismo patrón ADR-0027: qty editable, drawer).
- Si hay Generar en curso con cambios locales → **confirmación** antes de reemplazar sesión.
- Qty editable **solo en web**; Telegram no edita cantidades.
- Persistencia de edits: al **Guardar cambios / Aprobar / Enviar** (no autosave por línea).

### Snapshot sin re-correr motor

- Al Guardar borrador FE y al crear propuesta IA: persistir `comparativa_cantidades` + `pedido_propuesto` en tabla hija (p. ej. `BorradorPedidosComparativa`), no embebido solo en `ParametrosJson`.
- Cabecera lleva `Revision` (int) + `SnapshotHash` para invalidar botones Telegram si la web guardó cambios.
- Destino Graph async / React: `GET /propuestas/{id}/comparativa` lazy (rivales/hermanos completos a la larga).

### Reglas de envío / aprobación (FE)

- Envío P1: **una** `PropuestaID` a la vez.
- Desde lista Por enviar: **Enviar** solo si **0 desviaciones** vs Pedido Sencillo; si hay desvíos → forzar Analizar.
- IA web: **Aprobar sin enviar** | **Aprobar y enviar**.
- Rechazar (web/Telegram): `RECHAZADO` + **motivo obligatorio**; no borrar.
- Historial: lectura + PDF + Comparativa read-only; **Clonar a borrador** (nueva `PropuestaID`).

### Desviación vs Pedido Sencillo (PDF Telegram)

Sección **exhaustiva** en PDF para líneas con:

- `qty_propuesto ≠ qty_baseline` (misma barra), y/o
- cambio de producto / sucedáneo, y/o
- altas/bajas (solo propuesto o solo baseline).

Telegram: texto corto + PDF + botones; approve lleva `revision`/`hash`; si cabecera cambió → botones inválidos (“desactualizado; abre Synapse”).

### TTL / retención

| Estado | Cabecera | Snapshot Comparativa |
|--------|----------|----------------------|
| `BORRADOR` | ≤ **24 h** luego purge | ≤ 24 h |
| `PENDIENTE_APROBACION` | **72 h** (+ aviso a las **48 h**) luego auto-`RECHAZADO` motivo “expirado” | 7 d tras rechazo |
| `FALLIDO_ENVIO` | **72 h** (+ aviso 48 h) luego auto-`RECHAZADO` “fallido expirado” | 7 d tras rechazo |
| `ENVIADO` | **no borrar** | ≥ **7 días** luego se puede purgar solo el blob |
| `RECHAZADO` | permanente (auditoría) | ≥ 7 días |

### Reintentos n8n (enmienda ADR-0029)

- **3 ciclos × 3 intentos = 9**.
- Intra-ciclo: **1 → 2 → 5 min**.
- Entre ciclos: **30 min → 2 h → 6 h**.

## Consequences

- Supersede ADR-0029 “Out of scope: listar/editar borradores en FE”.
- Guardar borrador debe grabar Comparativa (rompe “solo líneas” de ADR-0018 en la práctica de bandeja).
- Job de TTL + avisos FE/Telegram.
- API listado liviano (cabecera) vs GET comparativa pesado (hijo) alineado a migración Graph/React.

## Out of scope (P2+)

- Multi-send de varias cabeceras en un gesto.
- Comparativa embebida dentro del modal (se hidrata la principal).
- Whitelist aprobadores Telegram (sigue ADR-0029 P2).
- Cold archive de `ENVIADO` más allá de 7 d de Comparativa.
