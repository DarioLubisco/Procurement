# 01 — Taxonomía Farma Pronto no-medicina + migrador SAINSTA

Status: ready-for-agent

## What to build

Fuente canónica JSON de categorías Farma Pronto (excluyendo ATC/medicamento),
padres sintéticos para `InsPadre`, planificador/SQL renderer, CLI dry-run/apply,
fixture SQL, y tests.

## Acceptance

- [x] `sainsta_pronto_taxonomy.json` sin huérfanos no-medicina
- [x] Medicinas marcada preserve; hojas Pronto no incluyen ATC
- [x] `plan_sainsta_rewrite` retira no-medicina a Anulados y remapea SAPROD
- [x] `scripts/migrate_sainsta_pronto.py validate|plan|render-sql`
- [x] Tests unitarios en `tests/backend/test_sainsta_pronto_taxonomy.py`
- [ ] Apply contra SQL Server staging/prod (humano — credenciales)

## Comments

- Nota: `InsPadre` es **columna** de `dbo.SAINSTA`, no tabla aparte.
- Catálogo tomado de `https://grupofarmapronto.com/wp-json/wp/v2/product_cat`.
