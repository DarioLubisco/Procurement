-- =============================================
-- Queries para el Motor de Rotación Grupal
-- Usado por: routers/rotacion_grupal.py
-- Autor: Synapse/Antigravity
-- Fecha: 2026-06-17
-- =============================================

-- QUERY: cached_base
-- Lee R1 + R2 materializadas de Procurement.RotacionGrupal
-- Paginado y con búsqueda opcional
SELECT 
    rg.codbarras,
    rg.principio_activo,
    rg.concentracion,
    rg.forma_farmaceutica,
    rg.cantidad_presentacion,
    rg.origen,
    rg.fabricante,
    rg.contenido_neto,
    rg.generico,
    rg.marca,
    rg.blister,
    rg.rot_sku,
    rg.existen_sku,
    rg.rot_base,
    rg.skus_base,
    rg.inv_base,
    rg.ultima_actualizacion,
    -- Descripciones legibles desde la tabla de equivalencias
    eq.principio_activo_Des,
    eq.concentracion_Des,
    eq.forma_farmaceutica_Des,
    eq.descrip1art,
    eq.origen AS origen_code,
    eq.elasticidad_demanda
FROM Procurement.RotacionGrupal rg
LEFT JOIN Procurement.por_aprobacion_equivalencias eq 
    ON rg.codbarras = eq.codbarras
WHERE 1=1
/* SEARCH_FILTER */
/* ATTRIBUTE_FILTERS */
ORDER BY rg.rot_base DESC
OFFSET ? ROWS FETCH NEXT ? ROWS ONLY;

-- QUERY: cached_base_count
-- Cuenta total para paginación
SELECT COUNT(*) AS total
FROM Procurement.RotacionGrupal rg
LEFT JOIN Procurement.por_aprobacion_equivalencias eq 
    ON rg.codbarras = eq.codbarras
WHERE 1=1
/* SEARCH_FILTER */
/* ATTRIBUTE_FILTERS */;

-- QUERY: cached_grupos
-- Agrupación R2 pre-calculada (lectura rápida de la tabla materializada)
SELECT 
    rg.principio_activo,
    rg.concentracion,
    rg.forma_farmaceutica,
    MAX(eq.principio_activo_Des) AS principio_activo_Des,
    MAX(eq.concentracion_Des) AS concentracion_Des,
    MAX(eq.forma_farmaceutica_Des) AS forma_farmaceutica_Des,
    MAX(rg.rot_base) AS rot_grupo,
    MAX(rg.skus_base) AS skus_en_grupo,
    MAX(rg.inv_base) AS inv_grupo
FROM Procurement.RotacionGrupal rg
LEFT JOIN Procurement.por_aprobacion_equivalencias eq 
    ON rg.codbarras = eq.codbarras
WHERE rg.principio_activo IS NOT NULL
/* SEARCH_FILTER */
/* ATTRIBUTE_FILTERS */
GROUP BY rg.principio_activo, rg.concentracion, rg.forma_farmaceutica
HAVING MAX(rg.rot_base) > 0
ORDER BY rot_grupo DESC
OFFSET ? ROWS FETCH NEXT ? ROWS ONLY;

-- QUERY: check_freshness
-- Verifica si la tabla necesita recálculo
SELECT 
    MIN(ultima_actualizacion) AS oldest_update,
    MAX(ultima_actualizacion) AS newest_update,
    COUNT(*) AS total_rows,
    DATEDIFF(MINUTE, MIN(ultima_actualizacion), GETDATE()) AS minutes_since_update
FROM Procurement.RotacionGrupal;

-- QUERY: get_atributos
-- Lista de atributos disponibles para el motor dinámico
SELECT 
    id, nombre_campo, etiqueta, es_base, activo, cardinalidad, descripcion
FROM Procurement.RotacionGrupal_Atributos
WHERE activo = 1
ORDER BY es_base DESC, id;
