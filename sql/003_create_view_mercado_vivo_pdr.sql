-- ============================================================
-- 003_create_view_mercado_vivo_pdr.sql
-- Vista enriquecida con PDR (Probabilidad de Disponibilidad Real)
-- Lee los pesos dinámicamente de [Analitica].[PDR_Config]
-- ============================================================

IF EXISTS (SELECT * FROM sys.views WHERE name = 'Mercado_Vivo_PDR' AND schema_id = SCHEMA_ID('Analitica'))
    DROP VIEW [Analitica].[Mercado_Vivo_PDR];
GO

CREATE VIEW [Analitica].[Mercado_Vivo_PDR]
AS
WITH 
-- Paso 0: Leer pesos desde la tabla de configuración
cfg AS (
    SELECT 
        MAX(CASE WHEN parametro = 'peso_vc'    THEN valor END) AS w_vc,
        MAX(CASE WHEN parametro = 'peso_cmp'   THEN valor END) AS w_cmp,
        MAX(CASE WHEN parametro = 'peso_ppp'   THEN valor END) AS w_ppp,
        MAX(CASE WHEN parametro = 'umbral_ppp' THEN valor END) AS umbral_ppp
    FROM [Analitica].[PDR_Config]
),

-- Paso 1: Data base consolidada
base AS (
    SELECT * FROM [Analitica].[Mercado_Vivo]
    WHERE codigo_barras IS NOT NULL 
      AND codigo_barras <> ''
      AND codigo_producto IS NOT NULL
),

-- Paso 2: Métricas por proveedor (para VC y PPP)
stats_proveedor AS (
    SELECT 
        proveedor,
        COUNT(*)                                            AS total_productos_proveedor,
        SUM(CASE WHEN stock_disponible > 0 THEN 1 ELSE 0 END) AS productos_con_stock_proveedor,
        NULLIF(SUM(ISNULL(stock_disponible, 0)), 0)        AS stock_total_proveedor
    FROM base
    GROUP BY proveedor
),

-- Paso 3: Métricas por producto (para CMP)
stats_producto AS (
    SELECT 
        codigo_barras,
        COUNT(DISTINCT proveedor)                                            AS total_proveedores_producto,
        COUNT(DISTINCT CASE WHEN stock_disponible > 0 THEN proveedor END)   AS proveedores_con_stock_producto
    FROM base
    GROUP BY codigo_barras
)

