-- 017: dual currency on Mercado_Historico (VES + USD + FX) — ADR-0024
-- Legacy precio_min / precio_mediana remain USD aliases for loader/desvío.
-- Weekly: optional tasa_bcv_ref only (USD-canonical series).

IF COL_LENGTH('Analitica.Mercado_Historico', 'tasa_bcv') IS NULL
BEGIN
    ALTER TABLE Analitica.Mercado_Historico
        ADD tasa_bcv FLOAT NULL;
END
GO

IF COL_LENGTH('Analitica.Mercado_Historico', 'moneda_origen') IS NULL
BEGIN
    ALTER TABLE Analitica.Mercado_Historico
        ADD moneda_origen CHAR(3) NULL;  -- USD | VES | MIX
END
GO

IF COL_LENGTH('Analitica.Mercado_Historico', 'precio_min_usd') IS NULL
BEGIN
    ALTER TABLE Analitica.Mercado_Historico
        ADD precio_min_usd FLOAT NULL;
END
GO

IF COL_LENGTH('Analitica.Mercado_Historico', 'precio_mediana_usd') IS NULL
BEGIN
    ALTER TABLE Analitica.Mercado_Historico
        ADD precio_mediana_usd FLOAT NULL;
END
GO

IF COL_LENGTH('Analitica.Mercado_Historico', 'precio_min_ves') IS NULL
BEGIN
    ALTER TABLE Analitica.Mercado_Historico
        ADD precio_min_ves FLOAT NULL;
END
GO

IF COL_LENGTH('Analitica.Mercado_Historico', 'precio_mediana_ves') IS NULL
BEGIN
    ALTER TABLE Analitica.Mercado_Historico
        ADD precio_mediana_ves FLOAT NULL;
END
GO

IF COL_LENGTH('Analitica.Mercado_Historico_Semanal', 'tasa_bcv_ref') IS NULL
BEGIN
    ALTER TABLE Analitica.Mercado_Historico_Semanal
        ADD tasa_bcv_ref FLOAT NULL;
END
GO

-- Backfill USD aliases from legacy columns where new cols are null
UPDATE Analitica.Mercado_Historico
SET
    precio_min_usd = COALESCE(precio_min_usd, CAST(precio_min AS FLOAT)),
    precio_mediana_usd = COALESCE(precio_mediana_usd, CAST(precio_mediana AS FLOAT)),
    moneda_snapshot = COALESCE(moneda_snapshot, 'USD')
WHERE precio_mediana IS NOT NULL;
GO
