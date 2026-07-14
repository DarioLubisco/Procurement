-- ============================================================
-- 004_create_view_estadisticas_producto.sql
-- Vista de estadísticas agregadas por producto (codigo_barras)
-- Mediana, desviación estándar, mejor proveedor, profundidad, etc.
-- ============================================================

IF EXISTS (SELECT * FROM sys.views WHERE name = 'Estadisticas_Producto' AND schema_id = SCHEMA_ID('Analitica'))
    DROP VIEW [Analitica].[Estadisticas_Producto];
GO

CREATE VIEW [Analitica].[Estadisticas_Producto]
AS
WITH base AS (
    SELECT * FROM [Analitica].[Mercado_Vivo]
    WHERE codigo_barras IS NOT NULL 
      AND codigo_barras <> ''
      AND precio_unitario_final IS NOT NULL
      AND precio_unitario_final > 0
),

-- Estadísticas base por producto
agg AS (
    SELECT 
        codigo_barras,
        MIN(precio_unitario_final)                          AS precio_min,
        MAX(precio_unitario_final)                          AS precio_max,
        AVG(precio_unitario_final)                          AS precio_promedio,
        STDEV(precio_unitario_final)                        AS precio_desviacion,
        MAX(precio_unitario_final) - MIN(precio_unitario_final) AS rango_precios,
        SUM(ISNULL(stock_disponible, 0))                    AS stock_total_mercado,
        COUNT(DISTINCT proveedor)                           AS num_proveedores_total,
        COUNT(DISTINCT CASE WHEN stock_disponible > 0 THEN proveedor END) AS num_proveedores_disponibles,
        COUNT(*)                                            AS profundidad_mercado,
        MAX(CAST(ISNULL(articulo_indexado, 0) AS INT))      AS es_indexado,
        MAX(fecha_carga)                                    AS ultima_actualizacion,
        MIN(fecha_lote)                                     AS fecha_vencimiento_mas_cercana
    FROM base
    GROUP BY codigo_barras
),

-- Mediana de precio (PERCENTILE_CONT)
mediana AS (
    SELECT DISTINCT
        codigo_barras,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY precio_unitario_final) 
            OVER (PARTITION BY codigo_barras) AS precio_mediana
    FROM base
),

-- Proveedor más barato (el que tiene precio_min)
mejor_precio AS (
    SELECT codigo_barras, proveedor AS proveedor_mas_barato, descripcion_producto,
           ROW_NUMBER() OVER (PARTITION BY codigo_barras ORDER BY precio_unitario_final ASC, stock_disponible DESC) AS rn
    FROM base
),

-- Proveedor con mayor stock
mayor_stock AS (
    SELECT codigo_barras, proveedor AS proveedor_mayor_stock,
           ROW_NUMBER() OVER (PARTITION BY codigo_barras ORDER BY stock_disponible DESC, precio_unitario_final ASC) AS rn
    FROM base
)

SELECT 
    a.codigo_barras,
    mp.descripcion_producto,

    -- Precios
    CAST(a.precio_min AS DECIMAL(18,4))        AS precio_min,
    CAST(a.precio_max AS DECIMAL(18,4))        AS precio_max,
    CAST(a.precio_promedio AS DECIMAL(18,4))    AS precio_promedio,
    CAST(m.precio_mediana AS DECIMAL(18,4))     AS precio_mediana,
    CAST(a.precio_desviacion AS DECIMAL(18,4))  AS precio_desviacion,
    CAST(a.rango_precios AS DECIMAL(18,4))      AS rango_precios,

    -- Disponibilidad
    a.stock_total_mercado,
    a.num_proveedores_disponibles,
    a.num_proveedores_total,
    CAST(
        CASE WHEN a.num_proveedores_total > 0 
             THEN (a.num_proveedores_disponibles * 100.0) / a.num_proveedores_total
             ELSE 0 
        END AS DECIMAL(5,2)
    ) AS pct_disponibilidad,

    -- Competencia
    mp.proveedor_mas_barato,
    ms.proveedor_mayor_stock,
    a.profundidad_mercado,

    -- Indexación
    CAST(a.es_indexado AS BIT) AS es_indexado,

    -- Temporalidad
    a.ultima_actualizacion,
    a.fecha_vencimiento_mas_cercana

FROM agg a
JOIN mediana m         ON a.codigo_barras = m.codigo_barras
LEFT JOIN mejor_precio mp ON a.codigo_barras = mp.codigo_barras AND mp.rn = 1
LEFT JOIN mayor_stock  ms ON a.codigo_barras = ms.codigo_barras AND ms.rn = 1

GO

PRINT '✅ Vista [Analitica].[Estadisticas_Producto] creada con 12 indicadores estadísticos.';
GO
