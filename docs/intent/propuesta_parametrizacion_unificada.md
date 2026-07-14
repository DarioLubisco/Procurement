# Propuesta Técnica: Unificación del Sistema de Parametrización de Pedidos

**Fecha:** 2026-07-08
**Estado:** Propuesta aprobada en diseño — pendiente de implementación
**Decisión de arquitectura adoptada:** Convergencia en un solo motor (Optimizer v3.2 absorbe al generador clásico)
**Alcance:** Documento de análisis y diseño. No implica cambios de código en esta fase.

> **Referencia:** Enmiendas 2026-07-10 (S4 muerto, paridad operativa, ADRs, roadmap ampliado) en
> [`propuesta_parametrizacion_unificada_enmiendas_2026-07-10.md`](./propuesta_parametrizacion_unificada_enmiendas_2026-07-10.md).
> Este archivo se conserva intacto como propuesta original del otro agente.

---

## 0. Resumen Ejecutivo

Hoy existen **dos motores de generación de pedidos** independientes (el clásico lineal de `backend/routers/pedidos.py` y el Optimizer v3.2 de `analytics_engine/`) apoyados en un tercer sistema de demanda agregada (Rotación Grupal) que el v3.2 **no consume, sino que duplica**. La parametrización está fragmentada en **5 fuentes distintas** (tabla `OptimizerConfig`, tabla `PDR_Config`, parámetros de request sin persistencia, columnas del ERP y constantes hardcodeadas), con defaults triplicados y al menos 3 parámetros muertos.

**Propuesta:**
1. **Back-end:** un solo motor (v3.2) donde el modo lineal clásico es un *perfil degenerado* de configuración; una sola fuente de demanda (`Procurement.RotacionGrupal`); una sola tabla de configuración con perfiles; núcleo reducido de ~12 parámetros activos.
2. **Front-end:** una pantalla de parametrización en `dashboard-react` con **3 niveles de exposición** — Sencillo (lenguaje de negocio), Intermedio (mixto negocio/matemático) y Avanzado (todos los parámetros).

---

## 1. Mapeo de Variables y Parámetros

### 1.1 Motor A — Optimizer v3.2 "Market-Driven" (`analytics_engine/`)

Pipeline de 6 capas (`analytics_engine/core/optimizer.py`): agrupamiento por molécula (PA+FF+Concentración), gap grupal (`calculate_group_gaps`, `optimizer.py:214`), reducción S4 (`optimizer.py:263`), presupuesto (`optimizer.py:307`), scoring F1–F5 (`optimizer.py:352-389`), distribución (`optimizer.py:396`), split por lead time (`optimizer.py:482`) y justificación (`optimizer.py:535`).

Configuración persistida en **`Procurement.OptimizerConfig`** (`sql/007_create_optimizer_config.sql`), cargada por perfil activo en `optimizer.py:592-637`. Perfil actual: *"Default Calibrated v3.1"*.

