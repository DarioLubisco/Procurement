-- ============================================================
-- 008_proveedor_config_monto_minimo_usd.sql
-- Monto mínimo de pedido por proveedor (USD), nullable.
-- Applied 2026-07-14 on EnterpriseAdmin_AMC / Procurement.ProveedorConfig
-- ============================================================

IF COL_LENGTH('Procurement.ProveedorConfig', 'MontoMinimoPedidoUSD') IS NULL
BEGIN
    ALTER TABLE [Procurement].[ProveedorConfig]
    ADD [MontoMinimoPedidoUSD] DECIMAL(18, 2) NULL;
END
GO
