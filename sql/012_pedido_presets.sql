-- ============================================================
-- 012_pedido_presets.sql
-- Custom Definitivo presets (global company) — grill 2026-07-15.
-- Snapshot: Nombre + Nivel + BasePreset + OverridesJson.
-- ============================================================

IF OBJECT_ID(N'Procurement.PedidoPresets', N'U') IS NULL
BEGIN
    CREATE TABLE [Procurement].[PedidoPresets] (
        [PresetId]       INT            IDENTITY(1,1) NOT NULL,
        [Nombre]         NVARCHAR(100)  NOT NULL,
        [Nivel]          NVARCHAR(20)   NOT NULL,
        [BasePreset]     NVARCHAR(20)   NOT NULL,
        [OverridesJson]  NVARCHAR(MAX)  NOT NULL,
        [CreatedAt]      DATETIME2(0)   NOT NULL CONSTRAINT [DF_PedidoPresets_CreatedAt] DEFAULT (SYSUTCDATETIME()),
        [UpdatedAt]      DATETIME2(0)   NOT NULL CONSTRAINT [DF_PedidoPresets_UpdatedAt] DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT [PK_PedidoPresets] PRIMARY KEY CLUSTERED ([PresetId]),
        CONSTRAINT [UQ_PedidoPresets_Nombre] UNIQUE ([Nombre])
    );
END
GO
