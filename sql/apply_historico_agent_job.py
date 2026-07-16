#!/usr/bin/env python3
"""Apply historico night SPs + SQL Agent job via working DB connection."""
from __future__ import annotations

import os
from pathlib import Path

import pyodbc

PROCS = [
    "SP_Refresh_Historico_Semanal.sql",
    "SP_Refresh_Mercado_Historico_Noche.sql",
    "job_Refresh_Mercado_Historico_Noche.sql",
]


def connect():
    return pyodbc.connect(
        f"DRIVER={os.environ['DRIVER']};"
        f"SERVER={os.environ['DB_SERVER']};"
        f"DATABASE={os.environ['DB_DATABASE']};"
        f"UID={os.environ.get('DB_USERNAME') or os.environ.get('DB_USER')};"
        f"PWD={os.environ['DB_PASSWORD']};"
        f"Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=60;",
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
    root = Path("/app/sql/procs")
    if not root.is_dir():
        root = Path(__file__).resolve().parent / "procs"
    conn = connect()
    cur = conn.cursor()
    for name in PROCS:
        path = root / name
        print(f"=== {name} ===")
        for i, batch in enumerate(split_go(path.read_text(encoding="utf-8")), 1):
            print(f"  batch {i} ({len(batch)} chars)")
            cur.execute(batch)

    cur.execute(
        """
        SELECT name FROM sys.procedures
        WHERE schema_id = SCHEMA_ID('Analitica')
          AND name IN (
            'SP_Snapshot_Mercado',
            'SP_Refresh_Historico_Semanal',
            'SP_Refresh_Mercado_Historico_Noche'
          )
        ORDER BY name
        """
    )
    print("procs:", [r[0] for r in cur.fetchall()])

    cur.execute(
        "SELECT name, enabled FROM msdb.dbo.sysjobs WHERE name = N'Synapse_Refresh_Mercado_Historico_Noche'"
    )
    row = cur.fetchone()
    print("job:", row)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
