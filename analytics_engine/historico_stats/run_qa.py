"""CLI Fase 0: python -m analytics_engine.historico_stats.run_qa"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("historico_qa")


def _connect():
    import pyodbc
    from dotenv import load_dotenv

    for env_path in (
        "/app/.env",
        "/home/synapse/docker/synapse/backend/.env",
        Path(__file__).resolve().parents[2] / "backend" / ".env",
    ):
        if Path(env_path).is_file():
            load_dotenv(env_path)
            break
    else:
        load_dotenv()

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
    return pyodbc.connect(conn_str)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fase 0 QA histórico pre-stats")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Directorio reportes (default reports/historico_qa)",
    )
    parser.add_argument("--sample-n", type=int, default=50000)
    parser.add_argument(
        "--offline-demo",
        action="store_true",
        help="Sin DB: escribe inventory stub + exclusiones vacías (CI/smoke)",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from analytics_engine.historico_stats.qa_inventory import (
        run_qa_pipeline,
        write_qa_artifacts,
    )
    from analytics_engine.historico_stats.constants import (
        HISTORICO_DESVIO_LOOKBACK_DAYS,
        RECONVERSION_DATE,
    )
    import pandas as pd

    if args.offline_demo:
        inv = {
            "since": RECONVERSION_DATE.isoformat(),
            "lookback_days_motor": HISTORICO_DESVIO_LOOKBACK_DAYS,
            "mode": "offline_demo",
            "hist_rows_since_reconversion": 0,
            "note": "Smoke sin DB — correr sin --offline-demo contra SQL Server",
        }
        paths = write_qa_artifacts(inv, pd.DataFrame(), out_dir=args.out_dir)
        logger.info("OK offline demo → %s", paths)
        return 0

    conn = _connect()
    try:
        result = run_qa_pipeline(conn, out_dir=args.out_dir, sample_n=args.sample_n)
        logger.info("QA OK inventory=%s paths=%s", result["inventory"], result["paths"])
        return 0
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
