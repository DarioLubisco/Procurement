#!/usr/bin/env python3
"""Apply sql/013 + 014: MonedaOferta + PedidoAppConfig.MonedaTrabajo."""
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

STATEMENTS = [
    """
IF COL_LENGTH('Procurement.ProveedorConfig', 'MonedaOferta') IS NULL
BEGIN
    ALTER TABLE [Procurement].[ProveedorConfig]
    ADD [MonedaOferta] CHAR(3) NOT NULL
        CONSTRAINT [DF_ProveedorConfig_MonedaOferta] DEFAULT ('USD');
END
""",
    """
UPDATE [Procurement].[ProveedorConfig]
SET [MonedaOferta] = 'VES'
WHERE [Activo] = 1
  AND UPPER(LTRIM(RTRIM([CodProv]))) IN (
      'NENA', 'ZAKIPHARMA', 'DROCERCA', 'ITS', 'GAMA'
  )
""",
    """
IF OBJECT_ID(N'Procurement.PedidoAppConfig', N'U') IS NULL
BEGIN
    CREATE TABLE [Procurement].[PedidoAppConfig] (
        [ConfigKey]   NVARCHAR(50)  NOT NULL,
        [ConfigValue] NVARCHAR(100) NOT NULL,
        [UpdatedAt]   DATETIME2(0)  NOT NULL
            CONSTRAINT [DF_PedidoAppConfig_UpdatedAt] DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT [PK_PedidoAppConfig] PRIMARY KEY CLUSTERED ([ConfigKey])
    );
END
""",
    """
IF NOT EXISTS (
    SELECT 1 FROM [Procurement].[PedidoAppConfig] WHERE [ConfigKey] = N'MonedaTrabajo'
)
BEGIN
    INSERT INTO [Procurement].[PedidoAppConfig] ([ConfigKey], [ConfigValue])
    VALUES (N'MonedaTrabajo', N'USD');
END
""",
]


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
    for sql in STATEMENTS:
        cur.execute(sql)
    cur.execute(
        "SELECT CodProv, MonedaOferta FROM Procurement.ProveedorConfig WHERE Activo=1 ORDER BY CodProv"
    )
    print("ProveedorConfig.MonedaOferta:", flush=True)
    for r in cur.fetchall():
        print(f"  {r[0]}={r[1]}", flush=True)
    cur.execute(
        "SELECT ConfigValue FROM Procurement.PedidoAppConfig WHERE ConfigKey=N'MonedaTrabajo'"
    )
    row = cur.fetchone()
    print("MonedaTrabajo=", row[0] if row else None, flush=True)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
