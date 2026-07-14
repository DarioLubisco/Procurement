-- ============================================================
-- 006_create_rotacion_grupal_system.sql
-- Sistema completo de Rotación Grupal para Procurement
--
-- Objetos creados:
--   [Procurement].[RotacionGrupal_Atributos]   — Catálogo de atributos dinámicos
--   [Procurement].[RotacionGrupal]              — Tabla materializada SKU + R1 + R2
--   [Procurement].[SP_RecalcularRotacionGrupal] — SP de recálculo completo
--   ALTER [Procurement].[por_aprobacion_equivalencias] + elasticidad_demanda
--
-- Autor:  Synapse / Antigravity
-- Fecha:  2026-06-17
-- ============================================================

PRINT '=== Iniciando despliegue del sistema [Procurement].[RotacionGrupal] ===';
PRINT '';
GO

-- ============================================================
-- 1. Tabla de atributos disponibles para agrupación dinámica
-- ============================================================

IF NOT EXISTS (
    SELECT * FROM sys.tables
    WHERE name = 'RotacionGrupal_Atributos'
      AND schema_id = SCHEMA_ID('Procurement')
)
BEGIN
    CREATE TABLE [Procurement].[RotacionGrupal_Atributos] (
        id            INT IDENTITY(1,1) PRIMARY KEY,
        nombre_campo  VARCHAR(50)  NOT NULL,   -- nombre exacto de columna en por_aprobacion_equivalencias
        etiqueta      VARCHAR(100) NOT NULL,   -- etiqueta legible para UI
        es_base       BIT          NOT NULL DEFAULT 0,  -- atributos base (nunca se desactivan)
        activo        BIT          NOT NULL DEFAULT 1,  -- disponible para motor dinámico
        cardinalidad  INT          NULL,                -- cantidad de valores distintos
        descripcion   VARCHAR(255) NULL,
        CONSTRAINT UQ_RotGrupal_nombre_campo UNIQUE (nombre_campo)
    );

    PRINT '✅ Tabla [Procurement].[RotacionGrupal_Atributos] creada.';
END
ELSE
    PRINT 'ℹ️ Tabla [Procurement].[RotacionGrupal_Atributos] ya existe.';
GO

-- -------------------------------------------------------
-- Sembrado de atributos iniciales (10 filas)
-- Solo inserta si la tabla está vacía para evitar duplicados
-- -------------------------------------------------------

IF NOT EXISTS (SELECT 1 FROM [Procurement].[RotacionGrupal_Atributos])
BEGIN
    INSERT INTO [Procurement].[RotacionGrupal_Atributos]
        (nombre_campo, etiqueta, es_base, activo, cardinalidad)
    VALUES
        ('principio_activo',      'Principio Activo',   1, 1, 646),
        ('concentracion',         'Concentración',      1, 1, 422),
        ('forma_farmaceutica',    'Forma Farmacéutica', 1, 1, 151),
        ('cantidad_presentacion', 'Presentación',       0, 1,  66),
        ('origen',                'Origen',             0, 1,  22),
        ('fabricante',            'Fabricante',         0, 1, 318),
        ('contenido_neto',        'Contenido Neto',     0, 1, 163),
        ('generico',              'Genérico',           0, 1,   2),
        ('marca',                 'Marca',              0, 1,  14),
        ('blister',               'Blister',            0, 1,   2);

    PRINT '✅ 10 atributos iniciales insertados en [Procurement].[RotacionGrupal_Atributos].';
END
ELSE
    PRINT 'ℹ️ [Procurement].[RotacionGrupal_Atributos] ya contiene datos, omitiendo sembrado.';
GO

-- ============================================================
-- 2. Tabla materializada: un registro por SKU con R1 y R2
-- ============================================================

IF NOT EXISTS (
    SELECT * FROM sys.tables
    WHERE name = 'RotacionGrupal'
      AND schema_id = SCHEMA_ID('Procurement')
)
BEGIN
    CREATE TABLE [Procurement].[RotacionGrupal] (
        codbarras             VARCHAR(255) NOT NULL PRIMARY KEY,

        -- Claves de grupo (copiadas para JOINs rápidos y GROUP BY dinámico)
        principio_activo      VARCHAR(255) NULL,
        concentracion         VARCHAR(100) NULL,
        forma_farmaceutica    VARCHAR(255) NULL,
        cantidad_presentacion INT          NULL,
        origen                VARCHAR(100) NULL,
        fabricante            VARCHAR(255) NULL,
        contenido_neto        VARCHAR(50)  NULL,
        generico              BIT          NULL,
        marca                 VARCHAR(255) NULL,
        blister               BIT          NULL,

        -- R1: Rotación individual del SKU
        rot_sku               DECIMAL(18,6) NULL DEFAULT 0,
        existen_sku           DECIMAL(18,2) NULL DEFAULT 0,

        -- R2: Rotación base (PA + Concentración + FF)
        rot_base              DECIMAL(18,6) NULL DEFAULT 0,
        skus_base             INT           NULL DEFAULT 1,
        inv_base              DECIMAL(18,2) NULL DEFAULT 0,

        -- Metadatos
        ultima_actualizacion  DATETIME2     NOT NULL DEFAULT GETDATE()
    );

    -- Índices para consultas frecuentes
    CREATE NONCLUSTERED INDEX IX_RotGrupal_PA
        ON [Procurement].[RotacionGrupal] (principio_activo);

    CREATE NONCLUSTERED INDEX IX_RotGrupal_Base
        ON [Procurement].[RotacionGrupal] (principio_activo, concentracion, forma_farmaceutica);

    CREATE NONCLUSTERED INDEX IX_RotGrupal_Origen
        ON [Procurement].[RotacionGrupal] (principio_activo, concentracion, forma_farmaceutica, origen);

    CREATE NONCLUSTERED INDEX IX_RotGrupal_Fabricante
        ON [Procurement].[RotacionGrupal] (principio_activo, concentracion, forma_farmaceutica, fabricante);

    PRINT '✅ Tabla [Procurement].[RotacionGrupal] creada con 4 índices.';
