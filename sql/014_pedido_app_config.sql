-- ============================================================
-- 014_pedido_app_config.sql
-- Config global del módulo Pedidos.
-- MonedaTrabajo: USD | VES
--   - Comparativa vs histórico / desvío / mínimos: siempre en USD.
--   - Si MonedaTrabajo=VES: UI reconvierte Δ a Bs con dolartoday.dolarbcv.
-- ============================================================

IF OBJECT_ID(N'Procurement.PedidoAppConfig', N'U') IS NULL
BEGIN
    CREATE TABLE [Procurement].[PedidoAppConfig] (
        [ConfigKey]   NVARCHAR(50)  NOT NULL,
        [ConfigValue] NVARCHAR(100) NOT NULL,
        [UpdatedAt]   DATETIME2(0)  NOT NULL
            CONSTRAINT [DF_PedidoAppConfig_UpdatedAt] DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT [PK_PedidoAppConfig] PRIMARY KEY CLUSTERED ([ConfigKey])
    );
END
GO

IF NOT EXISTS (
    SELECT 1 FROM [Procurement].[PedidoAppConfig] WHERE [ConfigKey] = N'MonedaTrabajo'
)
BEGIN
    INSERT INTO [Procurement].[PedidoAppConfig] ([ConfigKey], [ConfigValue])
    VALUES (N'MonedaTrabajo', N'USD');
END
GO
