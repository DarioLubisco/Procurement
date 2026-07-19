-- ============================================================
-- 013_proveedor_config_moneda_oferta.sql
-- MonedaOferta por lab (ADR-0023). Default USD.
-- Idempotent: safe if column already exists.
-- ============================================================

IF COL_LENGTH(N'Procurement.ProveedorConfig', N'MonedaOferta') IS NULL
BEGIN
    ALTER TABLE Procurement.ProveedorConfig
        ADD MonedaOferta CHAR(3) NOT NULL
            CONSTRAINT DF_ProveedorConfig_MonedaOferta DEFAULT ('USD');
END
GO

-- Normalize legacy / unexpected values toward USD|VES
UPDATE Procurement.ProveedorConfig
SET MonedaOferta = 'USD'
WHERE MonedaOferta IS NULL
   OR LTRIM(RTRIM(MonedaOferta)) = ''
   OR UPPER(LTRIM(RTRIM(MonedaOferta))) NOT IN (N'USD', N'VES');
GO
