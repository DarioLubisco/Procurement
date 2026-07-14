-- ============================================================
-- 005_create_table_mercado_historico.sql
-- Tabla de snapshots diarios para tendencias históricas
-- Se llena con un INSERT INTO...SELECT desde Estadisticas_Producto
-- ============================================================

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Mercado_Historico' AND schema_id = SCHEMA_ID('Analitica'))
BEGIN
    CREATE TABLE [Analitica].[Mercado_Historico] (
        id                          INT IDENTITY(1,1) PRIMARY KEY,
        fecha_snapshot              DATE NOT NULL,
        codigo_barras               VARCHAR(30) NOT NULL,
        descripcion_producto        VARCHAR(255),
        
        -- Precios
        precio_min                  DECIMAL(18,4),
        precio_promedio             DECIMAL(18,4),
        precio_mediana              DECIMAL(18,4),
        precio_desviacion           DECIMAL(18,4),
        
        -- Disponibilidad
        stock_total_mercado         INT,
        num_proveedores_disponibles INT,
        pct_disponibilidad          DECIMAL(5,2),
        
        -- Competencia
        proveedor_mas_barato        VARCHAR(50),
        profundidad_mercado         INT,
        
        -- Constraint: un snapshot por producto por día
        CONSTRAINT UQ_Historico_Dia_Producto UNIQUE (fecha_snapshot, codigo_barras)
    );

    -- Índice para consultas por rango de fecha
    CREATE NONCLUSTERED INDEX IX_Historico_Fecha 
        ON [Analitica].[Mercado_Historico] (fecha_snapshot, codigo_barras)
        INCLUDE (precio_min, precio_mediana, stock_total_mercado);

    PRINT '✅ Tabla [Analitica].[Mercado_Historico] creada.';
END
ELSE
    PRINT 'ℹ️ Tabla [Analitica].[Mercado_Historico] ya existe.';
GO

-- ============================================================
-- Procedimiento para tomar el snapshot diario
-- Ejecutar una vez al día (ej. desde n8n a las 6:00 AM)
-- ============================================================

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'SP_Snapshot_Mercado' AND schema_id = SCHEMA_ID('Analitica'))
    DROP PROCEDURE [Analitica].[SP_Snapshot_Mercado];
GO

CREATE PROCEDURE [Analitica].[SP_Snapshot_Mercado]
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @hoy DATE = CAST(GETDATE() AS DATE);

    -- Evitar duplicados si se ejecuta más de una vez al día
    IF EXISTS (SELECT 1 FROM [Analitica].[Mercado_Historico] WHERE fecha_snapshot = @hoy)
    BEGIN
        PRINT 'ℹ️ Snapshot de hoy ya existe. Omitiendo.';
        RETURN;
    END

    INSERT INTO [Analitica].[Mercado_Historico] (
        fecha_snapshot, codigo_barras, descripcion_producto,
        precio_min, precio_promedio, precio_mediana, precio_desviacion,
        stock_total_mercado, num_proveedores_disponibles, pct_disponibilidad,
        proveedor_mas_barato, profundidad_mercado
    )
    SELECT 
        @hoy,
        codigo_barras, descripcion_producto,
        precio_min, precio_promedio, precio_mediana, precio_desviacion,
        stock_total_mercado, num_proveedores_disponibles, pct_disponibilidad,
        proveedor_mas_barato, profundidad_mercado
    FROM [Analitica].[Estadisticas_Producto];

    DECLARE @rows INT = @@ROWCOUNT;
    PRINT '✅ Snapshot del ' + CAST(@hoy AS VARCHAR) + ' completado: ' + CAST(@rows AS VARCHAR) + ' productos registrados.';
END
GO

PRINT '✅ Procedimiento [Analitica].[SP_Snapshot_Mercado] creado.';
GO
