-- ADR-0030: Bandeja — Comparativa snapshot + Revision/Hash/Motivo on cabecera
-- Idempotent. Apply via sql/migrate_014_borrador_comparativa.py (autocommit).

IF COL_LENGTH(N'Procurement.BorradorPedidosCabecera', N'Revision') IS NULL
BEGIN
    ALTER TABLE [Procurement].[BorradorPedidosCabecera]
        ADD [Revision] INT NOT NULL
            CONSTRAINT [DF_BorradorPedidosCabecera_Revision] DEFAULT (1);
END
GO

IF COL_LENGTH(N'Procurement.BorradorPedidosCabecera', N'SnapshotHash') IS NULL
BEGIN
    ALTER TABLE [Procurement].[BorradorPedidosCabecera]
        ADD [SnapshotHash] VARCHAR(64) NULL;
END
GO

IF COL_LENGTH(N'Procurement.BorradorPedidosCabecera', N'MotivoRechazo') IS NULL
BEGIN
    ALTER TABLE [Procurement].[BorradorPedidosCabecera]
        ADD [MotivoRechazo] NVARCHAR(500) NULL;
END
GO

IF COL_LENGTH(N'Procurement.BorradorPedidosCabecera', N'AvisoTTLEnviado') IS NULL
BEGIN
    ALTER TABLE [Procurement].[BorradorPedidosCabecera]
        ADD [AvisoTTLEnviado] BIT NOT NULL
            CONSTRAINT [DF_BorradorPedidosCabecera_AvisoTTL] DEFAULT (0);
END
GO

IF OBJECT_ID(N'Procurement.BorradorPedidosComparativa', N'U') IS NULL
BEGIN
    CREATE TABLE [Procurement].[BorradorPedidosComparativa] (
        [PropuestaID]           INT NOT NULL,
        [Revision]              INT NOT NULL CONSTRAINT [DF_BorrComp_Revision] DEFAULT (1),
        [SnapshotHash]          VARCHAR(64) NULL,
        [ComparativaJson]       NVARCHAR(MAX) NULL,
        [PedidoPropuestoJson]   NVARCHAR(MAX) NULL,
        [FechaActualizacion]    DATETIME2 NOT NULL CONSTRAINT [DF_BorrComp_Fecha] DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT [PK_BorradorPedidosComparativa] PRIMARY KEY CLUSTERED ([PropuestaID]),
        CONSTRAINT [FK_BorrComp_Cabecera] FOREIGN KEY ([PropuestaID])
            REFERENCES [Procurement].[BorradorPedidosCabecera] ([PropuestaID])
            ON DELETE CASCADE
    );
END
GO
