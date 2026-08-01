Status: resolved

# 11-validar-minimos-post-eleccion

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

After choosing a perfil, an alarm/CTA offers ValidarMinimosProveedor; opening it runs the existing mínimo flow on that perfil only — never inline as part of batch completion.

## Acceptance criteria

- [x] Batch completion does not force ValidarMinimos UI
- [x] After profile selection, alarm/banner + button appear when mínimos apply
- [x] Button opens the existing modal/panel flow (cola, %, Aceptar/Rechazar)
- [x] Evaluar operates on the active perfil GenerarResult only
- [x] ADR-0016 behaviours preserved

## Blocked by

- 07-fe-clic-columna-comparativa

## Answer

`stashBatchResult` never calls VM. Column hydrate → `showValidarMinimosAlarm`. Existing Evaluar/panel ADR-0016. `syncActiveBatchSlotFromLastGenerar` keeps siblings + shared Baseline.

## Comments