END
ELSE
    PRINT 'ℹ️ Tabla [Procurement].[RotacionGrupal] ya existe.';
GO

-- ============================================================
-- 3. Procedimiento de recálculo completo
--    Paso 1: MERGE SKUs + atributos + rot_sku + existen_sku
--    Paso 2: Cálculo R2 (grupo base PA+Conc+FF)
--    Paso 3: Actualizar timestamp
-- ============================================================

CREATE OR ALTER PROCEDURE [Procurement].[SP_RecalcularRotacionGrupal]
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @filas INT;

    -- =======================================================
    -- Paso 1: MERGE — Upsert de todos los SKUs con atributos,
    --         rotación individual (R1) y existencia
    -- =======================================================
    MERGE [Procurement].[RotacionGrupal] AS T
    USING (
        SELECT
            eq.codbarras,
            eq.principio_activo,
            eq.concentracion,
            eq.forma_farmaceutica,
            eq.cantidad_presentacion,
            eq.origen,
            eq.fabricante,
            eq.contenido_neto,
            eq.generico,
            eq.marca,
            eq.blister,
            ISNULL(r.RotacionMensual, 0)   AS rot_sku,
            ISNULL(s.Existen, 0)    AS existen_sku
        FROM [Procurement].[por_aprobacion_equivalencias] eq
        LEFT JOIN [Procurement].[Rotacion] r
            ON eq.codbarras = r.CodItem
        LEFT JOIN [dbo].[SAPROD] s
            ON eq.codbarras = s.CodProd
            AND s.Activo = 1
    ) AS S
    ON T.codbarras = S.codbarras

    WHEN MATCHED THEN UPDATE SET
        T.principio_activo      = S.principio_activo,
        T.concentracion         = S.concentracion,
        T.forma_farmaceutica    = S.forma_farmaceutica,
        T.cantidad_presentacion = S.cantidad_presentacion,
        T.origen                = S.origen,
        T.fabricante            = S.fabricante,
        T.contenido_neto        = S.contenido_neto,
        T.generico              = S.generico,
        T.marca                 = S.marca,
        T.blister               = S.blister,
        T.rot_sku               = S.rot_sku,
        T.existen_sku           = S.existen_sku

    WHEN NOT MATCHED BY TARGET THEN INSERT (
        codbarras,
        principio_activo, concentracion, forma_farmaceutica,
        cantidad_presentacion, origen, fabricante,
        contenido_neto, generico, marca, blister,
        rot_sku, existen_sku
    ) VALUES (
        S.codbarras,
        S.principio_activo, S.concentracion, S.forma_farmaceutica,
        S.cantidad_presentacion, S.origen, S.fabricante,
        S.contenido_neto, S.generico, S.marca, S.blister,
        S.rot_sku, S.existen_sku
    );

    SET @filas = @@ROWCOUNT;
    PRINT '  → Paso 1 completado: ' + CAST(@filas AS VARCHAR(20)) + ' SKUs procesados (MERGE).';

    -- =======================================================
    -- Paso 2: Cálculo R2 — Rotación del grupo base
    --         Agrupa por (PA + Concentración + Forma Farmacéutica)
    --         Usa ISNULL para agrupación segura con NULLs
    -- =======================================================
    ;WITH CTE_GrupoBase AS (
        SELECT
            ISNULL(principio_activo, '')   AS grp_pa,
            ISNULL(concentracion, '')      AS grp_conc,
            ISNULL(forma_farmaceutica, '') AS grp_ff,
            SUM(rot_sku)                   AS total_rot,
            COUNT(*)                       AS total_skus,
            SUM(existen_sku)               AS total_inv
        FROM [Procurement].[RotacionGrupal]
        GROUP BY
            ISNULL(principio_activo, ''),
            ISNULL(concentracion, ''),
            ISNULL(forma_farmaceutica, '')
    )
    UPDATE rg
    SET
        rg.rot_base   = g.total_rot,
        rg.skus_base  = g.total_skus,
        rg.inv_base   = g.total_inv
    FROM [Procurement].[RotacionGrupal] rg
    INNER JOIN CTE_GrupoBase g
        ON ISNULL(rg.principio_activo, '')   = g.grp_pa
        AND ISNULL(rg.concentracion, '')     = g.grp_conc
        AND ISNULL(rg.forma_farmaceutica, '') = g.grp_ff;

    SET @filas = @@ROWCOUNT;
    PRINT '  → Paso 2 completado: ' + CAST(@filas AS VARCHAR(20)) + ' filas actualizadas con R2 (grupo base).';

    -- =======================================================
    -- Paso 3: Actualizar timestamp de última ejecución
    -- =======================================================
    UPDATE [Procurement].[RotacionGrupal]
    SET ultima_actualizacion = GETDATE();

    SET @filas = @@ROWCOUNT;
    PRINT '  → Paso 3 completado: timestamp actualizado en ' + CAST(@filas AS VARCHAR(20)) + ' filas.';
    PRINT '✅ SP_RecalcularRotacionGrupal finalizado exitosamente.';
