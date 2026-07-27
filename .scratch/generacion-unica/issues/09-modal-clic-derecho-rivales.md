Status: ready-for-agent

# 09-modal-clic-derecho-rivales

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

Right-click on a propuesta BARRA opens a modal with Original | Rivales blocks (desc + proveedor + precio) driven by knob-sized payload; comprador can apply a replacement on the active Comparativa.

## Acceptance criteria

- [ ] Context menu / right-click on propuesta BARRA opens the modal
- [ ] Blocks show Original (hermanos/original) and Rivales with required commercial fields
- [ ] Offer counts respect the three knobs
- [ ] Applying a choice updates the active perfil Comparativa/Propuesto line coherently
- [ ] Left-click behaviour of the grid/Comparativa remains unchanged

## Blocked by

- 04-config-pedido-knobs-ui
- 05-payload-hermanos-rivales
- 07-fe-clic-columna-comparativa

## Comments
