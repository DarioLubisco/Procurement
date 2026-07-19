#!/usr/bin/env python3
"""Rebuild Analitica.Mercado_Historico_Semanal (ADR-0024) — SQL-first, low memory.

1) Agrega Mercado_Historico → semanal
2) Rellena huecos SACOMP/SAITEMCOM (anti-join SQL)

Uso:
  python3 sql/rebuild_historico_semanal.py           # dry-run ROLLBACK
  python3 sql/rebuild_historico_semanal.py --commit
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import pyodbc
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics_engine.historico_stats.constants import RECONVERSION_DATE
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

_SQL_MERGE_FROM_DAILY = """
;WITH base AS (
    SELECT
        CAST(h.codigo_barras AS NVARCHAR(50)) AS codigo_barras,
        CAST(h.fecha_snapshot AS date) AS fecha,
        CAST(h.precio_mediana AS FLOAT) AS precio_mediana,
        CAST(h.precio_min AS FLOAT) AS precio_min,
        DATEPART(ISO_WEEK, h.fecha_snapshot) AS semana_iso,
        YEAR(DATEADD(day, 26 - DATEPART(ISO_WEEK, h.fecha_snapshot), h.fecha_snapshot)) AS anio_iso
    FROM Analitica.Mercado_Historico h
    WHERE h.fecha_snapshot >= ?
      AND h.precio_mediana IS NOT NULL
      AND CAST(h.precio_mediana AS FLOAT) > 0
),
src AS (
    SELECT
        codigo_barras,
        anio_iso,
        semana_iso,
        MIN(precio_mediana) AS precio_p25,
        AVG(precio_mediana) AS precio_mediana,
        MAX(precio_mediana) AS precio_p75,
        MIN(CASE WHEN precio_min IS NOT NULL AND precio_min > 0 THEN precio_min END) AS precio_min,
        AVG(CASE WHEN precio_min IS NOT NULL AND precio_min > 0 THEN precio_min END) AS media_precio_min,
        CAST(COUNT_BIG(*) AS INT) AS n_obs,
        MIN(fecha) AS fecha_semana_ini,
        MAX(fecha) AS fecha_semana_fin
    FROM base
    GROUP BY codigo_barras, anio_iso, semana_iso
    HAVING AVG(precio_mediana) > 0
       AND MIN(CASE WHEN precio_min IS NOT NULL AND precio_min > 0 THEN precio_min END) > 0
)
MERGE Analitica.Mercado_Historico_Semanal AS t
USING src AS s
   ON t.codigo_barras = s.codigo_barras
  AND t.anio_iso = s.anio_iso
  AND t.semana_iso = s.semana_iso
WHEN MATCHED THEN UPDATE SET
    precio_p25 = s.precio_p25,
    precio_mediana = s.precio_mediana,
    precio_p75 = s.precio_p75,
    precio_min = s.precio_min,
    media_precio_min = COALESCE(s.media_precio_min, s.precio_min),
    n_obs = s.n_obs,
    fecha_semana_ini = s.fecha_semana_ini,
    fecha_semana_fin = s.fecha_semana_fin,
    actualizado_en = SYSUTCDATETIME()
WHEN NOT MATCHED THEN INSERT (
    codigo_barras, anio_iso, semana_iso,
    precio_p25, precio_mediana, precio_p75, precio_min, media_precio_min,
    n_obs, fecha_semana_ini, fecha_semana_fin
) VALUES (
    s.codigo_barras, s.anio_iso, s.semana_iso,
    s.precio_p25, s.precio_mediana, s.precio_p75, s.precio_min,
    COALESCE(s.media_precio_min, s.precio_min),
    s.n_obs, s.fecha_semana_ini, s.fecha_semana_fin
);
"""

# Prefer sql/rebuild_historico_from_lotes.py for wipe+backfill.
# Gap-fill here mirrors SP: CUSTOM_LOTES USD via NroUnicoL (never SAITEMCOM.Costo).
_SQL_MERGE_SACOM_GAPS = """
;WITH compras_usd AS (
    SELECT
        CAST(i.CodItem AS NVARCHAR(50)) AS codigo_barras,
        CAST(c.FechaE AS date) AS fecha,
        CAST(cl.[Precio$ (per unit)] AS FLOAT) AS precio_usd,
        DATEPART(ISO_WEEK, c.FechaE) AS semana_iso,
        YEAR(DATEADD(day, 26 - DATEPART(ISO_WEEK, c.FechaE), c.FechaE)) AS anio_iso
    FROM dbo.SAITEMCOM i
    INNER JOIN dbo.SACOMP c ON c.NumeroD = i.NumeroD
    INNER JOIN dbo.CUSTOM_LOTES cl ON cl.NroUnico = i.NroUnicoL
    WHERE c.FechaE >= ?
      AND i.CodItem IS NOT NULL
      AND i.NroUnicoL IS NOT NULL
      AND i.NroUnicoL <> 0
      AND LEN(LTRIM(RTRIM(CAST(i.CodItem AS NVARCHAR(50))))) >= 8
      AND LOWER(LTRIM(RTRIM(CAST(i.CodItem AS NVARCHAR(50))))) NOT IN (N'none', N'nan', N'null')
      AND cl.[Precio$ (per unit)] IS NOT NULL
      AND CAST(cl.[Precio$ (per unit)] AS FLOAT) > 0
),
gaps AS (
    SELECT c.*
    FROM compras_usd c
    WHERE c.precio_usd IS NOT NULL AND c.precio_usd > 0
      AND NOT EXISTS (
        SELECT 1
        FROM Analitica.Mercado_Historico_Semanal s
        WHERE s.codigo_barras = c.codigo_barras
          AND s.anio_iso = c.anio_iso
          AND s.semana_iso = c.semana_iso
      )
),
src AS (
    SELECT
        codigo_barras,
        anio_iso,
        semana_iso,
        MIN(precio_usd) AS precio_p25,
        AVG(precio_usd) AS precio_mediana,
        MAX(precio_usd) AS precio_p75,
        MIN(precio_usd) AS precio_min,
        AVG(precio_usd) AS media_precio_min,
        CAST(COUNT_BIG(*) AS INT) AS n_obs,
        MIN(fecha) AS fecha_semana_ini,
        MAX(fecha) AS fecha_semana_fin
    FROM gaps
    GROUP BY codigo_barras, anio_iso, semana_iso
    HAVING AVG(precio_usd) > 0
)
MERGE Analitica.Mercado_Historico_Semanal AS t
USING src AS s
   ON t.codigo_barras = s.codigo_barras
  AND t.anio_iso = s.anio_iso
  AND t.semana_iso = s.semana_iso
