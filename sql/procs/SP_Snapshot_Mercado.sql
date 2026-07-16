-- Analitica.SP_Snapshot_Mercado
-- Snapshot diario de Mercado_Vivo → Mercado_Historico en USD (ADR-0023 / 0024 hybrid C).
-- Normaliza a USD:
--   1) MonedaOferta=VES → ÷ BCV
--   2) si precio_raw >= BCV (absurdo como USD unitario) → ÷ BCV
--   3) si hay costo LOTES USD y precio_raw >= 20× ese costo → ÷ BCV (mislabel)
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
    vivo_usd AS (
        SELECT
            CAST(mv.codigo_barras AS NVARCHAR(50)) AS codigo_barras,
            CASE
                WHEN UPPER(LTRIM(RTRIM(ISNULL(pc.MonedaOferta, N'USD')))) = N'VES'
                    THEN CAST(mv.precio_unitario_final AS FLOAT) / @bcv
                WHEN CAST(mv.precio_unitario_final AS FLOAT) >= @bcv
                    THEN CAST(mv.precio_unitario_final AS FLOAT) / @bcv
                WHEN lr.media_costo_usd IS NOT NULL
                     AND CAST(mv.precio_unitario_final AS FLOAT) >= 20.0 * lr.media_costo_usd
                    THEN CAST(mv.precio_unitario_final AS FLOAT) / @bcv
                ELSE CAST(mv.precio_unitario_final AS FLOAT)
            END AS precio_usd,
            CAST(mv.stock_disponible AS FLOAT) AS stock_disponible
        FROM Analitica.Mercado_Vivo mv
        LEFT JOIN Procurement.ProveedorConfig pc
            ON UPPER(LTRIM(RTRIM(pc.CodProv))) = UPPER(LTRIM(RTRIM(mv.proveedor)))
           AND pc.Activo = 1
        LEFT JOIN lotes_ref lr
            ON lr.codigo_barras = CAST(mv.codigo_barras AS NVARCHAR(50))
        WHERE mv.codigo_barras IS NOT NULL
          AND CAST(mv.precio_unitario_final AS FLOAT) > 0
    ),
    agg AS (
        SELECT
            codigo_barras,
            COUNT_BIG(*) AS n_obs,
            MIN(precio_usd) AS precio_min,
            SUM(CASE WHEN stock_disponible IS NULL OR stock_disponible > 0 THEN 1 ELSE 0 END) AS proveedores_stock
        FROM vivo_usd
        GROUP BY codigo_barras
    ),
    med AS (
        SELECT DISTINCT
            codigo_barras,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY precio_usd)
                OVER (PARTITION BY codigo_barras) AS precio_mediana
        FROM vivo_usd
    )
    MERGE Analitica.Mercado_Historico AS t
    USING (
        SELECT
            a.codigo_barras,
            @hoy AS fecha_snapshot,
            m.precio_mediana,
            a.precio_min,
            CAST(a.n_obs AS INT) AS n_obs,
            N'vivo' AS fuente,
            'USD' AS moneda_snapshot
        FROM agg a
        INNER JOIN med m ON m.codigo_barras = a.codigo_barras
        WHERE m.precio_mediana IS NOT NULL AND m.precio_mediana > 0
          -- última red: no persistir "USD" absurdo tras normalización
          AND m.precio_mediana < @bcv
    ) AS s
        ON CAST(t.codigo_barras AS NVARCHAR(50)) = s.codigo_barras
       AND CAST(t.fecha_snapshot AS date) = s.fecha_snapshot
    WHEN MATCHED THEN
        UPDATE SET
            precio_mediana = s.precio_mediana,
            precio_min = s.precio_min,
            n_obs = s.n_obs,
            fuente = s.fuente,
            moneda_snapshot = s.moneda_snapshot
    WHEN NOT MATCHED THEN
        INSERT (codigo_barras, fecha_snapshot, precio_mediana, precio_min, n_obs, fuente, moneda_snapshot)
        VALUES (s.codigo_barras, s.fecha_snapshot, s.precio_mediana, s.precio_min, s.n_obs, s.fuente, s.moneda_snapshot);
END;
GO
