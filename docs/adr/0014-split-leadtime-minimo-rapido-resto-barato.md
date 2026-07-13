# SplitLeadTime: mínimo al rápido, resto al barato

**Disparo:** `Existen` (stock farmacia) menor que `rot_diaria × LT_días` del proveedor rápido.

**Si dispara:**
1. Mínimo al rápido = `max(rot×LT, MOQ_proveedor)`, **topeado por** `stock_proveedor` de la oferta rápida.
2. Resto → proveedor más barato (LeadTime malo).

**MOQ:** por **proveedor** (grill Q28 = B). No usar `SAPROD.Minimo` ERP como sustituto. Fuente a modelar/cargar (tabla o campo en catálogo de ofertas / proveedor); hoy no existe en el pipeline.

**Status:** accepted

## Consequences

- Crear/alimentar dato MOQ por proveedor antes de que `max(..., MOQ)` haga algo real; hasta entonces el término existe en dominio pero la impl puede degradar a solo rot×LT con log/ADR.
- PedidoPropuesto puede tener 2+ líneas del mismo producto con distinto proveedor.
- JustificacionDelta explica disparo Existen vs rot×LT, MOQ aplicado y tope stock_proveedor.
