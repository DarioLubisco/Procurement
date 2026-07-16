# Notion backlog — Pedidos / Validar mínimos

## Advertencia submínimo antes de enviar pedido al proveedor

**Status:** needs-triage  
**Sprint:** Analytics Engine / Pedidos  
**Origen:** grill Validar mínimos 2026-07-16

### Problema
Tras redistribución parcial, las líneas que **quedan** con el lab pueden seguir bajo `MontoMinimoPedidoUSD`. Hoy no hay un gate al momento de **enviar / confirmar el pedido al proveedor**.

### Requisito
Antes de enviar el pedido a un proveedor, si `sum(qty×precio_USD) < MontoMinimoPedidoUSD`:
1. Mostrar advertencia explícita (lab, total, mínimo, déficit).
2. Obligar confirmación consciente (no silencioso).
3. No bloquear del todo si el comprador confirma (aceptó submínimo operativo).

### Fuera de alcance (ya hecho 2026-07-16)
- Checklist de redistribución por línea
- Confiables marcados por defecto
- No marcadas = se quedan con el lab
- Botón «Aplicar redistribución» ≠ «Aceptar submínimo»
- Descripción + salto a línea del pedido

### Criterios de aceptación
- [ ] Hook en flujo de envío / Guardar borrador / export a proveedor (definir touchpoint)
- [ ] Copia clara en Bs o USD según MonedaTrabajo
- [ ] Audit trail (justificación o meta)
