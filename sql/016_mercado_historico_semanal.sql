-- 016: serie semanal ISO USD (ADR-0024)
-- Caja: p25 / mediana / p75 / min / media_precio_min / n_obs

IF OBJECT_ID(N'Analitica.Mercado_Historico_Semanal', N'U') IS NULL
BEGIN
    CREATE TABLE Analitica.Mercado_Historico_Semanal (
        codigo_barras     NVARCHAR(50)  NOT NULL,
        anio_iso          INT           NOT NULL,
        semana_iso        INT           NOT NULL,
        precio_p25        FLOAT         NOT NULL,
        precio_mediana    FLOAT         NOT NULL,
        precio_p75        FLOAT         NOT NULL,
        precio_min        FLOAT         NOT NULL,
        media_precio_min  FLOAT         NOT NULL,
        n_obs             INT           NOT NULL,
        fecha_semana_ini  DATE          NULL,
        fecha_semana_fin  DATE          NULL,
        actualizado_en    DATETIME2(0)  NOT NULL
            CONSTRAINT DF_Mercado_Historico_Semanal_actualizado
            DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_Mercado_Historico_Semanal
            PRIMARY KEY CLUSTERED (codigo_barras, anio_iso, semana_iso),
        CONSTRAINT CK_Mercado_Historico_Semanal_semana
            CHECK (semana_iso >= 1 AND semana_iso <= 53),
        CONSTRAINT CK_Mercado_Historico_Semanal_n_obs
            CHECK (n_obs >= 1),
        CONSTRAINT CK_Mercado_Historico_Semanal_precios
            CHECK (
                precio_p25 > 0 AND precio_mediana > 0 AND precio_p75 > 0
                AND precio_min > 0 AND media_precio_min > 0
            )
    );
END
GO

IF COL_LENGTH(N'Analitica.Mercado_Historico_Semanal', N'tasa_bcv_ref') IS NULL
BEGIN
    ALTER TABLE Analitica.Mercado_Historico_Semanal
        ADD tasa_bcv_ref FLOAT NULL;
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = N'IX_Mercado_Historico_Semanal_iso'
      AND object_id = OBJECT_ID(N'Analitica.Mercado_Historico_Semanal')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_Mercado_Historico_Semanal_iso
        ON Analitica.Mercado_Historico_Semanal (anio_iso, semana_iso)
        INCLUDE (precio_mediana, media_precio_min, n_obs);
END
GO