| # | Parámetro | Default | Rango (Pydantic) | Significado | Función que lo usa | Estado |
|---|-----------|---------|------------------|-------------|--------------------|--------|
| 1 | `amp_a` | 5.84 | 0.1–20.0 | Amplitud del amplificador exponencial `e^(a·\|d\|^b)` de cantidad ante descuentos | `exponential_amplifier` (`nonlinear.py:23`) | ✅ Activo |
| 2 | `amp_b` | 1.29 | 0.5–5.0 | Aceleración del amplificador (calibrado: −10%→1.5x, −20%→2.0x, −40%→6.0x) | ídem | ✅ Activo |
| 3 | `amp_max_increment_pct` | 500.0 | 50–2000 | Tope del amplificador (+500%) | ídem | ✅ Activo |
| 4 | `amp_floor_pct` | 0.2 | 0.0–1.0 | Piso del gap para productos caros (20%) | ídem | ✅ Activo |
| 5 | `s4_enabled` | 0 (off) | bool | Activa reducción de cobertura para SKUs costosos | `apply_s4_reduction` (`optimizer.py:263`) | ✅ Activo |
| 6 | `s4_porcentaje_base` | 0.66 | 0.1–1.0 | Cobertura reducida al 66% para elasticidad=0 | `s4_reduction_factor` (`nonlinear.py:205`) | ⚠️ Activo con bug conceptual (§2.9) |
| 7 | `monto_buffer_pct` | 20.0 | 0–100 | MontoMaximo = MontoEstimado × (1 + buffer) | `calculate_monto_maximo` (`nonlinear.py:285`) | ✅ Activo |
| 8 | `monto_days_reduction_pct` | 20.0 | 5–50 | % de reducción de días si se excede el monto | *(ninguna)* | ❌ **Muerto** — se carga (`optimizer.py:621`) pero nunca se aplica |
| 9 | `ext_max_dias_extra` | 21 | 0–60 | Máx. días extra de cobertura por oportunidad (F5) | `coverage_extension` (`nonlinear.py:170`) | ✅ Activo |
| 10 | `ext_umbral` | −0.10 | ≤ 0 | Desvío mínimo (−10%) para activar extensión | ídem | ✅ Activo |
| 11 | `ext_eta` | 4.0 | 1–15 | Agresividad de la extensión | ídem | ✅ Activo |
| 12 | `sust_kappa` | 5.0 | 1–20 | Expansión cuadrática del techo de sustitución | *(ninguna)* | ❌ **Muerto** — `quadratic_ceiling` (`nonlinear.py:136`) no se invoca en el pipeline |
| 13 | `opp_lambda` | 1.0 | 0.1–5.0 | Sensibilidad del score de oportunidad (F4) | `continuous_opportunity_score` (`nonlinear.py:98`) | ✅ Activo |
| 14 | `w1_elasticidad` | 0.15 | 0–1 | Peso F1 (elasticidad/sustitución) | `distribute_within_group` (`optimizer.py:417`) | ✅ Activo |
| 15 | `w2_demanda` | 0.25 | 0–1 | Peso F2 (velocidad de rotación) | ídem | ✅ Activo |
| 16 | `w3_posicionamiento` | 0.25 | 0–1 | Peso F3 (urgencia de stock) | ídem | ✅ Activo |
| 17 | `w4_oportunidad` | 0.20 | 0–1 | Peso F4 (oportunidad de precio) | ídem | ✅ Activo |
| 18 | `w5_extension` | 0.15 | 0–1 | Peso F5 (extensión de cobertura) | ídem | ✅ Activo |
| 19 | `dias_cobertura` | 21 | (request) | Horizonte de cobertura del pedido | `calculate_group_gaps` | ✅ Activo — **solo por request**, no está en la tabla (`models/optimization.py:129`) |
| 20 | `monto_maximo_override` | null | ≥ 0 | Presupuesto absoluto que anula el cálculo | `calculate_monto_maximo` | ✅ Activo — solo por request (`models/optimization.py:49`) |

### 1.2 Motor B — Generador clásico (`backend/routers/pedidos.py`)

Fórmula central (`pedidos.py:196`): `CANTIDAD = RotacionMensual × días / 30 − Existen`. **Ningún parámetro se persiste**: viven en el request y el front los guarda en `localStorage` (`frontend/js/app_pedidos.js:27-43`).

| # | Parámetro | Default | Significado | Referencia |
|---|-----------|---------|-------------|------------|
| 21 | `pedido_days` | 30 (UI) / 14 (fallback backend) | Días de cobertura del pedido | `pedidos.py:57,147-149` |
| 22 | `num_rows` | 5000 | Límite de líneas del Excel | `pedidos.py:58,112-113` |
| 23 | `umbral_rotacion` | 0.5 (UI) / 0.0 (backend) | Rotación mínima para incluir un SKU | `pedidos.py:61,226-230` |
| 24 | `include_generics` / `include_brands` | true/true | Filtro genéricos vs. marcas | `pedidos.py:64-65,100-107` |
| 25 | `nivel_rotacion` | `sku` | Nivel de demanda: `sku` (R1), `base` (R2), `custom` (dinámico) | `pedidos.py:66,152-194` |
| 26 | `atributos_custom` | — | Atributos de agrupación si `custom` (whitelist en `rotacion_grupal.py:32-38`) | `pedidos.py:67,162-174` |
| 27 | `forced_includes` | — | SKUs excluidos que el usuario fuerza | `pedidos.py:62,244-250` |
| 28 | `subtraction_files` | — | Archivos Excel de resta (pedidos en tránsito) | `pedidos.py:60,205-220` |
| 29 | `categories` | — | Filtro por categorías/instancias | `pedidos.py:59,136-140` |

