-- ============================================================
-- 000_deploy_all.sql
-- Script maestro que ejecuta todos los scripts en orden
-- Ejecutar este archivo para desplegar toda la capa Analítica
-- ============================================================

PRINT '=== Iniciando despliegue del esquema [Analitica] ===';
PRINT '';

-- Paso 1: Esquema + Configuración PDR
:r c:\source\Synapse\sql\001_create_schema_analitica.sql

-- Paso 2: Vista consolidada base
:r c:\source\Synapse\sql\002_create_view_mercado_vivo.sql

-- Paso 3: Vista enriquecida con PDR
:r c:\source\Synapse\sql\003_create_view_mercado_vivo_pdr.sql

-- Paso 4: Vista de estadísticas por producto
:r c:\source\Synapse\sql\004_create_view_estadisticas_producto.sql

-- Paso 5: Tabla histórica + SP de snapshot
:r c:\source\Synapse\sql\005_create_table_mercado_historico.sql

PRINT '';
PRINT '=== ✅ Despliegue completo del esquema [Analitica] ===';
PRINT '';
PRINT 'Objetos creados:';
PRINT '  [Analitica].[PDR_Config]            — Tabla de pesos calibrables';
PRINT '  [Analitica].[Mercado_Vivo]          — Vista consolidada (21 tablas)';
PRINT '  [Analitica].[Mercado_Vivo_PDR]      — Vista con score PDR';
PRINT '  [Analitica].[Estadisticas_Producto] — Vista de estadísticas agregadas';
PRINT '  [Analitica].[Mercado_Historico]      — Tabla de snapshots diarios';
PRINT '  [Analitica].[SP_Snapshot_Mercado]   — SP para snapshot diario';
PRINT '';
PRINT 'Consultas útiles:';
PRINT '  SELECT * FROM Analitica.Mercado_Vivo_PDR ORDER BY codigo_barras, precio_unitario_final;';
PRINT '  SELECT * FROM Analitica.Estadisticas_Producto ORDER BY stock_total_mercado DESC;';
PRINT '  EXEC Analitica.SP_Snapshot_Mercado;';
PRINT '';
PRINT 'Para calibrar PDR:';
PRINT '  UPDATE Analitica.PDR_Config SET valor = 0.40 WHERE parametro = ''peso_vc'';';
GO
