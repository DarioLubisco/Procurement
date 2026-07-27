Status: ready-for-agent

# 14-enmendar-adr-0007-context

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

After the productive path ships, amend ADR-0007 (and CONTEXT Pedido / PerfilPedido wording) so domain docs match generación única: first Generar may run ≤3 perfiles; Baseline fixed/shared; Intermedio/Avanzado re-gen remains per active perfil.

## Acceptance criteria

- [ ] ADR-0007 updated or superseded with explicit status and link to this PRD
- [ ] CONTEXT.md Pedido / PerfilPedido / PedidoPropuesto Avoid lines no longer mandate single-Sencillo-only first Generar
- [ ] PedidoBaseline “sin motor” and Comparativa grain (ADR-0004) remain intact in docs
- [ ] No silent contradiction left between ADR-0007 and shipped UI

## Blocked by

- 13-retirar-ui-sencillo-regenerar

## Comments
