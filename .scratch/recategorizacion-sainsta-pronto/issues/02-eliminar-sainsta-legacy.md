# 02 — Eliminar nodos SAINSTA legacy no-medicina (2ª instancia)

Status: ready-for-human

Type: task

## Notion (pendiente auth MCP)

**Título sugerido:** Eliminar nodos SAINSTA legacy no-medicina (2ª instancia)

**Descripción para pegar en Notion:**

---

Segunda instancia: **después** de (1) sync `taxonomias_v2` → `Procurement.Taxonomia` con CI drift-check, (2) insertar árbol MDM 3 niveles en `SAINSTA` (5 dominios no-medicina), (3) remapear `SAPROD.CodInst` donde MDM ya tenga dominio/categoría/subcategoría.

**Preservar:** subárbol Softland **Medicinas** (no tocar).

**Eliminar** estos nodos actuales (nombres del árbol vivo; CodInst de fixture/aprox — revalidar IDs con `SELECT CodInst, Descrip, InsPadre FROM dbo.SAINSTA` antes del delete):

### Árbol a eliminar

- Alimentos y Bebidas
- Anulados o Eliminadas
  - xx, xxx, xxx, xxxxx, xxxxxxxx
- Artículos para el Hogar
  - Otros Misceláneos
  - Productos de Limpieza
  - Repelentes de Insectos
- Bebidas (huérfano InsPadre roto en vivo)
- Cosméticos
  - Fotoprotección
- Cuidado Personal
  - Cuidado Corporal y Baño
  - Cuidado Femenino
  - Desodorantes
  - Higiene Bucodental
- Cuidado de Bebés y Niños
  - Alimentación y Fórmulas Infantiles
  - Pañales y Toallitas
- Cuidado de la Piel
- Cuidado de la Salud en Casa
- Cuidado del Cabello
- Equipos Medicos
  - Artículos Ortopédicos
  - Consumibles Médicos
  - Descartables
  - Equipos de Monitoreo de Salud
  - Ortopedicos
- Infantil
  - Accesorios Infantiles
  - Alimentación Infantil
  - Cosmeticos
  - Cuidado del Adulto
  - Cuidados del bebe
  - General
  - Juguetes y Entretenimiento
  - Ropa y Textiles
- Libreria
- Pañales
- REACTIVOS Y LABORATORIO
  - Pruebas Rápidas de Diagnóstico
  - Reactivos Químicos
- SERVICIOS GENERALES
- Suministros de Primeros Auxilios
  - Insumos Descartables
  - Material de Curación
- Suplementos Nutricionales
  - Alimentos y Bebidas Dietéticas
  - Nutrición Deportiva
  - Vitaminas y Minerales

**Conteo:** ~53 nodos no-Medicinas (sobre ~64 totales). Medicinas + hijos ≈ 11.

**Preconditions delete:** 0 filas `SAPROD` apuntando a esos CodInst (tras remap MDM).

Lista detallada con CodInst (fixture): ver `sainsta-a-eliminar.md` en el repo Procurement.

---

## Grill

- Q8: eliminar en 2ª instancia (no end-state de fase 1)
- Notion MCP `needsAuth` en cloud agent — descripción lista arriba

## Comments

- 2026-07-22: usuario pidió anotar categorías actuales a eliminar en descripción Notion