### 1.3 Pesos PDR — `Analitica.PDR_Config` (`sql/001_create_schema_analitica.sql:15-29`)

Consumidos por la vista `Analitica.Mercado_Vivo_PDR` (`sql/003`), insumo directo del Motor A.

| # | Parámetro | Default | Significado |
|---|-----------|---------|-------------|
| 30 | `peso_vc` | 0.50 | Peso del componente Valor Comercial |
| 31 | `peso_cmp` | 0.35 | Peso del Costo de Mercado Promedio |
| 32 | `peso_ppp` | 0.15 | Peso del Precio Promedio Ponderado |
| 33 | `umbral_ppp` | 0.001 | Umbral de validez del PPP |

### 1.4 Columnas de BD que actúan como parámetros

| # | Columna | Rol | Referencia |
|---|---------|-----|------------|
| 34 | `por_aprobacion_equivalencias.elasticidad_demanda` | 0–5; entra a F1 y gatilla S4. Seed: genérico→4, marca→1; default en query `ISNULL(...,1)` | `sql/006:296-312`, `optimizer.py:63,83` |
| 35 | `ProveedorHorarioEntrega.*` | Lead times por día/hora de corte por proveedor | `optimizer.py:113-123` |
| 36 | `SAPROD.Minimo` / `SAPROD.Maximo` | Min/max del ERP — se seleccionan (`pedidos.sql:21-22`) pero **ya no gobiernan ningún cálculo** | Informativo/legado |
| 37 | `Procurement.Rotacion.RotacionMensual` | Demanda base de todo el sistema | Todos los motores |

### 1.5 Constantes hardcodeadas (no configurables hoy)

| # | Constante | Valor | Ubicación | ¿Debería ser parámetro? |
|---|-----------|-------|-----------|------------------------|
| 38 | Margen para costo de stockout | 30% del precio | `optimizer.py:524` | **Sí** (varía por negocio) |
| 39 | Lead time default sin dato | 48 h (24 h ante-corte) | `optimizer.py:501,508-512` | **Sí** |
| 40 | Ventana histórica larga / corta | 90 / 21 días | `optimizer.py:99,109` | Sí (nivel avanzado) |
| 41 | Frescura de RotacionGrupal | 15 min | `rotacion_grupal.py:41` | Opcional |
| 42 | Mínimo CANTIDAD=1 en export | 1 | `pedidos.py:258` | Sí (regla de negocio implícita) |
| 43 | Fallback `days` inválido | 14.0 | `pedidos.py:149` | No — eliminar con la unificación |
| 44 | Pesos scorecard proveedores | 6 pesos | `supplier_scorer.py:25-32` | Sí (misma tabla de config) |
| 45 | Detección de anomalías | `contamination=0.05`, `z=3.0`, `MIN_SNAPSHOTS=30` | `anomaly_detector.py` | Opcional (nivel avanzado) |

**Total: ~45 variables**, de las cuales solo 18 están en una tabla administrable, y de esas, 2 están muertas.

---

## 2. Análisis de Solapamientos y Redundancias

### 2.1 Cuatro cálculos independientes de la misma fórmula de demanda
La fórmula `necesidad = rotación × días / 30 − stock` está implementada 4 veces:

| Implementación | Ubicación | Nivel | Agregación |
|----------------|-----------|-------|------------|
| Columnas `Pedido9…Pedido120` precalculadas | `backend/queries/pedidos.sql:25-33` | SKU | `AVG(RotacionMensual)` |
| Cálculo dinámico en Python | `pedidos.py:196` | SKU o grupo | según nivel |
| Gap grupal del optimizer | `optimizer.py:239-244` | Grupo-molécula | `SUM` |
| SP de rotación grupal | `SP_RecalcularRotacionGrupal` (`sql/006:137-247`) | Grupo base | `SUM` |

