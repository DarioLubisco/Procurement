-- ============================================================
-- 011_borrador_parametros_json.sql
-- Snapshot of Definitivo knobs/params on each Borrador cabecera (ADR-0018).
-- ============================================================

IF COL_LENGTH(N'Procurement.BorradorPedidosCabecera', N'ParametrosJson') IS NULL
BEGIN
    ALTER TABLE [Procurement].[BorradorPedidosCabecera]
        ADD [ParametrosJson] NVARCHAR(MAX) NULL;
END
GO
