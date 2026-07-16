-- ============================================================
-- 013_proveedor_config_moneda_oferta.sql
-- Moneda en que cotiza el lab en Mercado_Vivo: USD | VES.
-- El motor de pedidos normaliza siempre a USD (÷ dolartoday.dolarbcv si VES)
-- antes de desvío / mínimos / scoring.
-- ============================================================

IF COL_LENGTH('Procurement.ProveedorConfig', 'MonedaOferta') IS NULL
BEGIN
    ALTER TABLE [Procurement].[ProveedorConfig]
    ADD [MonedaOferta] CHAR(3) NOT NULL
        CONSTRAINT [DF_ProveedorConfig_MonedaOferta] DEFAULT ('USD');
END
GO

-- Labs cuya escala en Mercado_Vivo coincide con Bs (÷ BCV ≈ USD de labs USD).
UPDATE [Procurement].[ProveedorConfig]
SET [MonedaOferta] = 'VES'
WHERE [Activo] = 1
  AND UPPER(LTRIM(RTRIM([CodProv]))) IN (
      'NENA', 'ZAKIPHARMA', 'DROCERCA', 'ITS', 'GAMA'
  );
GO
