Status: resolved

# 09-modal-clic-derecho-rivales

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

Right-click on a propuesta BARRA opens a modal with Original | Rivales blocks (desc + proveedor + precio) driven by knob-sized payload; comprador can apply a replacement on the active Comparativa.

## Acceptance criteria

- [x] Context menu / right-click on propuesta BARRA opens the modal
- [x] Blocks show Original (hermanos/original) and Rivales with required commercial fields
- [x] Offer counts respect the three knobs
- [x] Applying a choice updates the active perfil Comparativa/Propuesto line coherently
- [x] Left-click behaviour of the grid/Comparativa remains unchanged

## Blocked by

- 04-config-pedido-knobs-ui
- 05-payload-hermanos-rivales
- 07-fe-clic-columna-comparativa

## Answer

`#reemplazoModal` + `openReemplazoModal` on `contextmenu` of `.barra-propuesto-cell`. Original = `oferta_baseline` + `hermanos_reemplazables`; Rivales = nested `ofertas[]` sliced by `top_n_*` / `ofertas_por_rival`. `applyReemplazoOffer` updates Comparativa + PedidoPropuesto (and active batch slot). Left-click justificacion accordion unchanged.

## Comments
