# Recategorización SAINSTA ↔ taxonomía MDM (no medicinas)

## Goal

Árbol Softland `SAINSTA` de **3 niveles** (Dominio → Categoría → Subcategoría) para
productos no-medicina, alineado a `taxonomias_v2` del orchestrator. Medicinas intacta.

## Grill

Ver `GRILL_DECISIONS.md` y Notion:
https://app.notion.com/p/Grill-SAINSTA-no-medicina-taxonom-a-MDM-decisiones-3a5c22d58177816290eec89901254809

## Artefactos

- `backend/data/taxonomias_v2.txt` (copia canónica importada)
- `backend/data/sainsta_mdm_taxonomy.json`
- `backend/services/sainsta_mdm_taxonomy.py`
- `scripts/migrate_sainsta_mdm.py`
- `sql/013_sainsta_mdm_non_medicine.sql`

## Runbook

```bash
python3 scripts/migrate_sainsta_mdm.py validate
python3 scripts/migrate_sainsta_mdm.py plan --sainsta-json <dump.json>
python3 scripts/migrate_sainsta_mdm.py render-sql
# staging:
python3 scripts/migrate_sainsta_mdm.py apply --execute
```

## Fase 2

Eliminar legacy bajo `LEGACY_NO_MEDICINA` — Notion + `issues/02-eliminar-sainsta-legacy.md`.
