# Backorder desde tablas; subtraction_files como soporte eventual

El backorder (cantidades ya pedidas / en tránsito / pendientes) se toma de **tablas dedicadas en el backend**, no del upload Excel. `subtraction_files` queda como **sistema de soporte eventual** (contingencia), no como FiltroOperativo de primer nivel ni criterio de paridad P1.

**Status:** accepted

## Consequences

- FiltrosOperativos = categorías, genéricos/marcas, umbral, tope de líneas (+ Cobertura / CriteriosAgrupacion aparte).
- Integrar lectura de tablas de backorder; **restar en Baseline y Propuesto** (mismo dato).
- En este repo aún no aparece el nombre de esas tablas — documentar schema en implementación.
- Enmiendas que listaban subtraction_files como contrato operativo quedan parcialmente obsoletas en ese punto.
