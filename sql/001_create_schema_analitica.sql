-- ============================================================
-- 001_create_schema_analitica.sql
-- Crea el esquema [Analitica] y la tabla de configuración PDR
-- ============================================================

-- 1. Crear esquema
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'Analitica')
BEGIN
    EXEC('CREATE SCHEMA [Analitica]');
END
GO

-- 2. Tabla de pesos del PDR (Probabilidad de Disponibilidad Real)
--    Permite calibrar los pesos desde fuera de SQL (app, n8n, API, etc.)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'PDR_Config' AND schema_id = SCHEMA_ID('Analitica'))
BEGIN
    CREATE TABLE [Analitica].[PDR_Config] (
        parametro   VARCHAR(50)    PRIMARY KEY,
        valor       DECIMAL(5,4)   NOT NULL,
        descripcion VARCHAR(255)   NULL,
        updated_at  DATETIME       DEFAULT GETDATE()
    );

    -- Pesos por defecto (suman 1.00)
    INSERT INTO [Analitica].[PDR_Config] (parametro, valor, descripcion) VALUES
    ('peso_vc',       0.5000, 'Peso de Vitalidad del Catálogo del proveedor (qué tan fresca es su data)'),
    ('peso_cmp',      0.3500, 'Peso de Cobertura de Mercado del Producto (validación cruzada entre proveedores)'),
    ('peso_ppp',      0.1500, 'Peso del Peso del Producto en el Proveedor (significancia del SKU)'),
    ('umbral_ppp',    0.0010, 'Umbral mínimo de PPP para recibir el peso completo');
END
GO

PRINT '✅ Esquema [Analitica] y tabla PDR_Config creados.';
GO
