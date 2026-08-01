"""Docs — ADR-0007 / CONTEXT align with generación única (ticket 14)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADR = (ROOT / "docs" / "adr" / "0007-perfil-sencillo-luego-intermedio.md").read_text(
    encoding="utf-8"
)
CTX = (ROOT / "CONTEXT.md").read_text(encoding="utf-8")


def test_adr_0007_amended_for_generacion_unica():
    assert "generación única" in ADR.lower() or "generacion unica" in ADR.lower()
    assert ".scratch/generacion-unica/PRD.md" in ADR
    assert "PedidoBaseline" in ADR
    assert "sin motor" in ADR.lower()
    assert "accepted" in ADR.lower()
    # Batch first Generar, not single-Sencillo-only as current rule
    assert "three" in ADR.lower() or "tres" in ADR.lower() or "≤3" in ADR or "3" in ADR


def test_context_perfil_allows_batch_first_generar():
    start = CTX.index("**PerfilPedido:**")
    chunk = CTX[start : start + 500]
    assert "tres" in chunk.lower() or "3" in chunk
    assert "activo" in chunk.lower()
    assert "solo **Sencillo**" not in chunk  # old single-first-Generar mandate gone


def test_context_baseline_still_sin_motor_shared():
    start = CTX.index("**PedidoBaseline:**")
    chunk = CTX[start : start + 450]
    assert "sin motor" in chunk.lower()
    assert "una vez" in chunk.lower() or "compart" in chunk.lower()


def test_context_comparativa_grain_intact():
    start = CTX.index("**ComparativaCantidades:**")
    chunk = CTX[start : start + 550]
    assert "BARRA Baseline" in chunk or "fila por BARRA" in chunk
    assert "ADR-0004" in chunk
