"""PedidoAppConfig — MonedaTrabajo USD|VES (display); motor always USD."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .fx_bcv import normalize_moneda

_SQL_GET = """
SELECT ConfigValue FROM Procurement.PedidoAppConfig WHERE ConfigKey = ?
"""

_SQL_UPSERT = """
MERGE Procurement.PedidoAppConfig AS t
USING (SELECT ? AS ConfigKey, ? AS ConfigValue) AS s
ON t.ConfigKey = s.ConfigKey
WHEN MATCHED THEN
    UPDATE SET ConfigValue = s.ConfigValue, UpdatedAt = SYSUTCDATETIME()
WHEN NOT MATCHED THEN
    INSERT (ConfigKey, ConfigValue) VALUES (s.ConfigKey, s.ConfigValue);
"""

KEY_MONEDA_TRABAJO = "MonedaTrabajo"


def get_moneda_trabajo(conn: Any) -> str:
    try:
        cur = conn.cursor()
        cur.execute(_SQL_GET, (KEY_MONEDA_TRABAJO,))
        row = cur.fetchone()
        if row and row[0]:
            return normalize_moneda(row[0], default="USD")
    except Exception:
        pass
    return "USD"


def set_moneda_trabajo(conn: Any, moneda: str) -> str:
    m = normalize_moneda(moneda, default="USD")
    if m not in ("USD", "VES"):
        raise ValueError("MonedaTrabajo must be USD|VES")
    cur = conn.cursor()
    cur.execute(_SQL_UPSERT, (KEY_MONEDA_TRABAJO, m))
    try:
        conn.commit()
    except Exception:
        pass
    return m


def load_moneda_trabajo() -> str:
    import database

    conn = database.get_db_connection()
    try:
        return get_moneda_trabajo(conn)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def fx_meta(conn: Any) -> Dict[str, Any]:
    """MonedaTrabajo + BCV for FE reconversión de Δ."""
    from .fx_bcv import fetch_dolarbcv

    moneda = get_moneda_trabajo(conn)
    try:
        bcv = fetch_dolarbcv(conn)
    except Exception:
        bcv = None
    return {
        "moneda_trabajo": moneda,
        "dolarbcv": bcv,
        "desvio_unidad": "USD",
        "nota": (
            "Comparativa vs histórico / desvío / mínimos siempre en USD. "
            "Si moneda_trabajo=VES, la UI reconvierte Δ a Bs con dolarbcv."
        ),
    }
