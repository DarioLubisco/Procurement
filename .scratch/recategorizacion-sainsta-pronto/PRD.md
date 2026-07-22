# Recategorización SAINSTA → Farma Pronto (no medicinas)

## Goal

Reescribir las instancias **no medicina** de `dbo.SAINSTA` (jerarquía vía columna
`InsPadre`; no existe tabla `dbo.InsPadre`) para que las hojas coincidan con las
categorías de producto de **Farma Pronto**, sin tocar el subárbol **Medicinas**.

## Background

- Pedidos lee categorías de `dbo.SAINSTA` (`CodInst`, `Descrip`, `InsPadre`).
- El árbol actual (≈64 filas) mezcla raíces duplicadas, huérfanos y basura bajo Anulados.
- Farma Pronto publica ~100 `product_cat` planas (WooCommerce); las ATC/medicamento
  se excluyen porque Medicinas ya cubre ese universo en Softland.

## Scope

**In**
- Insertar padres sintéticos + hojas Farma Pronto (rango CodInst 2100+/2200+).
- Retirar nodos no-medicina hacia `Anulados o Eliminadas` (CodInst 27).
- Remapear `dbo.SAPROD.CodInst` de categorías retiradas → hojas Pronto (tabla de mapeo).
- Tooling offline + SQL generable; tests unitarios sin BD.

**Out**
- Reescribir hijos de Medicinas / ATC Pronto.
- Ejecutar la migración en producción desde este PR (requiere `.env` + ventana de cambio).
- Matching por código de barras contra el catálogo Pronto (SKU vacío en su API pública).

## Source of truth

- `backend/data/sainsta_pronto_taxonomy.json`
- Loader/plan/SQL: `backend/services/sainsta_pronto_taxonomy.py`
- CLI: `scripts/migrate_sainsta_pronto.py`
- SQL generado (fixture): `sql/013_sainsta_pronto_non_medicine.sql`

## Acceptance

1. `python3 scripts/migrate_sainsta_pronto.py validate` → OK.
2. Plan sobre dump real de SAINSTA: Medicinas + descendientes en `preserve_codinsts`.
3. Tras apply: `GET /api/pedidos/categories` muestra padres Pronto con hojas
   (`DESODORANTES`, `SHAMPOOS`, …) y Medicinas intacta.
4. Productos que estaban en categorías no-medicina apuntan a hojas nuevas.
5. Backup tables `Procurement.SAINSTA_Backup_Pronto` /
   `Procurement.SAPROD_CodInst_Backup_Pronto` creadas en el script.

## Runbook (humano / private worker)

```bash
# 1) Dump actual
# SELECT CodInst, Descrip, InsPadre FROM dbo.SAINSTA → JSON

python3 scripts/migrate_sainsta_pronto.py plan --sainsta-json /path/sainsta.json
python3 scripts/migrate_sainsta_pronto.py render-sql --sainsta-json /path/sainsta.json \
  -o sql/013_sainsta_pronto_non_medicine.sql

# 2) Revisar SQL; backup nativo Softland recomendado
python3 scripts/migrate_sainsta_pronto.py apply --execute   # solo con DB creds
```

## Open risks

- Softland puede tener columnas extra en `SAINSTA` (p.ej. `Nivel`, `DEsLote`); el script
  solo escribe `CodInst`/`Descrip`/`InsPadre` — `Nivel` puede quedar desfasado (ya lo estaba).
- Mapeo legacy→Pronto es semántico por nombre; productos mal clasificados hoy pueden
  heredar el sesgo. Refinar con inventario real tras el primer apply en staging.
