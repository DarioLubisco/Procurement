"""Backorder subtraction from dedicated backend tables (ADR-0009).

## Schema discovery (P1) — 2026-07-12

Searched this monorepo (`sql/`, `backend/`, `analytics_engine/`): **no dedicated
Backorder / en-tránsito / pedidos-pendientes table** is defined yet.

Legacy path today: Excel `subtraction_files` upload in `backend/routers/pedidos.py`
(`BARRA` × `CANTIDAD`). Per ADR-0009 that remains contingency only — not a P1
parity requirement.

### Injectable contract (offline seam)

Until physical tables exist, `generar_pedido(..., backorder=DataFrame)` accepts:

| column    | type | meaning                                      |
|-----------|------|----------------------------------------------|
| `barra`   | str  | product barcode (CodProd / BARRA)            |
| `cantidad`| int  | committed / in-transit / pending qty to subtract |

Same map is subtracted from **PedidoBaseline and PedidoPropuesto** so Comparativa
deltas stay motor-only.

### Candidate sources to wire when discovered

Document here when ops confirms (do not invent):

- ERP open POs / transfers keyed by CodProd
- Any future `Procurement.Backorder` (or equivalent) view

Reader should produce the DataFrame above; do not reintroduce Excel as happy path.
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
