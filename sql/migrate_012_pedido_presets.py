#!/usr/bin/env python3
"""Apply sql/012_pedido_presets.sql (autocommit — never use DB pool)."""
from __future__ import annotations

import os
import sys

import pyodbc
from dotenv import load_dotenv

for env_path in (
    "/app/.env",
    "/home/synapse/docker/synapse/backend/.env",
    os.path.join(os.path.dirname(__file__), "..", "backend", ".env"),
):
    if os.path.isfile(env_path):
        load_dotenv(env_path)
        break
else:
    load_dotenv()

SQL_CREATE = """
IF OBJECT_ID(N'Procurement.PedidoPresets', N'U') IS NULL
BEGIN
    CREATE TABLE [Procurement].[PedidoPresets] (
        [PresetId]       INT            IDENTITY(1,1) NOT NULL,
        [Nombre]         NVARCHAR(100)  NOT NULL,
        [Nivel]          NVARCHAR(20)   NOT NULL,
        [BasePreset]     NVARCHAR(20)   NOT NULL,
        [OverridesJson]  NVARCHAR(MAX)  NOT NULL,
        [CreatedAt]      DATETIME2(0)   NOT NULL CONSTRAINT [DF_PedidoPresets_CreatedAt] DEFAULT (SYSUTCDATETIME()),
        [UpdatedAt]      DATETIME2(0)   NOT NULL CONSTRAINT [DF_PedidoPresets_UpdatedAt] DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT [PK_PedidoPresets] PRIMARY KEY CLUSTERED ([PresetId]),
        CONSTRAINT [UQ_PedidoPresets_Nombre] UNIQUE ([Nombre])
    );
END
"""


def main() -> int:
    user = os.environ.get("DB_USERNAME") or os.environ.get("DB_USER") or "sa"
    password = os.environ.get("DB_PASSWORD") or ""
    server = os.environ["DB_SERVER"]
    database = os.environ["DB_DATABASE"]
    driver = os.getenv("DRIVER", "ODBC Driver 18 for SQL Server").strip("{}")
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"Encrypt=yes;TrustServerCertificate=yes;"
    )
    conn = pyodbc.connect(conn_str, autocommit=True)
    cur = conn.cursor()
    cur.execute(SQL_CREATE)
    print("Procurement.PedidoPresets ok", flush=True)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