Además, las columnas `PedidoN` de `pedidos.sql` **quedan sin uso** porque `pedidos.py:196` recalcula con días dinámicos.

### 2.2 El Motor A no consume `RotacionGrupal`
`SQL_CATALOG_FOR_GROUPS` (`optimizer.py:74-88`) recalcula rotación + stock por grupo on-the-fly desde `Rotacion` + `SAPROD`, duplicando exactamente lo que el SP de `sql/006` ya materializa en `Procurement.RotacionGrupal` con freshness controlada.

### 2.3 Agregación de rotación inconsistente
`pedidos.sql:6` usa `AVG(RotacionMensual)` por ítem; el SP y el optimizer usan `SUM`/valor directo. **Dos motores pueden sugerir cantidades distintas para el mismo SKU con los mismos datos.**

### 2.4 DDL duplicado de `OptimizerConfig`
`sql/007_create_optimizer_config.sql` vs `analytics_engine/init_db.py:66-135`. Riesgo de divergencia de esquema.

### 2.5 Defaults triplicados
Los mismos valores (5.84, 1.29, 0.66, 20.0…) viven en:
1. Los `DEFAULT` de la tabla SQL (`sql/007:13-40`)
2. Los `Field(default=...)` de `models/optimization.py:17-108`
3. Las firmas por defecto de las funciones en `nonlinear.py`

Cambiar la calibración exige tocar 3 lugares.

### 2.6 Parámetros muertos
- `monto_days_reduction_pct`: cargado (`optimizer.py:621`), nunca aplicado.
- `sust_kappa`: cargado (`optimizer.py:631`); `quadratic_ceiling` se importa (`optimizer.py:33`) pero no se ejecuta en el pipeline.
- `estimate_order_amount` (`nonlinear.py:257`): importada, no usada — el presupuesto se calcula inline en `calculate_budget`.
- `dias_sugeridos_reduccion` del modelo de respuesta nunca se llena.

### 2.7 Tres sistemas de pesos sin mecanismo común
F1–F5 (`OptimizerConfig`), PDR (`PDR_Config`, clave-valor) y scorecard de proveedores (`DEFAULT_WEIGHTS` en código). Tres formas de persistir "pesos", ninguna con UI.

### 2.8 Min/Max duplicado conceptualmente
`SAPROD.Minimo/Maximo` (ERP, estático) vs. min/max dinámico `rotación × días` (documentado como reemplazo en `docs/intent/optimizador_compras.md`), pero la query maestra aún los arrastra.

### 2.9 Bug conceptual de elasticidad / S4
S4 se activa con `elasticidad == 0` (`optimizer.py:276`), pero el seed de BD asigna 1 (marca) o 4 (genérico) y el default de query es `ISNULL(...,1)`. **S4 solo aplicaría a valores puestos manualmente en 0** — en la práctica está doblemente apagado (además `s4_enabled=0`).

### 2.10 Sin persistencia ni UI para el motor principal
`sql/007` declara *"Permite que el frontend y el backend compartan configuración"*, pero no existen endpoints CRUD para `OptimizerConfig` en `backend/routers/` ni referencia alguna en `frontend/` o `dashboard-react/`. La única UI de parametrización existente (`frontend/modulo_pedidos.html`) opera sobre el motor legado.

---

## 3. Propuesta de Simplificación del Back-end

### 3.1 Decisión: convergencia en un solo motor

**El Optimizer v3.2 absorbe al generador clásico.** El modo lineal clásico es matemáticamente un *caso degenerado* del v3.2:

| Componente v3.2 | Configuración "modo lineal" | Efecto |
|-----------------|----------------------------|--------|
| Amplificador exponencial | `amp_a` tal que amp=1 para todo desvío (o flag `amplifier_enabled=0`) | Sin amplificación por precio |
| S4 | `s4_enabled=0` | Sin reducción para costosos |
| Extensión F5 | `ext_max_dias_extra=0` | Sin días extra |
| Pesos F1–F5 | `w3_posicionamiento=1`, resto=0 | Solo urgencia de stock |
| MontoMaximo | `monto_maximo_override=NULL`, `buffer` alto o `budget_enabled=0` | Sin techo presupuestario |
| Nivel de demanda | `nivel_demanda='sku'` | Gap por SKU en vez de por molécula |

