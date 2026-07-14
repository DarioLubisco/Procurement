## Parent

ADR-0016 ValidarMinimosProveedor USD

## What to build

Post-Generar step: evaluate supplier USD minimums, boost coverage % on that supplier's SKUs only, accept subminimum or reject (2nd best barra→Grupo / orphan), queue + cascade, dual audit trail.

## Acceptance criteria

- [x] Pure core + unit tests (queue, boost, panel, accept, reject)
- [x] `POST /api/pedidos/validar-minimos` (evaluar|recalcular|aceptar|rechazar)
- [x] Loader `ProveedorConfig.MontoMinimoPedidoUSD`
- [x] FE panel after Generar
- [ ] Live smoke with seeded minimo on DROCERCA (ops)

## Blocked by

None

Status: ready-for-agent
