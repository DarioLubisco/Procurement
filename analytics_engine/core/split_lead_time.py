"""SplitLeadTime quantity allocation — ADR-0014 / ADR-0015."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class OfferCandidate:
    proveedor: str
    barra: str
    descripcion: str
    lead_time_dias: float
    precio: float
    stock_proveedor: Optional[float] = None
    moq: Optional[float] = None  # nullable; never SAPROD.Minimo


@dataclass(frozen=True)
class SplitLeg:
    proveedor: str
    barra: str
    descripcion: str
    cantidad: int
    rol: str  # "rapido" | "barato"


@dataclass(frozen=True)
class SplitLeadTimeResult:
    fired: bool
    legs: tuple[SplitLeg, ...]
    justificacion: str


def compute_split_lead_time(
    *,
    existen: float,
    rotacion_diaria: float,
    demanda: int,
    offers: Sequence[OfferCandidate],
) -> SplitLeadTimeResult:
    """Split demand: min to fastest supplier, remainder to cheapest worse-LT.

    Trigger: Existen < rotacion_diaria × LT_fast.
    Fast qty = max(rot×LT, MOQ?) capped by stock_proveedor; MOQ nullable.
    """
    if demanda <= 0 or len(offers) < 2:
        return SplitLeadTimeResult(fired=False, legs=(), justificacion="")

    ranked = sorted(offers, key=lambda o: (o.lead_time_dias, o.precio))
    fast = ranked[0]
    cover_need = float(rotacion_diaria) * float(fast.lead_time_dias)

    if float(existen) >= cover_need:
        return SplitLeadTimeResult(fired=False, legs=(), justificacion="")

    # Fast minimum: max(rot×LT, MOQ) when MOQ present, else rot×LT
    fast_min = cover_need
    moq_note = "MOQ ausente→rot×LT"
    if fast.moq is not None:
        fast_min = max(cover_need, float(fast.moq))
        moq_note = f"MOQ={fast.moq:g}"

    # Cap by offer stock
    if fast.stock_proveedor is not None:
        capped = min(fast_min, float(fast.stock_proveedor))
        stock_note = f"tope stock_proveedor={fast.stock_proveedor:g}"
    else:
        capped = fast_min
        stock_note = "sin tope stock"

    qty_fast = int(round(capped))
    qty_fast = max(0, min(qty_fast, int(demanda)))

    # Cheapest among worse-LT suppliers
    worse = [o for o in offers if o.proveedor != fast.proveedor and o.lead_time_dias > fast.lead_time_dias]
    if not worse:
        worse = [o for o in offers if o.proveedor != fast.proveedor]
    if not worse:
        return SplitLeadTimeResult(fired=False, legs=(), justificacion="")

    cheap = min(worse, key=lambda o: (o.precio, o.lead_time_dias))
    qty_cheap = int(demanda) - qty_fast
    if qty_cheap < 0:
        qty_cheap = 0

    legs = (
        SplitLeg(
            proveedor=fast.proveedor,
            barra=fast.barra,
            descripcion=fast.descripcion,
            cantidad=qty_fast,
            rol="rapido",
        ),
        SplitLeg(
            proveedor=cheap.proveedor,
            barra=cheap.barra,
            descripcion=cheap.descripcion,
            cantidad=qty_cheap,
            rol="barato",
        ),
    )
    just = (
        f"SplitLeadTime: Existen={existen:g} < rot×LT={cover_need:g} "
        f"(rot={rotacion_diaria:g}, LT_fast={fast.lead_time_dias:g}); "
        f"mínimo rápido={qty_fast} ({moq_note}, {stock_note}); "
        f"resto={qty_cheap}→{cheap.proveedor}"
    )
    return SplitLeadTimeResult(fired=True, legs=legs, justificacion=just)
