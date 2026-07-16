-- SQL Server Agent job: refresh mercado histórico cada noche 06:00
-- Idempotente: recrea job si ya existe.
-- Requiere SQL Server Agent en marcha.

USE msdb;
GO

DECLARE @job_name sysname = N'Synapse_Refresh_Mercado_Historico_Noche';
DECLARE @job_id uniqueidentifier;

SELECT @job_id = job_id FROM msdb.dbo.sysjobs WHERE name = @job_name;
IF @job_id IS NOT NULL
BEGIN
    EXEC msdb.dbo.sp_delete_job @job_id = @job_id, @delete_unused_schedule = 1;
END
GO

DECLARE @job_id uniqueidentifier;

EXEC msdb.dbo.sp_add_job
    @job_name = N'Synapse_Refresh_Mercado_Historico_Noche',
    @enabled = 1,
    @description = N'Día (SP_Snapshot_Mercado) luego semana (SP_Refresh_Historico_Semanal). Sustituye flujo N8N.',
    @owner_login_name = N'sa',
    @job_id = @job_id OUTPUT;

EXEC msdb.dbo.sp_add_jobstep
    @job_id = @job_id,
    @step_name = N'Ejecutar SP_Refresh_Mercado_Historico_Noche',
    @subsystem = N'TSQL',
    @database_name = N'EnterpriseAdmin_AMC',
    @command = N'EXEC [Analitica].[SP_Refresh_Mercado_Historico_Noche];',
    @on_success_action = 1,  -- quit success
    @on_fail_action = 2;     -- quit fail

EXEC msdb.dbo.sp_add_schedule
    @schedule_name = N'Diario_0600',
    @freq_type = 4,          -- daily
    @freq_interval = 1,
    @active_start_time = 60000;  -- 06:00:00

EXEC msdb.dbo.sp_attach_schedule
    @job_name = N'Synapse_Refresh_Mercado_Historico_Noche',
    @schedule_name = N'Diario_0600';

EXEC msdb.dbo.sp_add_jobserver
    @job_name = N'Synapse_Refresh_Mercado_Historico_Noche',
    @server_name = N'(local)';
GO
