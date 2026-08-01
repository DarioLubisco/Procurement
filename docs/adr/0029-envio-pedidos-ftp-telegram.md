# Envío de pedidos a droguerías (FTP/API) + aprobación FE/Telegram

**Status:** accepted  
**Grill:** 2026-07-22  
**Related:** ADR-0018 (BorradorPedidos), ADR-0015/0016 (ProveedorConfig/aliases), ADR-0028 (Mastranto Centro), ADR-0030 (Bandeja / Comparativa / TTL)

## Context

Tras Guardar borrador (ADR-0018), el comprador necesita **enviar** el pedido a cada lab por FTP/API. También llegarán **propuestas IA** que deben aprobarse por FE y/o Telegram sin duplicar el pipeline de envío. Ya existen specs en `N8N/*_FTP_SPECS.md`, orquestador n8n de pedidos, y `Proveedores.Pedidos_FTP_Secuencia`.

## Decision

### Pipeline único

```
[IA | FE Definitivo]
        ↓
  BorradorPedidos (PropuestaID)
        ↓
  Aprobación (FE Enviar = aprueba; Telegram = aprueba propuestas IA)
        ↓
  n8n Orquestador (FTP/API) ← contrato: PropuestaID (+ CodProv opcional)
        ↓
  ACK efectivo → ENVIADO | agotó reintentos → FALLIDO_ENVIO
        ↓
  Telegram AMC_Administrativo (intentos + resultado final)
```

Synapse **orquesta negocio** (persistir, estados, PDF, disparo). n8n **ejecuta** el canal del lab (credenciales FTP/API ya en n8n).

### UX FE

1. CTA único **Enviar** (por proveedor en P1): preview → confirmar → **guardar borrador interno** → solo si OK dispara envío. Sin segunda aprobación en Telegram.
2. Opcional: «Solo guardar» sin enviar (sigue ADR-0018).
3. Envío **por proveedor entero**; labs no seleccionados quedan en borrador para envío posterior/manual.
4. Labs sin formato de pedido documentado: botón deshabilitado (`formato_pendiente`).

### P1 — labs con formato verificado

| Lab | Canal | Tipo |
|-----|-------|------|
| VitalClinic, Zakipharma, Insuaminca | FTP TXT `;` | `TXT_ESTANDAR` |
| Intercontinental | FTP TXT | `TXT_POSICIONAL` |
| Mastranto Centro (`MASTRANTO_C`) | FTP TXT `\|` | Mastranto |
| Biogenética | FTP XLS | `XLS` |
| CristMedical | API JSON | `API_REST` |

**Fuera de P1 (formato pedido no documentado):** Nena, ITS, Drocerca, Gama. No inventar layouts.

### Estados cabecera (`BorradorPedidosCabecera.Estado`)

| Estado | Uso |
|--------|-----|
| `BORRADOR` | Definitivo FE guardado / listo para Enviar |
| `PENDIENTE_APROBACION` | Propuesta IA (no pisar con replace de `BORRADOR`) |
| `ENVIANDO` | Reintentos en curso |
| `ENVIADO` | ACK efectivo del lab |
| `FALLIDO_ENVIO` | Agotó intentos; disponible para manual |
| `RECHAZADO` | Telegram/FE rechazó; no borrar |

**Replace ADR-0018:** solo borra/reemplaza cabeceras `Estado=BORRADOR` del CodProv (no toca `PENDIENTE_APROBACION` / `ENVIADO` / etc.).

### Reintentos y notificaciones

- **3 ciclos × 3 intentos = 9 envíos** totales (enmienda grill 2026-07-23 / ADR-0030).
- Intra-ciclo: **1 → 2 → 5 min**. Entre ciclos: **30 min → 2 h → 6 h**.
- Avisos intermedios (“quedan N”) y final OK/KO → canal **AMC_Administrativo** (no el de notificación general).
- Telegram final **OK solo con ACK real** (FTP STOR exitoso + listado tamaño>0 si posible; API Crist HTTP 2xx parseable). No celebrar “encolado en orquestador”.
- Idempotencia: **primero gana** (`ENVIANDO` en txn); segundo approve → “ya en curso / ya enviado”.

### Telegram (aprobación IA)

- Texto corto (lab, PropuestaID, montos, #líneas) + **PDF** adjunto + botones Aprobar/Rechazar + link Synapse.
- PDF generado por **Synapse API** (misma plantilla que preview FE). No Excel de aprobación.
- PDF: sección **exhaustiva** para líneas con desviación vs Pedido Sencillo (Δqty, sucedáneo, altas/bajas) — ADR-0030.
- Botones llevan `revision`/`hash`; si la web guardó cambios → inválidos (“desactualizado”).
- P1: cualquier miembro del canal puede aprobar; persistir `AprobadoPor`. Whitelist users = P2.

### Armado del archivo

1. **Código lab:** lookup Mercado/inventario `(proveedor, barra≈CodProd)` → `codigo_producto`. Sin match → omitir línea + reportar en PDF/Telegram. Persistir código usado en snapshot de envío.
2. **Precio:** borrador guarda **Bs y USD**. Si el lab maneja ambas monedas → **enviar en bolívares**; si solo USD → USD. PDF declara moneda enviada.
3. **Correlativo:** `Proveedores.Pedidos_FTP_Secuencia` (ampliar seeds: Mastranto, Crist, etc.).
4. Tras OK: `ENVIADO` + `FechaEnvio`, nombre archivo, correlativo; **no borrar** cabecera.

### Schema (impl.)

Extender cabecera (y/o tabla de intentos) con: `FechaEnvio`, `ArchivoRemoto`, `Correlativo`, `AprobadoPor`, `AprobadoEn`, campos de último error/intento. Línea o snapshot: `CodigoProveedor` usado en el envío.

## Consequences

- Un solo pipeline sirve FE, Telegram e IA; no reescribir cuando lleguen propuestas automáticas.
- n8n reutiliza tipologías `TXT_ESTANDAR` / `TXT_POSICIONAL` / `XLS` / `API_REST`.
- ADR-0018 punto “FTP fuera de P1” queda supersedido por este ADR para el envío.
- Requiere migración de estados/metadatos y endpoints: resumen PDF, disparo envío, callback/poll de ACK.

## Out of scope (P2+)

- Whitelist de aprobadores Telegram.
- Envío parcial por línea dentro de un proveedor.
- Formatos Nena/ITS/Drocerca/Gama (cuando haya sample/spec del lab).
- Multi-send de varias cabeceras en un gesto (ADR-0030: P1 una a una).

**Superseded:** “Listar/editar borradores en FE” → **ADR-0030** (Bandeja de pedidos).
