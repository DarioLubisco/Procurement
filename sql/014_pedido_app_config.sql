-- ============================================================
-- 014_pedido_app_config.sql
-- Key-value config for Pedidos UI (ADR-0023).
-- MonedaTrabajo = display only; motor always USD.
-- ============================================================

IF OBJECT_ID(N'Procurement.PedidoAppConfig', N'U') IS NULL
BEGIN
    CREATE TABLE Procurement.PedidoAppConfig (
        ConfigKey   NVARCHAR(50)  NOT NULL,
        ConfigValue NVARCHAR(100) NOT NULL,
        UpdatedAt   DATETIME2(0)  NOT NULL
            CONSTRAINT DF_PedidoAppConfig_UpdatedAt DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_PedidoAppConfig PRIMARY KEY CLUSTERED (ConfigKey)
    );
END
GO

-- Seed default display currency if missing
IF NOT EXISTS (
    SELECT 1 FROM Procurement.PedidoAppConfig WHERE ConfigKey = N'MonedaTrabajo'
)
BEGIN
    INSERT INTO Procurement.PedidoAppConfig (ConfigKey, ConfigValue)
    VALUES (N'MonedaTrabajo', N'USD');
END
GO
