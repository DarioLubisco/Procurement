"""Backorder subtraction from dedicated backend tables (ADR-0009).

## Schema discovery — updated 2026-07-14

Physical tables (SQL Server `Procurement`):

| Table | Role |
|-------|------|
| `BackorderPedidosCabecera` | Pedido header (`EstadoBackorder`, proveedor, fechas) |
| `BackorderPedidosLineas` | Lines: `CodigoBarras` / `CodigoProducto`, `CantidadPendiente`, `EstadoLinea` |
| `BackorderReceipts` | Receipt events (not required for Generar subtract) |
| `BackorderResolution` | Close-out metrics |

**Open need** = sum(`CantidadPendiente`) by barra for cabeceras whose
`EstadoBackorder` is not `CERRADO`/`CANCELADO`, and líneas not
`COMPLETO`/`REVERTIDO`/`CANCELADO`. Barra = `CodigoBarras` if present, else
`CodigoProducto`.

Loader: `backend/services/backorder_loader.py` → injectable
`generar_pedido(..., backorder=DataFrame)` with columns `barra`, `cantidad`.
Same map subtracted from **PedidoBaseline and PedidoPropuesto**.

Legacy Excel `subtraction_files` remains contingency only (ADR-0009).
"""
from __future__ import annotations

from typing import Dict, Mapping, Optional, Sequence

import pandas as pd

from .pedido_baseline import BaselineLine


def normalize_backorder(backorder: Optional[pd.DataFrame]) -> Dict[str, int]:
    """Aggregate backorder qty by barra. Empty/None → {}."""
    if backorder is None or backorder.empty:
        return {}
    df = backorder.copy()
    if "barra" not in df.columns or "cantidad" not in df.columns:
        raise ValueError("backorder requires columns: barra, cantidad")
    df["barra"] = df["barra"].astype(str)
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0).astype(int)
    agg = df.groupby("barra", as_index=True)["cantidad"].sum()
    return {str(k): int(v) for k, v in agg.items() if int(v) != 0}


def subtract_backorder_from_baseline(
    baseline: Sequence[BaselineLine],
    backorder_by_barra: Mapping[str, int],
) -> list[BaselineLine]:
    """Subtract the same backorder map from each Baseline line (floor at 0)."""
    if not backorder_by_barra:
        return list(baseline)
    out: list[BaselineLine] = []
    for line in baseline:
        bo = int(backorder_by_barra.get(line.barra, 0))
        qty = max(0, int(line.cantidad) - bo)
        if qty <= 0:
            continue
        out.append(
            BaselineLine(
                barra=line.barra,
                descripcion=line.descripcion,
                cantidad=qty,
            )
        )
    return out
