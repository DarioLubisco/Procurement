"""BCV FX via dbo.dolartoday — ecosistema Synapse (CUSTOM_PRECIO_EN_DOLAR, etc.)."""
from __future__ import annotations

from typing import Any, Optional

_SQL_LATEST_BCV = """
SELECT TOP 1 CAST(dolarbcv AS FLOAT)
FROM dbo.dolartoday
WHERE dolarbcv IS NOT NULL AND dolarbcv > 0
ORDER BY fecha DESC
"""


def fetch_dolarbcv(conn: Any) -> float:
    """Latest BCV rate (Bs per 1 USD). Raises if missing."""
    cur = conn.cursor()
    cur.execute(_SQL_LATEST_BCV)
    row = cur.fetchone()
    if not row or row[0] is None or float(row[0]) <= 0:
        raise RuntimeError("dbo.dolartoday.dolarbcv no disponible")
    return float(row[0])


def load_dolarbcv() -> float:
    import database

    conn = database.get_db_connection()
    try:
        return fetch_dolarbcv(conn)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def normalize_moneda(raw: Any, default: str = "USD") -> str:
    m = str(raw or default).strip().upper()
    if m in ("BS", "VES", "BOLIVAR", "BOLIVARES", "Bs", "BS."):
        return "VES"
    if m in ("USD", "$", "DOLAR", "DOLARES", "DOLLAR"):
        return "USD"
    return default if default in ("USD", "VES") else "USD"


def to_usd(precio: float, *, moneda: str, dolarbcv: float) -> float:
    """Offer unit price → USD. VES ÷ BCV; USD unchanged."""
    m = normalize_moneda(moneda)
    p = float(precio)
    if m == "VES":
        if dolarbcv <= 0:
            raise ValueError("dolarbcv inválido")
        return p / float(dolarbcv)
    return p


def usd_to_bs(monto_usd: float, *, dolarbcv: float) -> float:
    """Reconvert Δ / totals to Bs when MonedaTrabajo=VES."""
    return float(monto_usd) * float(dolarbcv)


def maybe_display_amount(
    monto_usd: Optional[float],
    *,
    moneda_trabajo: str,
    dolarbcv: float,
) -> Optional[float]:
    if monto_usd is None:
        return None
    if normalize_moneda(moneda_trabajo) == "VES":
        return round(usd_to_bs(float(monto_usd), dolarbcv=dolarbcv), 2)
    return round(float(monto_usd), 2)
