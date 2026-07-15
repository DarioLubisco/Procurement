#!/usr/bin/env python3
"""Apply sql/011 ParametrosJson on BorradorPedidosCabecera (autocommit — never use DB pool)."""
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

SQL = """
IF COL_LENGTH(N'Procurement.BorradorPedidosCabecera', N'ParametrosJson') IS NULL
BEGIN
    ALTER TABLE [Procurement].[BorradorPedidosCabecera]
        ADD [ParametrosJson] NVARCHAR(MAX) NULL;
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
    cur.execute(SQL)
    cur.execute(
        """
        SELECT COL_LENGTH(N'Procurement.BorradorPedidosCabecera', N'ParametrosJson')
        """
    )
    print("ParametrosJson col_length=", cur.fetchone()[0], flush=True)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
