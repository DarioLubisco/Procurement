Status: resolved

# 10-api-fe-generar-sencillo

Parent: `.scratch/parametrizacion-pedidos/PRD.md`  
Also listed in: `tickets.md`

## API + FE Generar Sencillo (Comparativa + Propuesto con proveedor)

**What to build:** UI productiva Generar usa el seam unificado: muestra ComparativaCantidades y PedidoPropuesto con proveedor; permite Cobertura, FiltrosOperativos, CriteriosAgrupacion editables, PresetSencillo y presupuesto opcional. Excel BARRA×CANTIDAD deja de ser la salida humana primaria de esta fase.

**Blocked by:** DistribucionParcial multi-factor + sucedáneos en Comparativa; Presets Normal y Agresivo; Backorder desde tablas + resta igual en ambos lados

- [x] Productive Generar calls unified path (not legacy-only Excel generator)
- [x] Comprador sees Comparativa columns: Baseline BARRA/desc/qty, Propuesto BARRA/desc/qty, JustificacionDelta
- [x] Comprador sees Propuesto with proveedor on first Generar
- [x] First Generar UI is Sencillo only (preset + cobertura + filtros + criterios + optional budget)
- [x] CriteriosAgrupacion editable before Generar; effective list sent on request

## Implementation notes

- Adapter: `analytics_engine/core/generar_sencillo_api.py`
- HTTP: `POST /api/pedidos/generar-sencillo` (`backend/routers/generar_sencillo.py`)
- DB loaders: `backend/services/generar_sencillo_loaders.py` (catalog + Mercado_Vivo when body omits injection)
- FE: `frontend/modulo_pedidos.html` + `js/app_pedidos.js` — primary Generar → Comparativa/Propuesto; Excel legacy secondary
