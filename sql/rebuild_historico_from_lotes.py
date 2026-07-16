#!/usr/bin/env python3
"""Hybrid C: wipe dirty histórico and rebuild weekly from CUSTOM_LOTES USD (ADR-0024).

1) Optional backup tables (*_BKP_YYYYMMDD_HHMM)
2) TRUNCATE Mercado_Historico + Mercado_Historico_Semanal
3) INSERT weekly from SAITEMCOM.NroUnicoL → CUSTOM_LOTES (true percentiles via Python)
4) Optional seed today: EXEC SP_Snapshot_Mercado

Uso (desde contenedor API):
  python sql/rebuild_historico_from_lotes.py              # dry-run ROLLBACK
  python sql/rebuild_historico_from_lotes.py --commit --backup --seed-today
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyodbc
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics_engine.historico_stats.constants import RECONVERSION_DATE
from analytics_engine.historico_stats.lotes_usd import fetch_lotes_usd_observations
from analytics_engine.historico_stats.weekly_aggregate import aggregate_weekly_box

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

_INSERT_WEEKLY = """
INSERT INTO Analitica.Mercado_Historico_Semanal (
    codigo_barras, anio_iso, semana_iso,
    precio_p25, precio_mediana, precio_p75, precio_min, media_precio_min,
    n_obs, fecha_semana_ini, fecha_semana_fin, actualizado_en
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, SYSUTCDATETIME())
"""


def _connect():
    user = os.environ.get("DB_USERNAME") or os.environ.get("DB_USER") or "sa"
    password = os.environ.get("DB_PASSWORD") or ""
    server = os.environ["DB_SERVER"]
    database = os.environ["DB_DATABASE"]
    driver = os.getenv("DRIVER", "ODBC Driver 18 for SQL Server").strip("{}")
    return pyodbc.connect(
        f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
        f"UID={user};PWD={password};Encrypt=yes;TrustServerCertificate=yes;"
        f"Connection Timeout=120;",
    )


def _count(cur, table: str) -> int:
    cur.execute(f"SELECT COUNT_BIG(*) FROM {table}")
    return int(cur.fetchone()[0])


def _backup(cur, table: str, stamp: str) -> str:
    # table like Analitica.Mercado_Historico → Analitica.Mercado_Historico_BKP_...
    schema, name = table.split(".", 1)
    bkp = f"{schema}.{name}_BKP_{stamp}"
    cur.execute(f"SELECT * INTO {bkp} FROM {table}")
    return bkp


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true", help="Persist (default: ROLLBACK)")
    parser.add_argument(
        "--backup",
        action="store_true",
        help="SELECT INTO *_BKP_YYYYMMDD_HHMM before truncate (recommended with --commit)",
    )
    parser.add_argument(
        "--seed-today",
        action="store_true",
        help="After weekly insert, EXEC SP_Snapshot_Mercado for today's daily seed",
    )
    parser.add_argument("--offline-demo", action="store_true")
    args = parser.parse_args(argv)

    if args.offline_demo:
        import pandas as pd

        demo = pd.DataFrame(
            [
                {"codigo_barras": "7591821801929", "fecha": "2024-06-03", "precio_usd": 1.5},
                {"codigo_barras": "7591821801929", "fecha": "2024-06-05", "precio_usd": 1.7},
                {"codigo_barras": "None", "fecha": "2024-06-05", "precio_usd": 99.0},
            ]
        )
        from analytics_engine.historico_stats.lotes_usd import filter_lotes_observations

        clean = filter_lotes_observations(demo)
        print(aggregate_weekly_box(clean).to_string(index=False))
        return 0

    if args.commit and not args.backup:
        print(
            "REFUSE: --commit requires --backup (sql-safety). "
            "Re-run with: --commit --backup [--seed-today]"
        )
        return 2

    since = RECONVERSION_DATE
    conn = _connect()
    conn.autocommit = False
    cur = conn.cursor()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    try:
        n_daily_before = _count(cur, "Analitica.Mercado_Historico")
        n_weekly_before = _count(cur, "Analitica.Mercado_Historico_Semanal")
        print(f"before daily={n_daily_before} weekly={n_weekly_before}")

        print(f"fetch LOTES USD obs since {since.isoformat()}…")
        obs = fetch_lotes_usd_observations(conn, since=since)
        print(f"observations={len(obs)} unique_barras={obs['codigo_barras'].nunique() if len(obs) else 0}")
        if obs.empty:
            print("ABORT: no LOTES observations")
            conn.rollback()
            return 1

        weekly = aggregate_weekly_box(obs)
        print(f"weekly_rows={len(weekly)}")
        print(weekly.head(8).to_string(index=False))
        med = weekly["precio_mediana"]
        print(
            f"mediana_usd p50={med.median():.4f} p95={med.quantile(0.95):.4f} "
            f"max={med.max():.4f} gt100={(med > 100).sum()}"
        )

        if args.backup:
            for t in (
                "Analitica.Mercado_Historico",
                "Analitica.Mercado_Historico_Semanal",
            ):
                bkp = _backup(cur, t, stamp)
                print(f"backup → {bkp} rows={_count(cur, bkp)}")

        print("TRUNCATE daily + weekly…")
        cur.execute("TRUNCATE TABLE Analitica.Mercado_Historico_Semanal")
        cur.execute("TRUNCATE TABLE Analitica.Mercado_Historico")

        print(f"INSERT {len(weekly)} weekly rows…")
        batch = []
        for row in weekly.itertuples(index=False):
            batch.append(
                (
                    str(row.codigo_barras),
                    int(row.anio_iso),
                    int(row.semana_iso),
                    float(row.precio_p25),
                    float(row.precio_mediana),
                    float(row.precio_p75),
                    float(row.precio_min),
                    float(row.media_precio_min),
                    int(row.n_obs),
                    row.fecha_semana_ini,
                    row.fecha_semana_fin,
                )
            )
            if len(batch) >= 500:
                cur.fast_executemany = True
                cur.executemany(_INSERT_WEEKLY, batch)
                batch.clear()
        if batch:
            cur.fast_executemany = True
            cur.executemany(_INSERT_WEEKLY, batch)

        if args.seed_today:
            print("EXEC Analitica.SP_Snapshot_Mercado…")
            cur.execute("EXEC [Analitica].[SP_Snapshot_Mercado]")

        n_daily = _count(cur, "Analitica.Mercado_Historico")
        n_weekly = _count(cur, "Analitica.Mercado_Historico_Semanal")
        print(f"after daily={n_daily} weekly={n_weekly}")

        cur.execute(
            """
            SELECT TOP (10) codigo_barras, anio_iso, semana_iso,
                   precio_mediana, media_precio_min, n_obs
            FROM Analitica.Mercado_Historico_Semanal
            ORDER BY anio_iso DESC, semana_iso DESC, codigo_barras
            """
        )
        print("sample", cur.fetchall())

        if args.commit:
            conn.commit()
            print("COMMIT OK")
        else:
            conn.rollback()
            print("DRY-RUN ROLLBACK — review numbers, then: --commit --backup --seed-today")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
