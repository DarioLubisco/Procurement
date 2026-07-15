"""Structured justificacion_factores + resumen C."""
from __future__ import annotations

from analytics_engine.core.justificacion_factores import (
    factor,
    finalize,
    resumen_corto,
)


def test_resumen_corto_priority_top2():
    facts = [
        factor("delta_qty", "30→38"),
        factor("amplificador", "30→33"),
        factor("kappa", "techo 40%"),
        factor("sucedaneo", "A→B"),
        factor("f5", "+12"),
    ]
    # priority: sucedaneo > kappa > f5 > amp > delta
    assert resumen_corto(facts, max_n=2) == "Sucedáneo · Techo κ · +3"


def test_finalize_roundtrip_titles():
    resumen, tup = finalize(
        [
            factor("sucedaneo", "A→B"),
            factor("oferta", "P @ $5", datos={"precio": 5.0}),
        ]
    )
    assert resumen.startswith("Sucedáneo")
    assert tup[1].datos["precio"] == 5.0
