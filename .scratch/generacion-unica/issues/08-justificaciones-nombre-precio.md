Status: resolved

# 08-justificaciones-nombre-precio

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

Primary JustificacionDelta presentation shows product name + proveedor + precio; BARRA detail is secondary.

## Acceptance criteria

- [x] Primary cell/summary line is commercially readable (nombre, proveedor, precio)
- [x] BARRA appears as secondary detail (hover/acordeón/secondary line)
- [x] Structured `justificacion_factores` model from ADR-0019 is not flattened away
- [x] Sucedáneo / code-change cases still declare the change

## Blocked by

- 07-fe-clic-columna-comparativa

## Answer

FE `formatJustificacionPrimaryHtml`: primary = [Sucedáneo ·] nombre · proveedor · $precio; secondary `justificacion-barra` + factor titles (`justificacion_delta`). Accordion rivales/hermanos: `competencia-nombre` + proveedor + precio first, `competencia-barra` secondary. Factors model untouched.

## Comments
