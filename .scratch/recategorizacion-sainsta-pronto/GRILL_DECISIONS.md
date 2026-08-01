# Grill decisions — SAINSTA no-medicina ↔ taxonomía MDM

Fecha: 2026-07-22  
Fuente taxonomía: `Clasificacion-Medicamentos/taxonomias_v2.txt` (orchestrator), **no** Farma Pronto.

| Q | Decisión |
|---|---|
| 1 | Autoridad = taxonomía clasificador no-medicamentos (5 dominios ≠ MEDICAMENTO_ALOPATICO) |
| 2 | Árbol Softland **3 niveles**: Dominio → Categoría → Subcategoría |
| 3 | `SAPROD.CodInst` puede ser Categoría **o** Subcategoría (mixto) |
| 4 | Preferir **Subcategoría** cuando exista |
| 5 | Remap SAPROD solo donde MDM ya tenga dominio/categoría/subcategoría |
| 6–7 | Sync a priori: archivo repo → `Procurement.Taxonomia`; orchestrator lee BD; CI drift-check |
| 8 | Legacy se **elimina en 2ª instancia** (Notion task creada) |
| 9 | **No tocar** Medicinas Softland; sí sembrar completo los 5 dominios no-medicina a 3 niveles |
| 10 | `Descrip` = strings **exactos** MDM |
| 11 | Legacy bajo raíz colapsable `LEGACY_NO_MEDICINA` hasta delete |
| 12–15 | CodInst fijos: LEGACY=2999; Dominios 3000–3099; Cats 3100–3199; Subs 3200–3999 |
| 13 | Autoridad en Clasificacion-Medicamentos; Procurement importa; CI ambos |
| 14 | Fase 1: árbol SAINSTA ya; remap no-op hasta columnas MDM |

## Dominios a insertar

1. COSMETICO_CUIDADO_PERSONAL  
2. MATERIAL_MEDICO_INSUMO  
3. MISCELANEO  
4. PRODUCTO_NATURAL_HOMEOPATICO  
5. SUPLEMENTO_VITAMINICO  

## Fuera de alcance fase 1

- Reescribir Medicinas / MEDICAMENTO_ALOPATICO ATC  
- Delete físico legacy (fase 2)  
- Remap masivo sin columnas MDM  
