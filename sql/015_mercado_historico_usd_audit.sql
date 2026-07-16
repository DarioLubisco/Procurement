-- 015: auditoría Mercado_Historico diario (USD) + índice útil
-- Backup manual recomendado antes de rebuild:
--   SELECT * INTO Analitica.Mercado_Historico_BKP_YYYYMMDD FROM Analitica.Mercado_Historico;

IF COL_LENGTH('Analitica.Mercado_Historico', 'n_obs') IS NULL
BEGIN
    ALTER TABLE Analitica.Mercado_Historico
        ADD n_obs INT NULL;
END
GO

IF COL_LENGTH('Analitica.Mercado_Historico', 'fuente') IS NULL
BEGIN
    ALTER TABLE Analitica.Mercado_Historico
        ADD fuente NVARCHAR(20) NULL;  -- 'vivo' | 'rebuild'
END
GO

IF COL_LENGTH('Analitica.Mercado_Historico', 'moneda_snapshot') IS NULL
BEGIN
    ALTER TABLE Analitica.Mercado_Historico
        ADD moneda_snapshot CHAR(3) NULL;  -- 'USD' tras SP normalizado
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = N'IX_Mercado_Historico_fecha_barra'
      AND object_id = OBJECT_ID(N'Analitica.Mercado_Historico')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_Mercado_Historico_fecha_barra
        ON Analitica.Mercado_Historico (fecha_snapshot, codigo_barras)
        INCLUDE (precio_mediana, precio_min);
END
GO
