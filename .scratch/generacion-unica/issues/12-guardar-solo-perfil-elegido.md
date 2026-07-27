Status: ready-for-agent

# 12-guardar-solo-perfil-elegido

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

Guardar persists only the active/chosen perfil (BorradorPedidos / PedidoDefinitivo path); batch siblings are not auto-saved.

## Acceptance criteria

- [ ] Guardar disabled or no-ops until a perfil is chosen
- [ ] Only the chosen perfil’s lines/knobs/Comparativa snapshot are persisted
- [ ] No second/third borrador created for sibling slots
- [ ] Knobs snapshot matches the chosen (possibly re-gen’d) perfil

## Blocked by

- 07-fe-clic-columna-comparativa

## Comments
