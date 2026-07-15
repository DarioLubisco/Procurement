-- ============================================================
-- 010_proveedor_cod_prov_alias.sql
-- Map Mercado_Vivo.proveedor (CodProv) strings → commercial ProveedorID.
-- Canonical ProveedorConfig rows stay Activo=1; alias-only rows Activo=0.
-- ============================================================

IF OBJECT_ID(N'Procurement.ProveedorCodProvAlias', N'U') IS NULL
BEGIN
    CREATE TABLE [Procurement].[ProveedorCodProvAlias] (
        [CodProv]     VARCHAR(50) NOT NULL,
        [ProveedorID] INT         NOT NULL,
        CONSTRAINT [PK_ProveedorCodProvAlias] PRIMARY KEY ([CodProv]),
        CONSTRAINT [FK_ProveedorCodProvAlias_ProveedorID]
            FOREIGN KEY ([ProveedorID])
            REFERENCES [Procurement].[ProveedorConfig] ([ProveedorID])
    );
END
GO
