# ADR-0021: SAINSTA no-medicina alineada a taxonomía MDM (3 niveles)

## Context

Pedidos lee `dbo.SAINSTA` (`InsPadre`). El árbol legacy no-medicina no coincidía con
la taxonomía del orchestrator de clasificación (`taxonomias_v2` /
`Procurement.Taxonomia`: Dominio → Categoría → Subcategoría).

Farma Pronto se descartó en grill 2026-07-22 como fuente incorrecta.

## Decision

1. **Fuente:** `taxonomias_v2` (autoridad en Clasificacion-Medicamentos); sync a priori
   a `Procurement.Taxonomia`; orchestrator arma prompt desde BD; CI drift-check.
2. **Árbol Softland 3 niveles** con `Descrip` exactos MDM para los 5 dominios
   no-`MEDICAMENTO_ALOPATICO`.
3. **Medicinas Softland:** no tocar.
4. **CodInst fijos:** `LEGACY_NO_MEDICINA=2999`; dominios `3000–3099`; categorías
   `3100–3199`; subcategorías `3200–3999`.
5. **Fase 1:** upsert MDM + reparent legacy bajo `LEGACY_NO_MEDICINA`. Remap
   `SAPROD` solo si existen columnas MDM (preferir subcategoría).
6. **Fase 2:** eliminar nodos legacy (tarea Notion).

## Consequences

- Modal Pedidos muestra Medicinas + 5 dominios MDM + cajón LEGACY hasta fase 2.
- Procurement importa artifact de taxonomía; Clasificacion-Medicamentos es dueño.
- PR tooling: `backend/data/sainsta_mdm_taxonomy.json`,
  `scripts/migrate_sainsta_mdm.py`, `sql/013_sainsta_mdm_non_medicine.sql`.
