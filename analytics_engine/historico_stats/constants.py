"""Constantes del pipeline histórico USD / semanal (ADR-0024)."""

from __future__ import annotations

from datetime import date

# Bolívar digital / reconversión — corte de serie larga
RECONVERSION_DATE: date = date(2021, 10, 1)

# Ventana operativa del desvío (motor Generar)
HISTORICO_DESVIO_LOOKBACK_DAYS: int = 120

# Si hay menos días diarios limpios, fallback a mediana semanal
MIN_DIAS_DIARIO_COBERTURA: int = 7

# Heurística última: precio_raw >= factor × mediana_usd_barra → tratar como VES
VES_VS_USD_MEDIAN_FACTOR: float = 20.0

# MAD: |x - mediana| / MAD > threshold → outlier
MAD_Z_THRESHOLD: float = 3.5
