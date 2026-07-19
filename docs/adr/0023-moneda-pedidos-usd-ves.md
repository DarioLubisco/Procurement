# Moneda Pedidos USD/VES

**Status:** accepted  
**Related:** `Procurement.ProveedorConfig.MonedaOferta`, `dbo.dolartoday`, ADR-0026

## Decision

1. Motor Generar scorea y persiste cantidades/precios siempre en **USD**.
2. `MonedaOferta` por lab (`USD` | `VES`). Si `VES`, `precio / dolarbcv` (BCV de `dbo.dolartoday`) antes de desvío/scoring.
3. `MonedaTrabajo` es solo display FE (USD o Bs), no cambia el motor.

## Consequences

- Labs con precios en bolívares mal etiquetados como USD distorsionan desvío y ranking (ej. NENA/ITS/GAMA → deben ser `VES`).
- ZAKIPHARMA ya opera en VES.