Con este perfil, el resultado del pipeline es exactamente `rotación × días / 30 − stock`, lo que permite **migrar sin cambio funcional** para los usuarios actuales y luego encender factores gradualmente.

> **Requisito técnico habilitante:** el pipeline debe aceptar `nivel_demanda ∈ {sku, molecula, custom}` como criterio de agrupamiento (hoy la capa 1 solo agrupa por molécula). Es la generalización del `nivel_rotacion` del Motor B.

### 3.2 Una sola fuente de demanda: `Procurement.RotacionGrupal`

- El optimizer **deja de ejecutar** `SQL_CATALOG_FOR_GROUPS` y lee R1/R2 de `Procurement.RotacionGrupal`, respetando el mecanismo de freshness existente (`/api/rotacion-grupal/recalcular`).
- Se **estandariza `SUM`** como agregación (eliminando el `AVG` de `pedidos.sql:6`); si el `AVG` respondía a registros duplicados por ítem, se corrige en el SP con dedupe explícito.
- Se eliminan las columnas `Pedido9…Pedido120` de `pedidos.sql` (código muerto).

### 3.3 Esquema de parametrización unificado

Una sola tabla `Procurement.OptimizerConfig` **v2** con perfiles, que pasa a ser la fuente de verdad única:

**Altas (promover a parámetro):**
- `dias_cobertura` (hoy solo request) — default del perfil
- `nivel_demanda` + `atributos_custom` (absorbe `nivel_rotacion` del Motor B)
- `umbral_rotacion` (absorbe el filtro del Motor B)
- `stockout_margen_pct` (hoy hardcode 30% en `optimizer.py:524`)
- `lead_time_default_horas` (hoy hardcode 48/24)
- `min_cantidad_linea` (hoy hardcode 1 en `pedidos.py:258`)
- `ventana_hist_larga_dias` / `ventana_hist_corta_dias` (hoy 90/21)
- `budget_enabled`, `amplifier_enabled` (flags de apagado limpio por capa)

**Bajas (eliminar):**
- `monto_days_reduction_pct` y `sust_kappa` (muertos) — o implementarlos; la propuesta es **eliminar** hasta que exista un caso de uso.
- Funciones huérfanas: `estimate_order_amount`, invocación pendiente de `quadratic_ceiling`.

**Correcciones:**
- Elasticidad/S4: redefinir el gatillo como `elasticidad <= s4_umbral_elasticidad` (nuevo parámetro, default 0) o alinear el seed; documentar la semántica 0–5.
- `SAPROD.Minimo/Maximo`: se dejan de seleccionar; el min/max operativo es el dinámico.

**Perfiles seed propuestos:**
| Perfil | Uso |
|--------|-----|
| `Lineal (compatibilidad)` | Reproduce el Motor B actual — modo Sencillo |
| `Calibrado v3.2` | Perfil actual del optimizer — modo Intermedio/Avanzado |
| `Agresivo oportunidades` | Amplificador y extensión al máximo — preset de negocio |

### 3.4 Una sola fuente de defaults

- La **BD es la fuente de verdad**: los `Field` de Pydantic dejan de duplicar valores; los defaults se cargan del perfil activo y Pydantic solo valida **rangos**.
- El DDL vive **solo en `sql/007` (v2)**; `init_db.py` ejecuta los scripts de `sql/` en vez de duplicar el CREATE.
- Los pesos de PDR (`PDR_Config`) y del scorecard (`supplier_scorer.py`) se administran con el **mismo patrón de perfiles/endpoints** (pueden permanecer en sus tablas, pero con CRUD común).

### 3.5 Modelo matemático resultante

Núcleo activo de **~12 parámetros** organizados en 5 grupos conceptuales (base del diseño de UI):

