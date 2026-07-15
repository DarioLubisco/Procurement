#!/usr/bin/env python3
"""Apply sql/010 + seed Insuaminca/Mastranto aliases (autocommit — never use DB pool)."""
from __future__ import annotations

import os
import sys

import pyodbc
from dotenv import load_dotenv

# Prefer docker API .env, then repo backend .env
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

SQL_CREATE = """
IF OBJECT_ID(N'Procurement.ProveedorCodProvAlias', N'U') IS NULL
BEGIN
    CREATE TABLE [Procurement].[ProveedorCodProvAlias] (
        [CodProv]     VARCHAR(50) NOT NULL,
        [ProveedorID] INT         NOT NULL,
        CONSTRAINT [PK_ProveedorCodProvAlias] PRIMARY KEY ([CodProv])
    );
END
"""

# Canonical CodProv → aliases (identity alias included). ProveedorID resolved at runtime.
SEED_GROUPS = {
    "Insuaminca": ["Insuaminca", "INSUAMINCA_G", "INSUAMINCA_M"],
    "MASTRANTO_B": ["MASTRANTO_B", "MASTRANTO_C"],
}

DEACTIVATE = ["INSUAMINCA_G", "INSUAMINCA_M", "MASTRANTO_C"]


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

    cur.execute(SQL_CREATE)
    print("table ok", flush=True)

    # Ensure FK if ProveedorID UNIQUE exists (may fail if already present)
    try:
        cur.execute(
            """
            IF NOT EXISTS (
                SELECT 1 FROM sys.foreign_keys
                WHERE name = 'FK_ProveedorCodProvAlias_ProveedorID'
            )
            ALTER TABLE [Procurement].[ProveedorCodProvAlias]
            ADD CONSTRAINT [FK_ProveedorCodProvAlias_ProveedorID]
                FOREIGN KEY ([ProveedorID])
                REFERENCES [Procurement].[ProveedorConfig] ([ProveedorID]);
            """
        )
    except Exception as exc:
        print("FK note:", exc, flush=True)

    # Canonical display names
    cur.execute(
        """
        UPDATE Procurement.ProveedorConfig
        SET NombreCorto = 'Mastranto', FechaActualizacion = GETDATE()
        WHERE CodProv = 'MASTRANTO_B'
        """
    )
    cur.execute(
        """
        UPDATE Procurement.ProveedorConfig
        SET NombreCorto = 'Insuaminca', FechaActualizacion = GETDATE()
        WHERE CodProv = 'Insuaminca'
        """
    )

    id_by_cod: dict[str, int] = {}
    cur.execute("SELECT ProveedorID, CodProv FROM Procurement.ProveedorConfig")
    for pid, cod in cur.fetchall():
        id_by_cod[str(cod).strip()] = int(pid)

    for canonical, aliases in SEED_GROUPS.items():
        pid = id_by_cod.get(canonical)
        if pid is None:
            print(f"MISSING canonical {canonical!r}", flush=True)
            conn.close()
            return 1
        for alias in aliases:
            cur.execute(
                """
                MERGE Procurement.ProveedorCodProvAlias AS t
                USING (SELECT ? AS CodProv, CAST(? AS INT) AS ProveedorID) AS s
                ON t.CodProv = s.CodProv
                WHEN MATCHED THEN UPDATE SET ProveedorID = s.ProveedorID
                WHEN NOT MATCHED THEN INSERT (CodProv, ProveedorID)
                    VALUES (s.CodProv, s.ProveedorID);
                """,
                (alias, pid),
            )
            print(f"alias {alias!r} -> ProveedorID={pid}", flush=True)

    for cod in DEACTIVATE:
        cur.execute(
            """
            UPDATE Procurement.ProveedorConfig
            SET Activo = 0, FechaActualizacion = GETDATE()
            WHERE CodProv = ?
            """,
            (cod,),
        )
        print(f"deactivated {cod!r}", flush=True)

    print("=== aliases ===", flush=True)
    cur.execute(
        """
        SELECT a.CodProv, a.ProveedorID, c.NombreCorto, c.Activo, c.MontoMinimoPedidoUSD
        FROM Procurement.ProveedorCodProvAlias a
        LEFT JOIN Procurement.ProveedorConfig c ON c.ProveedorID = a.ProveedorID
        ORDER BY a.ProveedorID, a.CodProv
        """
    )
    for row in cur.fetchall():
        print(row, flush=True)

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
