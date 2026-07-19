#!/usr/bin/env python3
"""Apply sql/013 + 014: MonedaOferta + PedidoAppConfig (ADR-0023)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pyodbc
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent

for env_path in (
    "/app/.env",
    "/home/synapse/docker/synapse/backend/.env",
    ROOT.parent / "backend" / ".env",
):
    if Path(env_path).is_file():
        load_dotenv(env_path)
        break
else:
    load_dotenv()


def _split_batches(sql_text: str) -> list[str]:
    batches: list[str] = []
    cur: list[str] = []
    for line in sql_text.splitlines():
        if line.strip().upper() == "GO":
            batch = "\n".join(cur).strip()
            if batch:
                batches.append(batch)
            cur = []
        else:
            cur.append(line)
    tail = "\n".join(cur).strip()
    if tail:
        batches.append(tail)
    return batches


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
    for name in (
        "013_proveedor_config_moneda_oferta.sql",
        "014_pedido_app_config.sql",
    ):
        text = (ROOT / name).read_text(encoding="utf-8")
        for batch in _split_batches(text):
            print(f"EXEC batch from {name} ({len(batch)} chars)…")
            cur.execute(batch)
    conn.close()
    print("OK 013+014 applied")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyError as exc:
        print(f"Missing env: {exc}", file=sys.stderr)
        raise SystemExit(2)