-- Paso 4: Ensamblar todo + calcular PDR
SELECT 
    b.proveedor,
    b.sucursal,
    b.codigo_producto,
    b.codigo_barras,
    b.descripcion_producto,
    b.fecha_lote,
    b.precio_unitario,
    b.pct_oferta_vigente,
    b.precio_unitario_final,
    b.stock_disponible,
    b.articulo_indexado,
    b.descuento_adicional,
    b.marca_proveedor,
    b.fecha_carga,

    -- === Señales individuales del PDR ===

    -- Señal 1: Vitalidad del Catálogo (VC)
    CAST(
        CASE WHEN sp.total_productos_proveedor > 0 
             THEN (sp.productos_con_stock_proveedor * 1.0) / sp.total_productos_proveedor
             ELSE 0 
        END AS DECIMAL(5,4)
    ) AS vitalidad_catalogo,

    -- Señal 2: Cobertura de Mercado del Producto (CMP)
    CAST(
        CASE WHEN sprod.total_proveedores_producto > 0 
             THEN (sprod.proveedores_con_stock_producto * 1.0) / sprod.total_proveedores_producto
             ELSE 0 
        END AS DECIMAL(5,4)
    ) AS cobertura_mercado_producto,

    -- Señal 3: Peso del Producto en Proveedor (PPP)
    CAST(
        CASE WHEN sp.stock_total_proveedor > 0 
             THEN (ISNULL(b.stock_disponible, 0) * 1.0) / sp.stock_total_proveedor
             ELSE 0 
        END AS DECIMAL(10,8)
    ) AS peso_producto_en_proveedor,

    -- === PDR Compuesto (0.00 a 1.00) ===
    CAST(
        -- Componente VC
        (CASE WHEN sp.total_productos_proveedor > 0 
              THEN (sp.productos_con_stock_proveedor * 1.0) / sp.total_productos_proveedor
              ELSE 0 END) * c.w_vc
        +
        -- Componente CMP
        (CASE WHEN sprod.total_proveedores_producto > 0 
              THEN (sprod.proveedores_con_stock_producto * 1.0) / sprod.total_proveedores_producto
              ELSE 0 END) * c.w_cmp
        +
        -- Componente PPP (con umbral)
        CASE 
            WHEN sp.stock_total_proveedor IS NULL OR sp.stock_total_proveedor = 0 THEN 0
            WHEN (ISNULL(b.stock_disponible, 0) * 1.0) / sp.stock_total_proveedor >= c.umbral_ppp 
                THEN c.w_ppp
            ELSE ((ISNULL(b.stock_disponible, 0) * 1.0) / sp.stock_total_proveedor) / c.umbral_ppp * c.w_ppp
        END
    AS DECIMAL(5,4)) AS pdr,

    -- === Semáforo legible ===
    CASE 
        WHEN (
            (CASE WHEN sp.total_productos_proveedor > 0 
                  THEN (sp.productos_con_stock_proveedor * 1.0) / sp.total_productos_proveedor
                  ELSE 0 END) * c.w_vc
            + (CASE WHEN sprod.total_proveedores_producto > 0 
                    THEN (sprod.proveedores_con_stock_producto * 1.0) / sprod.total_proveedores_producto
                    ELSE 0 END) * c.w_cmp
            + CASE 
                WHEN sp.stock_total_proveedor IS NULL OR sp.stock_total_proveedor = 0 THEN 0
                WHEN (ISNULL(b.stock_disponible, 0) * 1.0) / sp.stock_total_proveedor >= c.umbral_ppp 
                    THEN c.w_ppp
                ELSE ((ISNULL(b.stock_disponible, 0) * 1.0) / sp.stock_total_proveedor) / c.umbral_ppp * c.w_ppp
              END
        ) >= 0.80 THEN 'ALTA'
        WHEN (
            (CASE WHEN sp.total_productos_proveedor > 0 
                  THEN (sp.productos_con_stock_proveedor * 1.0) / sp.total_productos_proveedor
                  ELSE 0 END) * c.w_vc
            + (CASE WHEN sprod.total_proveedores_producto > 0 
                    THEN (sprod.proveedores_con_stock_producto * 1.0) / sprod.total_proveedores_producto
                    ELSE 0 END) * c.w_cmp
            + CASE 
                WHEN sp.stock_total_proveedor IS NULL OR sp.stock_total_proveedor = 0 THEN 0
                WHEN (ISNULL(b.stock_disponible, 0) * 1.0) / sp.stock_total_proveedor >= c.umbral_ppp 
                    THEN c.w_ppp
                ELSE ((ISNULL(b.stock_disponible, 0) * 1.0) / sp.stock_total_proveedor) / c.umbral_ppp * c.w_ppp
              END
        ) >= 0.50 THEN 'MODERADA'
        WHEN (
            (CASE WHEN sp.total_productos_proveedor > 0 
                  THEN (sp.productos_con_stock_proveedor * 1.0) / sp.total_productos_proveedor
                  ELSE 0 END) * c.w_vc
            + (CASE WHEN sprod.total_proveedores_producto > 0 
                    THEN (sprod.proveedores_con_stock_producto * 1.0) / sprod.total_proveedores_producto
                    ELSE 0 END) * c.w_cmp
            + CASE 
                WHEN sp.stock_total_proveedor IS NULL OR sp.stock_total_proveedor = 0 THEN 0
                WHEN (ISNULL(b.stock_disponible, 0) * 1.0) / sp.stock_total_proveedor >= c.umbral_ppp 
                    THEN c.w_ppp
                ELSE ((ISNULL(b.stock_disponible, 0) * 1.0) / sp.stock_total_proveedor) / c.umbral_ppp * c.w_ppp
              END
        ) >= 0.20 THEN 'BAJA'
        ELSE 'NO_CONFIABLE'
    END AS pdr_semaforo,

    -- === Metadatos auxiliares ===
    sp.total_productos_proveedor,
    sp.productos_con_stock_proveedor,
    sprod.total_proveedores_producto,
    sprod.proveedores_con_stock_producto

FROM base b
CROSS JOIN cfg c
LEFT JOIN stats_proveedor sp   ON b.proveedor = sp.proveedor
LEFT JOIN stats_producto sprod ON b.codigo_barras = sprod.codigo_barras

GO

PRINT '✅ Vista [Analitica].[Mercado_Vivo_PDR] creada con score de confiabilidad calibrable.';
GO
