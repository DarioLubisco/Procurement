-- Analitica.SP_Snapshot_Mercado
-- Snapshot diario Mercado_Vivo → Mercado_Historico con VES + USD + tasa_bcv (ADR-0024 dual currency).
-- Normaliza origen:
--   1) MonedaOferta=VES → origen VES
--   2) precio_raw >= BCV → origen VES (absurdo como USD unitario)
--   3) precio_raw >= 20× media costo LOTES USD → origen VES (lab mal etiquetado)
--   else origen USD
-- Legacy precio_min / precio_mediana = alias USD. Desvío lee USD.
-- Invocado desde SQL Agent (no N8N).

CREATE OR ALTER PROCEDURE [Analitica].[SP_Snapshot_Mercado]
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @hoy date = CAST(GETDATE() AS date);
    DECLARE @bcv float;

    SELECT TOP (1) @bcv = CAST(dolarbcv AS FLOAT)
    FROM dbo.dolartoday
    WHERE dolarbcv IS NOT NULL AND dolarbcv > 0
    ORDER BY fecha DESC;

    IF @bcv IS NULL OR @bcv <= 0
    BEGIN
        RAISERROR(N'SP_Snapshot_Mercado: dbo.dolartoday.dolarbcv no disponible', 16, 1);
        RETURN;
    END;

    ;WITH lotes_ref AS (
        SELECT
            CAST(cl.CodProd AS NVARCHAR(50)) AS codigo_barras,
            AVG(CAST(cl.[Precio$ (per unit)] AS FLOAT)) AS media_costo_usd
        FROM dbo.CUSTOM_LOTES cl
        WHERE cl.[Precio$ (per unit)] IS NOT NULL
          AND CAST(cl.[Precio$ (per unit)] AS FLOAT) > 0
          AND CAST(cl.[Precio$ (per unit)] AS FLOAT) < 500
        GROUP BY CAST(cl.CodProd AS NVARCHAR(50))
    ),
    vivo_dual AS (
        SELECT
            CAST(mv.codigo_barras AS NVARCHAR(50)) AS codigo_barras,
            CAST(mv.precio_unitario_final AS FLOAT) AS precio_raw,
            CAST(mv.stock_disponible AS FLOAT) AS stock_disponible,
            CASE
                WHEN UPPER(LTRIM(RTRIM(ISNULL(pc.MonedaOferta, N'USD')))) = N'VES'
                    THEN N'VES'
                WHEN CAST(mv.precio_unitario_final AS FLOAT) >= @bcv
                    THEN N'VES'
                WHEN lr.media_costo_usd IS NOT NULL
                     AND CAST(mv.precio_unitario_final AS FLOAT) >= 20.0 * lr.media_costo_usd
                    THEN N'VES'
                ELSE N'USD'
            END AS moneda_origen_linea
        FROM Analitica.Mercado_Vivo mv
        LEFT JOIN Procurement.ProveedorConfig pc
            ON UPPER(LTRIM(RTRIM(pc.CodProv))) = UPPER(LTRIM(RTRIM(mv.proveedor)))
           AND pc.Activo = 1
        LEFT JOIN lotes_ref lr
            ON lr.codigo_barras = CAST(mv.codigo_barras AS NVARCHAR(50))
        WHERE mv.codigo_barras IS NOT NULL
          AND CAST(mv.precio_unitario_final AS FLOAT) > 0
    ),
    vivo_priced AS (
        SELECT
            codigo_barras,
            stock_disponible,
            moneda_origen_linea,
            CASE
                WHEN moneda_origen_linea = N'VES'
                    THEN precio_raw / @bcv
                ELSE precio_raw
            END AS precio_usd,
            CASE
                WHEN moneda_origen_linea = N'VES'
                    THEN precio_raw
                ELSE precio_raw * @bcv
            END AS precio_ves
        FROM vivo_dual
    ),
    agg AS (
        SELECT
            codigo_barras,
            COUNT_BIG(*) AS n_obs,
            MIN(precio_usd) AS precio_min_usd,
            MIN(precio_ves) AS precio_min_ves,
            SUM(CASE WHEN stock_disponible IS NULL OR stock_disponible > 0 THEN 1 ELSE 0 END) AS proveedores_stock,
            SUM(CASE WHEN moneda_origen_linea = N'VES' THEN 1 ELSE 0 END) AS n_ves,
            SUM(CASE WHEN moneda_origen_linea = N'USD' THEN 1 ELSE 0 END) AS n_usd
        FROM vivo_priced
        GROUP BY codigo_barras
    ),
    med_usd AS (
        SELECT DISTINCT
            codigo_barras,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY precio_usd)
                OVER (PARTITION BY codigo_barras) AS precio_mediana_usd
        FROM vivo_priced
    ),
    med_ves AS (
        SELECT DISTINCT
            codigo_barras,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY precio_ves)
                OVER (PARTITION BY codigo_barras) AS precio_mediana_ves
        FROM vivo_priced
    )
    MERGE Analitica.Mercado_Historico AS t
    USING (
        SELECT
            a.codigo_barras,
            @hoy AS fecha_snapshot,
            -- legacy aliases = USD
            a.precio_min_usd AS precio_min,
            m.precio_mediana_usd AS precio_mediana,
            a.precio_min_usd,
            m.precio_mediana_usd,
            a.precio_min_ves,
            v.precio_mediana_ves,
            @bcv AS tasa_bcv,
            CASE
                WHEN a.n_ves > 0 AND a.n_usd > 0 THEN 'MIX'
                WHEN a.n_ves > 0 THEN 'VES'
                ELSE 'USD'
            END AS moneda_origen,
            CAST(a.n_obs AS INT) AS n_obs,
            N'vivo' AS fuente,
            'USD' AS moneda_snapshot
        FROM agg a
        INNER JOIN med_usd m ON m.codigo_barras = a.codigo_barras
        INNER JOIN med_ves v ON v.codigo_barras = a.codigo_barras
        WHERE m.precio_mediana_usd IS NOT NULL
          AND m.precio_mediana_usd > 0
          AND m.precio_mediana_usd < @bcv
    ) AS s
        ON CAST(t.codigo_barras AS NVARCHAR(50)) = s.codigo_barras
       AND CAST(t.fecha_snapshot AS date) = s.fecha_snapshot
    WHEN MATCHED THEN
        UPDATE SET
            precio_mediana = s.precio_mediana,
            precio_min = s.precio_min,
            precio_mediana_usd = s.precio_mediana_usd,
            precio_min_usd = s.precio_min_usd,
            precio_mediana_ves = s.precio_mediana_ves,
            precio_min_ves = s.precio_min_ves,
            tasa_bcv = s.tasa_bcv,
            moneda_origen = s.moneda_origen,
            n_obs = s.n_obs,
            fuente = s.fuente,
            moneda_snapshot = s.moneda_snapshot
    WHEN NOT MATCHED THEN
        INSERT (
            codigo_barras, fecha_snapshot,
            precio_mediana, precio_min,
            precio_mediana_usd, precio_min_usd,
            precio_mediana_ves, precio_min_ves,
            tasa_bcv, moneda_origen,
            n_obs, fuente, moneda_snapshot
        )
        VALUES (
            s.codigo_barras, s.fecha_snapshot,
            s.precio_mediana, s.precio_min,
            s.precio_mediana_usd, s.precio_min_usd,
            s.precio_mediana_ves, s.precio_min_ves,
            s.tasa_bcv, s.moneda_origen,
            s.n_obs, s.fuente, s.moneda_snapshot
        );
END;
GO
