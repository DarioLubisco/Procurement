#!/usr/bin/env python3
"""Apply sql/014 BorradorPedidosComparativa + cabecera Revision/Hash/Motivo (autocommit)."""
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

SQL_PATH = os.path.join(os.path.dirname(__file__), "014_borrador_comparativa.sql")


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
    with open(SQL_PATH, encoding="utf-8") as f:
        raw = f.read()
    batches = [b.strip() for b in raw.split("\nGO\n") if b.strip()]
    # also split on GO\r\n
    if len(batches) == 1:
        batches = [b.strip() for b in raw.replace("\r\n", "\n").split("\nGO\n") if b.strip()]

    conn = pyodbc.connect(conn_str, autocommit=True)
    cur = conn.cursor()
    for i, batch in enumerate(batches):
        # strip trailing GO
        sql = batch.strip()
        if sql.upper().endswith("GO"):
            sql = sql[:-2].strip()
        if not sql:
            continue
        print(f"exec batch {i+1}/{len(batches)}…", flush=True)
        cur.execute(sql)

    cur.execute(
        """
        SELECT
            COL_LENGTH(N'Procurement.BorradorPedidosCabecera', N'Revision'),
            COL_LENGTH(N'Procurement.BorradorPedidosCabecera', N'SnapshotHash'),
            COL_LENGTH(N'Procurement.BorradorPedidosCabecera', N'MotivoRechazo'),
            OBJECT_ID(N'Procurement.BorradorPedidosComparativa', N'U')
        """
    )
    row = cur.fetchone()
    print(
        "Revision=", row[0],
        "SnapshotHash=", row[1],
        "MotivoRechazo=", row[2],
        "Comparativa_OID=", row[3],
        flush=True,
    )
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
