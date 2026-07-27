Status: resolved

# 12-guardar-solo-perfil-elegido

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

Guardar persists only the active/chosen perfil (BorradorPedidos / PedidoDefinitivo path); batch siblings are not auto-saved.

## Acceptance criteria

- [x] Guardar disabled or no-ops until a perfil is chosen
- [x] Only the chosen perfil’s lines/knobs/Comparativa snapshot are persisted
- [x] No second/third borrador created for sibling slots
- [x] Knobs snapshot matches the chosen (possibly re-gen’d) perfil

## Blocked by

- 07-fe-clic-columna-comparativa

## Answer

`canGuardarChosenPerfil` + `refreshGuardarBorradorGate`: batch requires `activeBatchPerfilId`. `buildGuardarBorradorPayload` sends one `pedido_propuesto` + Comparativa + `parametros.perfil_id` / `knobs_efectivos`. Single `POST /guardar-borrador`.

## Comments