| Grupo | Parámetros | Pregunta de negocio |
|-------|-----------|---------------------|
| **Horizonte** | `dias_cobertura`, `nivel_demanda`, `umbral_rotacion` | ¿Para cuántos días y a qué nivel compro? |
| **Presupuesto** | `monto_buffer_pct`, `monto_maximo_override`, `budget_enabled` | ¿Cuánto puedo gastar? |
| **Oportunidad** | `amp_a`, `amp_b`, `amp_max_increment_pct`, `ext_max_dias_extra`, `ext_umbral`, `ext_eta`, `opp_lambda` | ¿Cuánto más compro si hay oferta? |
| **Prioridad** | `w1…w5` | ¿Qué pesa más al elegir ofertas? |
| **Riesgo** | `s4_enabled`, `s4_porcentaje_base`, `stockout_margen_pct`, `lead_time_default_horas` | ¿Cómo trato costosos y quiebres? |

---

## 4. Diseño de la UI de Parametrización — `dashboard-react`

Nueva vista **"Parámetros de Pedido"** en el dashboard React (Vite), con selector de nivel persistido por usuario. Los tres niveles operan sobre **el mismo perfil de configuración**; los niveles inferiores son proyecciones simplificadas del superior.

### 4.1 Nivel Sencillo — 100% lenguaje de negocio

4 controles. Cada respuesta mapea a un preset completo:

```
┌─ Parámetros de Pedido · Nivel: [● Sencillo] [○ Intermedio] [○ Avanzado] ─┐
│                                                                          │
│  ¿Para cuántos días quieres comprar?          [ 21 ▾ ] días              │
│                                                                          │
│  ¿Cómo reaccionar ante ofertas del mercado?                              │
│     ( ) Conservador — compro solo lo que necesito                        │
│     (●) Normal — aprovecho descuentos moderadamente                      │
│     ( ) Agresivo — compro más cuando el precio está muy bajo             │
│                                                                          │
│  Presupuesto máximo (opcional)                [ $ ________ ]             │
│                                                                          │
│  ¿Agrupar productos equivalentes?             [Sí, por molécula ▾]       │
│                                                                          │
│                          [ Vista previa del pedido ]  [ Generar pedido ] │
└──────────────────────────────────────────────────────────────────────────┘
```

Mapeo interno de presets:

| Control | Conservador | Normal | Agresivo |
|---------|------------|--------|----------|
| Amplificador | off (amp=1) | calibrado v3.2 | `amp_max_increment_pct` alto |
| Extensión F5 | 0 días | 21 días | 45 días, `ext_umbral=−0.05` |
| `w4_oportunidad` | 0.05 | 0.20 | 0.40 |
| S4 | on (protege caja) | off | off |

### 4.2 Nivel Intermedio — mixto negocio/matemático

Los 5 grupos conceptuales del §3.5 como secciones, con controles amigables y el nombre técnico visible como subtítulo:

- **Horizonte:** días de cobertura (input), nivel de agrupación (select), rotación mínima (slider).
- **Presupuesto:** buffer % (slider 0–100), presupuesto absoluto (input opcional).
- **Oportunidad:** "descuento mínimo que activa compra extra" (`ext_umbral`, slider %), "máximo de días extra" (`ext_max_dias_extra`), "intensidad de reacción a descuentos" (slider 3 posiciones que ajusta `amp_a/amp_b` sobre curvas precalibradas con `calibrate_amplifier_params`).
- **Prioridad:** 5 sliders acoplados (suman 100%) con etiquetas de negocio: Sustituibilidad / Velocidad de venta / Urgencia de stock / Precio de oportunidad / Cobertura extra.
- **Riesgo:** toggle S4 + % de cobertura para costosos; margen de quiebre %.

Cada sección muestra un **indicador de desviación** respecto al perfil guardado y un botón "restaurar".

### 4.3 Nivel Avanzado — control total

- Tabla/formulario con **todos** los parámetros de `OptimizerConfig` v2, con nombre técnico, valor, rango válido (validación en vivo con los rangos de Pydantic) y descripción.
- **Gestión de perfiles:** crear, clonar, activar (`is_active`), historial (`created_at/created_by`).
- **Simulador de curvas:** mini-gráficas del amplificador `e^(a·|d|^b)` y de `coverage_extension` en función del desvío, para entender el efecto de `amp_a/amp_b/eta` antes de guardar.
- Acceso a pesos PDR y scorecard de proveedores (pestañas hermanas).

