"""
Módulo de conexión a base de datos para Analytics Engine.
Reutiliza el mismo patrón de connection pool del backend principal.
"""
import os
import pyodbc
import logging
from contextlib import contextmanager

logger = logging.getLogger("AnalyticsEngine.DB")

# Configuración — mismas variables que el backend
DB_SERVER = os.getenv("DB_SERVER", "amc.sql\\efficacis3")
DB_DATABASE = os.getenv("DB_DATABASE", "EnterpriseAdmin_AMC")
DB_USERNAME = os.getenv("DB_USERNAME", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Twinc3pt.")


def _get_driver() -> str:
    """Detecta el driver ODBC disponible en el sistema."""
    available = pyodbc.drivers()
    for candidate in [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "SQL Server",
    ]:
        if candidate in available:
            return candidate
    raise RuntimeError(f"No hay driver ODBC disponible. Encontrados: {available}")


def get_connection() -> pyodbc.Connection:
    """Crea una conexión directa a SQL Server."""
    driver = _get_driver()
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_DATABASE};"
        f"UID={DB_USERNAME};"
        f"PWD={DB_PASSWORD};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=yes;"
    )
    conn = pyodbc.connect(conn_str)
    conn.timeout = 60
    return conn


@contextmanager
def db_cursor():
    """Context manager que entrega un cursor y hace commit/rollback automático."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def query_dataframe(sql: str, params=None):
    """Ejecuta un query y retorna un pandas DataFrame."""
    import pandas as pd
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params=params)
        return df
    finally:
        conn.close()
