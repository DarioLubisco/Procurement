# 01 — Taxonomía MDM 3 niveles + migrador SAINSTA

Status: ready-for-agent

## What to build

Árbol Dominio→Categoría→Subcategoría desde `taxonomias_v2` (no Farma Pronto),
LEGACY_NO_MEDICINA, SQL/CLI/tests. Medicinas preservada.

## Acceptance

- [x] `sainsta_mdm_taxonomy.json` 5 dominios / 36 cats / 98 subs
- [x] CodInst ranges 2999 / 3000+ / 3100+ / 3200+
- [x] `scripts/migrate_sainsta_mdm.py validate|plan|render-sql`
- [x] SQL `013_sainsta_mdm_non_medicine.sql`
- [x] Tests `test_sainsta_mdm_taxonomy.py`
- [ ] Apply staging/prod (humano)
- [ ] CI sync Clasificacion-Medicamentos ↔ Procurement.Taxonomia (paralelo)

## Grill

Ver `GRILL_DECISIONS.md` + Notion grill page.
