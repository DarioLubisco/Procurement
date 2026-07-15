# Layout full-width Pedidos + Criterios whitelist (ADR-0020)

Tras grill 2026-07-15: el módulo Pedido de Moléculas deja la columna fija de categorías (320px) y pasa a **full-width**. Categorías se editan en modal; el formulario se pliega tras Generar; CriteriosAgrupacion expone la whitelist completa (10 attrs) alimentada end-to-end.

**Status:** accepted

## Layout

1. Barra `Categorías · N` + **Editar** → modal centrado (patrón `.modal` del suite).
2. Checks de categorías **instantáneos**; Listo solo cierra.
3. Stack vertical: barra → config → resultados.
4. Tras Generar exitoso: **config colapsada** (“Editar configuración”).
5. Excel/resta en `<details>` **Opciones avanzadas / contingencia** (cerrado).
6. Tablas Comparativa/Propuesto: `max-height: min(60vh, 640px)`.

## CriteriosAgrupacion

- Whitelist = `ATRIBUTOS_VALIDOS` (alineada a `RotacionGrupal_Atributos`): 10 campos.
- Default checked = 5 de ADR-0008.
- Cualquier subconjunto no vacío ⊆ whitelist.
- FE: `GET /api/rotacion-grupal/atributos`.
- Backend: `pedidos.sql` + mapper cargan los 10; `resolve_criterios_agrupacion` valida.

## Consequences

- ADR-0008 se mantiene (defaults); este ADR amplía UI + carga de attrs extra.
- Sin los CASTs extra en SQL, marcar origen/fabricante/etc. agruparía vacío.
