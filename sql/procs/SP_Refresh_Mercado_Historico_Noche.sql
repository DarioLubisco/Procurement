-- Orquestador noche: día → semana (SQL Agent, un solo paso o dos en orden).
-- No depende de N8N.

CREATE OR ALTER PROCEDURE [Analitica].[SP_Refresh_Mercado_Historico_Noche]
AS
BEGIN
    SET NOCOUNT ON;
    EXEC [Analitica].[SP_Snapshot_Mercado];
    EXEC [Analitica].[SP_Refresh_Historico_Semanal];
END;
GO
