# HANDOFF: SAINSTA MDM fase 1 — apply local / private worker

## 1. PROPÓSITO DE ESTA SESIÓN

Aplicar en SQL Server (VPN Tailscale) la migración **fase 1** de categorías no-medicina en `dbo.SAINSTA`, verificar el árbol, y dejar listo el camino a remap/fase 2. **No** reabrir el grill ni reintroducir Farma Pronto.

Repo: `DarioLubisco/Procurement`  
Branch: `cursor/recategorizar-sainsta-pronto-c333`  
Base: `main`

## 2. CONTEXTO RELEVANTE (decisiones vigentes)

Fuente de taxonomía = orchestrator MDM `taxonomias_v2` (Clasificacion-Medicamentos), **no** Farma Pronto.

| Decisión | Valor |
|----------|--------|
| Árbol | 3 niveles: Dominio → Categoría → Subcategoría |
| `Descrip` | Strings **exactos** MDM |
| Medicinas Softland | **No tocar** |
| Dominios a insertar | `COSMETICO_CUIDADO_PERSONAL`, `MATERIAL_MEDICO_INSUMO`, `MISCELANEO`, `PRODUCTO_NATURAL_HOMEOPATICO`, `SUPLEMENTO_VITAMINICO` |
| CodInst | `LEGACY_NO_MEDICINA=2999`; dominios `3000–3099`; cats `3100–3199`; subs `3200–3999` |
| Legacy | Reparent bajo `LEGACY_NO_MEDICINA` (fase 1); **delete en fase 2** |
| Remap `SAPROD` | Solo si existen columnas MDM `dominio/categoria/subcategoria`; preferir subcategoría |
| Sync a priori | Archivo → `Procurement.Taxonomia`; orchestrator lee BD; CI drift (otro repo, paralelo) |

Detalle: `.scratch/recategorizacion-sainsta-pronto/GRILL_DECISIONS.md`  
ADR: `docs/adr/0021-sainsta-mdm-non-medicine.md`

### Notion

- Grill: https://app.notion.com/p/Grill-SAINSTA-no-medicina-taxonom-a-MDM-decisiones-3a5c22d58177816290eec89901254809
- Delete fase 2 (+ lista categorías): https://app.notion.com/p/Eliminar-nodos-SAINSTA-legacy-no-medicina-2-instancia-3a5c22d58177814cae60e87e152038d2
- Apply chore: https://app.notion.com/p/APPLY-SAINSTA-MDM-fase-1-private-worker-VPN-3a5c22d58177816f8f39e9664b9b3f11

## 3. ESTADO ACTUAL

**Hecho en cloud agent (código en branch):**
- `backend/data/taxonomias_v2.txt` + `sainsta_mdm_taxonomy.json` (5/36/98)
- `backend/services/sainsta_mdm_taxonomy.py`
- `scripts/migrate_sainsta_mdm.py` (`validate|plan|render-sql|apply`)
- `sql/013_sainsta_mdm_non_medicine.sql`
- Tests: `tests/backend/test_sainsta_mdm_taxonomy.py` — 9 passed
- Farma Pronto **eliminado** del branch

**NO hecho (bloqueado en cloud público):**
- Apply a `EnterpriseAdmin_AMC` — TCP llega a `100.94.5.108:49751` / ZT pero **handshake TDS y SSH se resetean** (firewall). Hace falta agent **local / private worker en Tailscale**.

## 4. PENDIENTES PARA EL AGENTE LOCAL (orden)

### P0 — Apply fase 1 (esta sesión)

1. Checkout branch y credenciales:
   ```bash
   git fetch origin && git checkout cursor/recategorizar-sainsta-pronto-c333
   # Cargar synapse.credentials o .env con DB_*
   # Preferido: DB_SERVER=100.94.5.108,49751  (o 100.94.5.108\efficacis3)
   # DB_DATABASE=EnterpriseAdmin_AMC  DB_USERNAME=sa
   ```
2. Validar + dry-run:
   ```bash
   python3 scripts/migrate_sainsta_mdm.py validate
   python3 scripts/migrate_sainsta_mdm.py plan   # live SAINSTA
   python3 scripts/migrate_sainsta_mdm.py apply --dry-run
   ```
