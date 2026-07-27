Status: ready-for-agent

# 13-retirar-ui-sencillo-regenerar

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

Remove the primary-path duplicate Generar Sencillo → Regenerar Definitivo workflow from the productive page so generación única is the happy path; leave prototype_compare_presets artifacts untouched.

## Acceptance criteria

- [ ] Primary UI no longer presents the old serial Sencillo-then-only-Regenerar compare story as the main path
- [ ] New Generar → grilla → Comparativa → comparador/mínimos/guardar path remains reachable
- [ ] `prototype_compare_presets.js`, `.wf3.js`, and NOTES are not deleted
- [ ] Smoke: one full happy path without using retired controls

## Blocked by

- 07-fe-clic-columna-comparativa
- 10-comparador-regen-activo
- 11-validar-minimos-post-eleccion
- 12-guardar-solo-perfil-elegido

## Comments
