## Parent

ADR-0016 ValidarMinimosProveedor USD

## What to build

Post-Generar step: evaluate supplier USD minimums, boost coverage % on that supplier's SKUs only, accept subminimum or reject (2nd best barra→Grupo / orphan), queue + cascade, dual audit trail.

## Acceptance criteria

- [x] Pure core + unit tests (queue, boost, panel, accept, reject)
- [x] `POST /api/pedidos/validar-minimos` (evaluar|recalcular|aceptar|rechazar)
- [x] Loader `ProveedorConfig.MontoMinimoPedidoUSD`
- [x] FE panel after Generar
- [x] Live smoke API: Generar Sencillo → Evaluar (cola con `#ProveedorID`; 2026-07-14)
- [x] Live smoke FE: headless Chrome `modulo_pedidos` → Generar Sencillo → Evaluar (cola `#11…`; 2026-07-14)
- [x] FE proxy path: Generar → Evaluar → Recalc (`requiere_panel`) → Aceptar (cascade a `#12`)

## Blocked by

None

Status: done