3. Apply:
   ```bash
   python3 scripts/migrate_sainsta_mdm.py apply --execute
   ```
4. Verificar:
   ```sql
   SELECT CodInst, Descrip, InsPadre FROM dbo.SAINSTA
   WHERE CodInst IN (2, 2999, 3000, 3001, 3002, 3003, 3004)
      OR CodInst BETWEEN 3000 AND 3999
   ORDER BY CodInst;

   -- Medicinas sigue raíz
   SELECT COUNT(*) AS medicinas_subtree
   FROM dbo.SAINSTA WHERE Descrip = N'Medicinas' AND ISNULL(InsPadre,0)=0;

   -- Legacy parked
   SELECT COUNT(*) FROM dbo.SAINSTA WHERE InsPadre = 2999;
   ```
5. Smoke FE/API: `GET /api/pedidos/categories` → Medicinas + 5 dominios + `LEGACY_NO_MEDICINA`.
6. Marcar Notion APPLY como Done; anotar conteos.

**Skill SQL Saint:** no `DROP`/`TRUNCATE`/`DELETE`/`ALTER TABLE` ad-hoc. El script de migrate ya usa `BEGIN TRAN`, WHERE, preserve Medicinas, backups `Procurement.SAINSTA_Backup_MDM` / `SAPROD_CodInst_Backup_MDM`.

### P1 — Paralelo (otro agente / repo Clasificacion-Medicamentos)

- Garantizar sync a priori: `taxonomias_v2` → `Procurement.Taxonomia`; orchestrator lee **solo** BD; CI falla si drift.

### P2 — Después del apply (no en el primer apply)

- Columnas MDM `dominio/categoria/subcategoria` en equivalencias + backfill clasificador.
- Remap `SAPROD` (ya está gated en el SQL si las columnas existen).
- **Fase 2:** eliminar nodos bajo `LEGACY_NO_MEDICINA` (lista en Notion / `sainsta-a-eliminar.md`). Preconditions: 0 `SAPROD` apuntando a esos CodInst.

## 5. ARCHIVOS CLAVE

| Path | Rol |
|------|-----|
| `scripts/migrate_sainsta_mdm.py` | CLI apply |
| `sql/013_sainsta_mdm_non_medicine.sql` | SQL generado |
| `backend/data/sainsta_mdm_taxonomy.json` | CodInst + árbol |
| `backend/data/taxonomias_v2.txt` | Copia autoridad |
| `.scratch/recategorizacion-sainsta-pronto/GRILL_DECISIONS.md` | Decisiones |
| `.scratch/recategorizacion-sainsta-pronto/sainsta-a-eliminar.md` | Lista fase 2 |

## 6. ERRORES / BLOQUEOS CONOCIDOS

- Cloud agent público: **no** puede completar TDS ni SSH a srv-sql-amc / Debian Synapse.
- Credenciales SSOT: `synapse.credentials` (`DB_*`). Fallback visto en repo N8N `Imp_Inv_Dronena.env` (mismo `sa` / AMC).
- `InsPadre` es **columna** de `SAINSTA`, no tabla `dbo.inspadre`.
- No usar Farma Pronto ni `sainsta_pronto_*` (borrados).

## 7. CRITERIO DE ÉXITO (sesión local)

- [ ] `apply --execute` OK en staging/prod acordado
- [ ] Medicinas intacta; 5 dominios + cats/subs presentes; legacy bajo 2999
- [ ] `/api/pedidos/categories` coherente
- [ ] Notion APPLY → Done con conteos
- [ ] No delete fase 2 en esta sesión salvo orden explícita

## 8. PROMPT SUGERIDO PARA EL AGENTE LOCAL

```
Handoff: lee .scratch/recategorizacion-sainsta-pronto/HANDOFF_APPLY_LOCAL.md
Branch cursor/recategorizar-sainsta-pronto-c333.
Usá synapse-credentials-resolver + skill SQL Saint.
Ejecutá fase 1: migrate_sainsta_mdm.py apply --execute contra EnterpriseAdmin_AMC,
verificá SAINSTA y GET /categories, actualizá Notion APPLY.
No borres legacy (fase 2). No toques Medicinas. No uses Farma Pronto.
```
