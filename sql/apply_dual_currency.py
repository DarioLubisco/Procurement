#!/usr/bin/env python3
"""Apply 017 dual-currency DDL + snapshot/refresh SPs (autocommit — not database.py pool).

  python sql/apply_dual_currency.py              # DDL + SPs
  python sql/apply_dual_currency.py --reseed     # also delete today + SP_Snapshot + SP_Refresh
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pyodbc
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
PROCS = ROOT / "sql" / "procs"

for env_path in (
    "/app/.env",
    "/home/synapse/docker/synapse/backend/.env",
    ROOT / "backend" / ".env",
):
    if Path(env_path).is_file():
        load_dotenv(env_path)
        break
else:
    load_dotenv()


def connect():
    user = os.environ.get("DB_USERNAME") or os.environ.get("DB_USER") or "sa"
    password = os.environ.get("DB_PASSWORD") or ""
    server = os.environ["DB_SERVER"]
    database = os.environ["DB_DATABASE"]
    driver = os.getenv("DRIVER", "ODBC Driver 18 for SQL Server").strip("{}")
    return pyodbc.connect(
        f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
        f"UID={user};PWD={password};Encrypt=yes;TrustServerCertificate=yes;"
        f"Connection Timeout=60;",
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


def apply_file(cur, path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    batches = split_go(text)
    print(f"=== {path.name} batches={len(batches)}")
    for i, b in enumerate(batches, 1):
        cur.execute(b)
        print(f"  batch {i} ok ({len(b)} chars)")
    return len(batches)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reseed",
        action="store_true",
        help="DELETE today's daily rows, EXEC SP_Snapshot_Mercado + SP_Refresh_Historico_Semanal",
    )
    args = parser.parse_args(argv)

    conn = connect()
    cur = conn.cursor()
    try:
        apply_file(cur, ROOT / "sql" / "017_mercado_historico_dual_currency.sql")
        # Drop+recreate snapshot so CREATE OR ALTER cannot silently no-op on pool quirks
        cur.execute(
            "IF OBJECT_ID('Analitica.SP_Snapshot_Mercado','P') IS NOT NULL "
            "DROP PROCEDURE Analitica.SP_Snapshot_Mercado"
        )
        apply_file(cur, PROCS / "SP_Snapshot_Mercado.sql")
        apply_file(cur, PROCS / "SP_Refresh_Historico_Semanal.sql")

        cur.execute(
            "SELECT CASE WHEN COL_LENGTH('Analitica.Mercado_Historico','tasa_bcv') IS NULL "
            "THEN 0 ELSE 1 END"
        )
        print("col_tasa_bcv", cur.fetchone()[0])
        cur.execute(
            "SELECT CASE WHEN OBJECT_DEFINITION(OBJECT_ID('Analitica.SP_Snapshot_Mercado')) "
            "LIKE '%precio_mediana_ves%' THEN 1 ELSE 0 END"
        )
        print("sp_has_ves", cur.fetchone()[0])

        if args.reseed:
            print("DELETE today + snapshot + weekly refresh…")
            cur.execute(
                "DELETE FROM Analitica.Mercado_Historico "
                "WHERE fecha_snapshot = CAST(GETDATE() AS date)"
            )
            print("deleted_today", cur.rowcount)
            cur.execute("EXEC [Analitica].[SP_Snapshot_Mercado]")
            cur.execute("EXEC [Analitica].[SP_Refresh_Historico_Semanal]")
            cur.execute(
                """
                SELECT TOP 5
                  codigo_barras, precio_mediana, precio_mediana_usd, precio_mediana_ves,
                  tasa_bcv, moneda_origen, moneda_snapshot
                FROM Analitica.Mercado_Historico
                WHERE fecha_snapshot = CAST(GETDATE() AS date)
                  AND precio_mediana_usd IS NOT NULL
                ORDER BY precio_mediana_usd
                """
            )
            rows = cur.fetchall()
            print("sample_dual", rows)
            cur.execute(
                """
                SELECT COUNT(*),
                       SUM(CASE WHEN tasa_bcv IS NULL THEN 1 ELSE 0 END),
                       SUM(CASE WHEN precio_mediana_ves IS NULL THEN 1 ELSE 0 END),
                       SUM(CASE WHEN ABS(precio_mediana_usd * tasa_bcv - precio_mediana_ves)
                                 / NULLIF(precio_mediana_ves,0) > 0.02 THEN 1 ELSE 0 END)
                FROM Analitica.Mercado_Historico
                WHERE fecha_snapshot = CAST(GETDATE() AS date)
                """
            )
            print("today_counts n/missing_tasa/missing_ves/violations", cur.fetchone())
        print("OK")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