END
GO

PRINT '✅ Procedimiento [Procurement].[SP_RecalcularRotacionGrupal] creado.';
GO

-- ============================================================
-- 4. ALTER TABLE: Agregar columnas de elasticidad de demanda
--    a por_aprobacion_equivalencias
-- ============================================================

-- Columna numérica: elasticidad_demanda (0 a 5)
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('Procurement.por_aprobacion_equivalencias')
      AND name = 'elasticidad_demanda'
)
BEGIN
    ALTER TABLE [Procurement].[por_aprobacion_equivalencias]
        ADD elasticidad_demanda INT NULL;

    PRINT '✅ Columna [elasticidad_demanda] agregada a [Procurement].[por_aprobacion_equivalencias].';
END
ELSE
    PRINT 'ℹ️ Columna [elasticidad_demanda] ya existe.';
GO

-- Columna descriptiva: elasticidad_demanda_Des
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('Procurement.por_aprobacion_equivalencias')
      AND name = 'elasticidad_demanda_Des'
)
BEGIN
    ALTER TABLE [Procurement].[por_aprobacion_equivalencias]
        ADD elasticidad_demanda_Des VARCHAR(20) NULL;

    PRINT '✅ Columna [elasticidad_demanda_Des] agregada a [Procurement].[por_aprobacion_equivalencias].';
END
ELSE
    PRINT 'ℹ️ Columna [elasticidad_demanda_Des] ya existe.';
GO

-- -------------------------------------------------------
-- Poblar valores por defecto según tipo genérico/marca
--   generico = 1 → ALTA (4)
--   generico = 0 → MUY BAJA (1)
-- Solo actualiza filas que aún no tengan valor asignado
-- -------------------------------------------------------

UPDATE [Procurement].[por_aprobacion_equivalencias]
SET
    elasticidad_demanda     = 4,
    elasticidad_demanda_Des = 'ALTA'
WHERE generico = 1
  AND elasticidad_demanda IS NULL;

PRINT '  → Elasticidad ALTA asignada a genéricos: ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' filas.';

UPDATE [Procurement].[por_aprobacion_equivalencias]
SET
    elasticidad_demanda     = 1,
    elasticidad_demanda_Des = 'MUY BAJA'
WHERE generico = 0
  AND elasticidad_demanda IS NULL;

PRINT '  → Elasticidad MUY BAJA asignada a marcas: ' + CAST(@@ROWCOUNT AS VARCHAR(20)) + ' filas.';
GO

-- ============================================================
-- 5. Ejecución inicial: poblar RotacionGrupal por primera vez
-- ============================================================

PRINT '';
PRINT '=== Ejecutando población inicial de [Procurement].[RotacionGrupal] ===';

EXEC [Procurement].[SP_RecalcularRotacionGrupal];
GO

PRINT '';
PRINT '=== ✅ Despliegue completo del sistema [Procurement].[RotacionGrupal] ===';
PRINT '';
PRINT 'Objetos creados:';
PRINT '  [Procurement].[RotacionGrupal_Atributos]       — Catálogo de 10 atributos dinámicos';
PRINT '  [Procurement].[RotacionGrupal]                  — Tabla materializada SKU + R1 + R2';
PRINT '  [Procurement].[SP_RecalcularRotacionGrupal]     — SP de recálculo (MERGE + R2 + timestamp)';
PRINT '  [Procurement].[por_aprobacion_equivalencias]    — +elasticidad_demanda, +elasticidad_demanda_Des';
PRINT '';
PRINT 'Consultas útiles:';
PRINT '  SELECT * FROM Procurement.RotacionGrupal ORDER BY rot_base DESC;';
PRINT '  SELECT * FROM Procurement.RotacionGrupal_Atributos WHERE activo = 1;';
PRINT '  EXEC Procurement.SP_RecalcularRotacionGrupal;';
GO