WHEN MATCHED THEN UPDATE SET
    precio_p25 = s.precio_p25,
    precio_mediana = s.precio_mediana,
    precio_p75 = s.precio_p75,
    precio_min = s.precio_min,
    media_precio_min = s.media_precio_min,
    n_obs = s.n_obs,
    fecha_semana_ini = s.fecha_semana_ini,
    fecha_semana_fin = s.fecha_semana_fin,
    actualizado_en = SYSUTCDATETIME()
WHEN NOT MATCHED THEN INSERT (
    codigo_barras, anio_iso, semana_iso,
    precio_p25, precio_mediana, precio_p75, precio_min, media_precio_min,
    n_obs, fecha_semana_ini, fecha_semana_fin
) VALUES (
    s.codigo_barras, s.anio_iso, s.semana_iso,
    s.precio_p25, s.precio_mediana, s.precio_p75, s.precio_min, s.media_precio_min,
    s.n_obs, s.fecha_semana_ini, s.fecha_semana_fin
);
"""

_SQL_COUNT_SEMANAL = "SELECT COUNT_BIG(*) FROM Analitica.Mercado_Historico_Semanal"

_SQL_SAMPLE_SEMANAL = """
SELECT TOP (10)
  codigo_barras, anio_iso, semana_iso, precio_mediana, media_precio_min, n_obs
FROM Analitica.Mercado_Historico_Semanal
ORDER BY anio_iso DESC, semana_iso DESC, codigo_barras
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
        f"Connection Timeout=60;",
    )


def _read(conn, sql: str, params=None) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute(sql, params or [])
    cols = [d[0] for d in cur.description]
    return pd.DataFrame.from_records(cur.fetchall(), columns=cols)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--skip-sacom", action="store_true")
    parser.add_argument("--offline-demo", action="store_true")
    args = parser.parse_args(argv)

    if args.offline_demo:
        demo = pd.DataFrame(
            [
                {"codigo_barras": "DEMO", "fecha": "2024-01-03", "precio_usd": 1.5, "precio_min_diario": 1.2},
                {"codigo_barras": "DEMO", "fecha": "2024-01-04", "precio_usd": 1.7, "precio_min_diario": 1.3},
            ]
        )
        print(aggregate_weekly_box(demo).to_string(index=False))
        return 0

    since = RECONVERSION_DATE.isoformat()
    conn = _connect()
    conn.autocommit = False
    try:
        print(f"MERGE semanal desde diario (>= {since})…")
        cur = conn.cursor()
        cur.execute(_SQL_MERGE_FROM_DAILY, [since])
        if not args.skip_sacom:
            print("MERGE SACom huecos (SQL)…")
            cur.execute(_SQL_MERGE_SACOM_GAPS, [since])

        cur.execute(_SQL_COUNT_SEMANAL)
        total = int(cur.fetchone()[0])
        sample = _read(conn, _SQL_SAMPLE_SEMANAL)
        print(f"Filas en Mercado_Historico_Semanal (en txn): {total}")
        print(sample.to_string(index=False) if not sample.empty else "(vacío)")

        if args.commit:
            conn.commit()
            print("COMMIT OK")
        else:
            conn.rollback()
            print("DRY-RUN ROLLBACK — repetir con --commit para persistir")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
