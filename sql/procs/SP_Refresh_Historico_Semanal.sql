-- Analitica.SP_Refresh_Historico_Semanal
-- Actualiza Mercado_Historico_Semanal desde diario + huecos LOTES USD (ADR-0024 hybrid C).
-- Huecos: SAITEMCOM.NroUnicoL → CUSTOM_LOTES.[Precio$ (per unit)] (nunca SAITEMCOM.Costo).
-- Pensado para SQL Agent (después de SP_Snapshot_Mercado).

CREATE OR ALTER PROCEDURE [Analitica].[SP_Refresh_Historico_Semanal]
    @Desde date = '2021-10-01'  -- reconversión monetaria
AS
BEGIN
    SET NOCOUNT ON;

    ----------------------------------------------------------------------
    -- 1) Diario → semanal
    ----------------------------------------------------------------------
    ;WITH base AS (
        SELECT
            CAST(h.codigo_barras AS NVARCHAR(50)) AS codigo_barras,
            CAST(h.fecha_snapshot AS date) AS fecha,
            CAST(h.precio_mediana AS FLOAT) AS precio_mediana,
            CAST(h.precio_min AS FLOAT) AS precio_min,
            DATEPART(ISO_WEEK, h.fecha_snapshot) AS semana_iso,
            YEAR(DATEADD(day, 26 - DATEPART(ISO_WEEK, h.fecha_snapshot), h.fecha_snapshot)) AS anio_iso
        FROM Analitica.Mercado_Historico h
        WHERE h.fecha_snapshot >= @Desde
          AND h.precio_mediana IS NOT NULL
          AND CAST(h.precio_mediana AS FLOAT) > 0
    ),
    src AS (
        SELECT
            codigo_barras,
            anio_iso,
            semana_iso,
            MIN(precio_mediana) AS precio_p25,
            AVG(precio_mediana) AS precio_mediana,
            MAX(precio_mediana) AS precio_p75,
            MIN(CASE WHEN precio_min IS NOT NULL AND precio_min > 0 THEN precio_min END) AS precio_min,
            AVG(CASE WHEN precio_min IS NOT NULL AND precio_min > 0 THEN precio_min END) AS media_precio_min,
            CAST(COUNT_BIG(*) AS INT) AS n_obs,
            MIN(fecha) AS fecha_semana_ini,
            MAX(fecha) AS fecha_semana_fin
        FROM base
        GROUP BY codigo_barras, anio_iso, semana_iso
        HAVING AVG(precio_mediana) > 0
           AND MIN(CASE WHEN precio_min IS NOT NULL AND precio_min > 0 THEN precio_min END) > 0
    )
    MERGE Analitica.Mercado_Historico_Semanal AS t
    USING src AS s
       ON t.codigo_barras = s.codigo_barras
      AND t.anio_iso = s.anio_iso
      AND t.semana_iso = s.semana_iso
    WHEN MATCHED THEN UPDATE SET
        precio_p25 = s.precio_p25,
        precio_mediana = s.precio_mediana,
        precio_p75 = s.precio_p75,
        precio_min = s.precio_min,
        media_precio_min = COALESCE(s.media_precio_min, s.precio_min),
        n_obs = s.n_obs,
        fecha_semana_ini = s.fecha_semana_ini,
        fecha_semana_fin = s.fecha_semana_fin,
        actualizado_en = SYSUTCDATETIME()
    WHEN NOT MATCHED THEN INSERT (
        codigo_barras, anio_iso, semana_iso,
        precio_p25, precio_mediana, precio_p75, precio_min, media_precio_min,
        n_obs, fecha_semana_ini, fecha_semana_fin
    ) VALUES (
        s.codigo_barras, s.anio_iso, s.semana_iso,
        s.precio_p25, s.precio_mediana, s.precio_p75, s.precio_min,
        COALESCE(s.media_precio_min, s.precio_min),
        s.n_obs, s.fecha_semana_ini, s.fecha_semana_fin
    );

    ----------------------------------------------------------------------
    -- 2) Huecos compras USD (CUSTOM_LOTES vía NroUnicoL; solo sin fila mercado)
    --    Nunca SAITEMCOM.Costo crudo (suele ser Bs). Mercado gana sobre costo.
    ----------------------------------------------------------------------
    ;WITH compras_usd AS (
        SELECT
            CAST(i.CodItem AS NVARCHAR(50)) AS codigo_barras,
            CAST(c.FechaE AS date) AS fecha,
            CAST(cl.[Precio$ (per unit)] AS FLOAT) AS precio_usd,
            DATEPART(ISO_WEEK, c.FechaE) AS semana_iso,
            YEAR(DATEADD(day, 26 - DATEPART(ISO_WEEK, c.FechaE), c.FechaE)) AS anio_iso
        FROM dbo.SAITEMCOM i
        INNER JOIN dbo.SACOMP c ON c.NumeroD = i.NumeroD
        INNER JOIN dbo.CUSTOM_LOTES cl ON cl.NroUnico = i.NroUnicoL
        WHERE c.FechaE >= @Desde
          AND i.CodItem IS NOT NULL
          AND i.NroUnicoL IS NOT NULL
          AND i.NroUnicoL <> 0
          AND LEN(LTRIM(RTRIM(CAST(i.CodItem AS NVARCHAR(50))))) >= 8
          AND LOWER(LTRIM(RTRIM(CAST(i.CodItem AS NVARCHAR(50))))) NOT IN (N'none', N'nan', N'null')
          AND cl.[Precio$ (per unit)] IS NOT NULL
          AND CAST(cl.[Precio$ (per unit)] AS FLOAT) > 0
    ),
    gaps AS (
        SELECT c.*
        FROM compras_usd c
        WHERE c.precio_usd IS NOT NULL AND c.precio_usd > 0
          AND NOT EXISTS (
            SELECT 1
            FROM Analitica.Mercado_Historico_Semanal s
            WHERE s.codigo_barras = c.codigo_barras
              AND s.anio_iso = c.anio_iso
              AND s.semana_iso = c.semana_iso
          )
    ),
    src2 AS (
        SELECT
            codigo_barras,
            anio_iso,
            semana_iso,
            MIN(precio_usd) AS precio_p25,
            AVG(precio_usd) AS precio_mediana,
            MAX(precio_usd) AS precio_p75,
            MIN(precio_usd) AS precio_min,
            AVG(precio_usd) AS media_precio_min,
            CAST(COUNT_BIG(*) AS INT) AS n_obs,
            MIN(fecha) AS fecha_semana_ini,
            MAX(fecha) AS fecha_semana_fin
        FROM gaps
        GROUP BY codigo_barras, anio_iso, semana_iso
        HAVING AVG(precio_usd) > 0
    )
    MERGE Analitica.Mercado_Historico_Semanal AS t
    USING src2 AS s
       ON t.codigo_barras = s.codigo_barras
      AND t.anio_iso = s.anio_iso
      AND t.semana_iso = s.semana_iso
    WHEN MATCHED THEN UPDATE SET
        precio_p25 = s.precio_p25,
        precio_mediana = s.precio_mediana,
        precio_p75 = s.precio_p75,
        precio_min = s.precio_min,
        media_precio_min = s.media_precio_min,
        n_obs = s.n_obs,
        fecha_semana_ini = s.fecha_semana_ini,
        fecha_semana_fin = s.fecha_semana_fin,
        actualizado_en = SYSUTCDATETIME()
    WHEN NOT MATCHED THEN INSERT (
        codigo_barras, anio_iso, semana_iso,
        precio_p25, precio_mediana, precio_p75, precio_min, media_precio_min,
        n_obs, fecha_semana_ini, fecha_semana_fin
    ) VALUES (
        s.codigo_barras, s.anio_iso, s.semana_iso,
        s.precio_p25, s.precio_mediana, s.precio_p75, s.precio_min, s.media_precio_min,
        s.n_obs, s.fecha_semana_ini, s.fecha_semana_fin
    );
END;
GO
