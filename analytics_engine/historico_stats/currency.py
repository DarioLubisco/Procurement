"""Clasificación USD|VES y conversión candidata (regla D del grill)."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .constants import VES_VS_USD_MEDIAN_FACTOR


def _norm_moneda(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip().upper()
    if s in ("USD", "US$", "$", "DOLAR", "DÓLAR"):
        return "USD"
    if s in ("VES", "BS", "BS.", "BOLIVAR", "BOLÍVAR", "VEF"):
        return "VES"
    return None


def classify_precio_moneda(
    *,
    precio: float,
    moneda_explicita: Any = None,
    moneda_proveedor: Any = None,
    mediana_usd_barra: Optional[float] = None,
    factor: float = VES_VS_USD_MEDIAN_FACTOR,
) -> Tuple[str, str]:
    """Devuelve (moneda, fuente).

    Orden: explícita → ProveedorConfig/lab → heurística vs mediana USD de la barra.
    Default conservador: USD (no dividir por BCV a ciegas).
    """
    try:
        p = float(precio)
    except (TypeError, ValueError):
        return "USD", "invalid_precio"

    mon = _norm_moneda(moneda_explicita)
    if mon:
        return mon, "explicita"

    mon = _norm_moneda(moneda_proveedor)
    if mon:
        return mon, "proveedor_config"

    if (
        mediana_usd_barra is not None
        and mediana_usd_barra > 0
        and p >= float(factor) * float(mediana_usd_barra)
    ):
        return "VES", "heuristica_magnitud"

    return "USD", "default_usd"


def to_usd_candidate(
    precio: float,
    *,
    moneda: str,
    dolarbcv: float,
) -> float:
    """Convierte a USD; VES ÷ BCV. BCV inválido → ValueError."""
    p = float(precio)
    mon = (moneda or "USD").strip().upper()
    if mon == "USD":
        return p
    if mon == "VES":
        bcv = float(dolarbcv)
        if bcv <= 0:
            raise ValueError("dolarbcv inválido")
        return p / bcv
    raise ValueError(f"moneda desconocida: {moneda}")


def classify_row_dict(
    row: Dict[str, Any],
    *,
    mediana_usd_barra: Optional[float] = None,
) -> Dict[str, Any]:
    """Anota moneda_clasificada + fuente_moneda sobre un dict de observación."""
    out = dict(row)
    try:
        precio = float(row.get("precio") or 0.0)
    except (TypeError, ValueError):
        precio = 0.0
    mon, fuente = classify_precio_moneda(
        precio=precio,
        moneda_explicita=row.get("moneda") or row.get("moneda_explicita"),
        moneda_proveedor=row.get("moneda_proveedor") or row.get("moneda_oferta"),
        mediana_usd_barra=mediana_usd_barra,
    )
    out["moneda_clasificada"] = mon
    out["fuente_moneda"] = fuente
    return out
