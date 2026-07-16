#!/usr/bin/env python3
"""Apply SP_Snapshot_Mercado + verify 015/016 objects."""
from __future__ import annotations

import os
from pathlib import Path

import pyodbc


def connect():
    return pyodbc.connect(
        f"DRIVER={os.environ['DRIVER']};"
        f"SERVER={os.environ['DB_SERVER']};"
        f"DATABASE={os.environ['DB_DATABASE']};"
        f"UID={os.environ.get('DB_USERNAME') or os.environ.get('DB_USER')};"
        f"PWD={os.environ['DB_PASSWORD']};"
        f"Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=30;",
        autocommit=True,
    )


def split_go(text: str) -> list[str]:
    batches, cur = [], []
    for line in text.splitlines():
        if line.strip().upper() == "GO":
            b = "\n".join(cur).strip()
            if b:
                batches.append(b)
            cur = []
        else:
            cur.append(line)
    tail = "\n".join(cur).strip()
    if tail:
        batches.append(tail)
    return batches


def main() -> int:
    sql_path = Path("/app/sql/procs/SP_Snapshot_Mercado.sql")
    if not sql_path.is_file():
        sql_path = Path(__file__).resolve().parent / "procs" / "SP_Snapshot_Mercado.sql"
    text = sql_path.read_text(encoding="utf-8")
    conn = connect()
    cur = conn.cursor()
    for i, batch in enumerate(split_go(text), 1):
        print(f"SP batch {i} ({len(batch)} chars)")
        cur.execute(batch)

    cur.execute(
        """
        SELECT c.name FROM sys.columns c
        JOIN sys.tables t ON t.object_id=c.object_id
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        WHERE s.name='Analitica' AND t.name='Mercado_Historico'
          AND c.name IN ('n_obs','fuente','moneda_snapshot')
        ORDER BY 1
        """
    )
    print("diario audit cols:", [r[0] for r in cur.fetchall()])
    cur.execute(
        "SELECT CASE WHEN OBJECT_ID('Analitica.Mercado_Historico_Semanal','U') IS NULL THEN 0 ELSE 1 END"
    )
    print("semanal_exists:", cur.fetchone()[0])
    cur.execute(
        "SELECT CASE WHEN OBJECT_ID('Analitica.SP_Snapshot_Mercado','P') IS NULL THEN 0 ELSE 1 END"
    )
    print("sp_exists:", cur.fetchone()[0])
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
