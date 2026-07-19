# PDR en Generar (stock no confiable)

`stock_disponible` bajo a menudo es ruido (ej. 3 unidades que no existen). Ya existe
`Analitica.Mercado_Vivo_PDR` (Probabilidad de Disponibilidad Real) con semáforo. El motor
de Generar solo hacía `min(qty, stock)` e ignoraba PDR.

**Status:** accepted  
**Grill:** 2026-07-18  
**Related:** ADR-0022 (justificación / rivales), `Analitica.PDR_Config`

## Decision

1. Loader de ofertas lee **`Analitica.Mercado_Vivo_PDR`** (no `Mercado_Vivo` crudo) y expone `pdr`, `pdr_semaforo`.
2. Semáforos que cambian el motor:
   - **`NO_CONFIABLE`:** filtrar **antes** del score (como stock 0).
   - **`BAJA`:** no usar stock como tope (`min(qty, stock)` omitido) **y** `score × max(0.5, pdr)`.
   - **`MODERADA` / `ALTA`:** passthrough.
3. Si `pdr` / `pdr_semaforo` faltan → **fail-open** (comportamiento pre-PDR).
4. Si tras filtrar `NO_CONFIABLE` no queda oferta → `sin_oferta` + factor `pdr` listando excluidas (proveedor · pdr · semáforo). No ensuciar rivales en el caso normal.
5. Justificación UI: factor chip **`pdr`** + badge `[PDR:SEMÁFORO]` en cabecera Oferta; rivales pueden llevar `pdr_semaforo` si existe.

## Consequences

- DIAPOST/MASTRANTO_C (`BAJA`, stock 3) deja de recortar qty baseline solo por stock falso; score baja proporcional al PDR (piso 0.5).
- Labs enteros no se “matan”: solo filas `NO_CONFIABLE`.
- Calibración de pesos sigue en `PDR_Config` / n8n calibrador; Generar no duplica la fórmula.
- Gate stock×PPP por corrida: ADR-0026 (knobs FE; no reescribe la vista).
