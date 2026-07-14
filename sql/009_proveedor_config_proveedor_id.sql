-- ============================================================
-- 009_proveedor_config_proveedor_id.sql
-- Add numeric ProveedorID (UNIQUE IDENTITY) while keeping CodProv
-- as PK for existing FK (e.g. BackorderRecepcionesNoSolicitadas).
-- CodProv remains the Mercado_Vivo.proveedor join key.
-- ============================================================

IF COL_LENGTH('Procurement.ProveedorConfig', 'ProveedorID') IS NULL
BEGIN
    ALTER TABLE [Procurement].[ProveedorConfig]
    ADD [ProveedorID] INT IDENTITY(1,1) NOT NULL;

    ALTER TABLE [Procurement].[ProveedorConfig]
    ADD CONSTRAINT [UQ_ProveedorConfig_ProveedorID] UNIQUE ([ProveedorID]);
END
GO