### 4.4 Contrato API propuesto (especificación)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/optimizer-config/profiles` | Lista de perfiles |
| `GET` | `/api/optimizer-config/profiles/{id}` | Detalle de un perfil |
| `POST` | `/api/optimizer-config/profiles` | Crear perfil (clonar desde otro) |
| `PUT` | `/api/optimizer-config/profiles/{id}` | Actualizar parámetros (validación de rangos) |
| `POST` | `/api/optimizer-config/profiles/{id}/activate` | Activar perfil |
| `GET` | `/api/optimizer-config/schema` | Metadatos: rangos, defaults, descripciones, grupo y nivel de cada parámetro (alimenta la UI dinámicamente) |
| `POST` | `/api/v2/optimize/preview` | Ejecuta el pipeline en modo dry-run con un perfil/overrides → vista previa del pedido |

El endpoint `/schema` es clave: la UI de los 3 niveles se **genera desde metadatos** (cada parámetro declara `nivel_minimo: sencillo|intermedio|avanzado`), evitando duplicar la definición de parámetros una cuarta vez en el front.

### 4.5 Mapeo control-UI → parámetro-BD (resumen)

| Control (Sencillo) | Parámetros afectados |
|--------------------|----------------------|
| "¿Cuántos días?" | `dias_cobertura` |
| "Reacción ante ofertas" | `amp_a`, `amp_b`, `amp_max_increment_pct`, `ext_*`, `w4`, `s4_enabled` (preset) |
| "Presupuesto máximo" | `monto_maximo_override` |
| "Agrupar equivalentes" | `nivel_demanda` |

---

## 5. Hoja de Ruta de Implementación

| Fase | Contenido | Esfuerzo | Riesgo principal |
|------|-----------|----------|------------------|
| **P1 — Saneamiento** | Eliminar parámetros muertos y columnas `PedidoN`; unificar DDL (borrar duplicado de `init_db.py`); estandarizar SUM; optimizer consume `RotacionGrupal`; corregir semántica S4/elasticidad; promover hardcodes a `OptimizerConfig` v2 con perfil `Lineal` | 1–2 semanas | Divergencia numérica vs. pedidos actuales → mitigar con `compare_orders.py` (ya existe) corriendo ambos motores en paralelo |
| **P2 — API de configuración** | Router `optimizer_config.py` con CRUD + `/schema` + `/preview`; Pydantic sin defaults duplicados; deprecación formal de `POST /api/pedidos/generate` (proxy al v3.2 con perfil `Lineal` durante la transición) | 1 semana | Compatibilidad del Excel de salida (BARRA/CANTIDAD) — mantener el formato de export |
| **P3 — UI React 3 niveles** | Vista en `dashboard-react`: Sencillo → Intermedio → Avanzado, generación desde `/schema`, simulador de curvas, gestión de perfiles | 2–3 semanas | Adopción de usuarios del módulo vanilla → mantener `modulo_pedidos.html` hasta validar paridad |
| **P4 — Retiro del legado** | Apagar Motor B y UI vanilla; limpiar `pedidos.sql` | 2–3 días | — |

**Criterio de éxito de P1:** con el perfil `Lineal`, el motor unificado reproduce las cantidades del Motor B actual (tolerancia de redondeo) sobre un corte real de datos.

---

## Anexo: Fuentes citadas

- `analytics_engine/core/optimizer.py`, `analytics_engine/core/nonlinear.py`, `analytics_engine/models/optimization.py`, `analytics_engine/init_db.py`, `analytics_engine/main.py`
- `backend/routers/pedidos.py`, `backend/routers/rotacion_grupal.py`, `backend/queries/pedidos.sql`
- `sql/001` (PDR_Config), `sql/003` (Mercado_Vivo_PDR), `sql/006` (RotacionGrupal + elasticidad), `sql/007` (OptimizerConfig)
- `frontend/modulo_pedidos.html`, `frontend/js/app_pedidos.js`
- `docs/intent/optimizador_compras.md`
