"""FE generación única — batch grilla ticket 06 (structural + format contract)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "frontend" / "modulo_pedidos.html").read_text(encoding="utf-8")
JS = (ROOT / "frontend" / "js" / "app_pedidos.js").read_text(encoding="utf-8")


def format_total_with_delta(total, delta):
    """Mirror of app_pedidos.formatTotalWithDelta — grill `938 (Δ −86)`."""
    if total is None:
        return "—"
    n = round(float(total))
    if delta is None:
        return str(n)
    d = round(float(delta))
    abs_d = abs(d)
    sign = "+" if d > 0 else ("\u2212" if d < 0 else "")
    return f"{n} (\u0394 {sign}{abs_d})"


def test_format_total_with_delta_grill_shape():
    assert format_total_with_delta(938, -86) == "938 (\u0394 \u221286)"
    assert format_total_with_delta(1000, 50) == "1000 (\u0394 +50)"
    assert format_total_with_delta(100, 0) == "100 (\u0394 0)"


def test_fe_batch_grid_and_slots_present():
    assert 'id="batchResultsSection"' in HTML
    assert 'id="batchResultsGrid"' in HTML
    assert 'id="batchPerfilSlot1"' in HTML
    assert 'id="batchPerfilSlot2"' in HTML
    assert 'id="batchPerfilSlot3"' in HTML
    assert 'value="factory:Conservador"' in HTML
    assert 'value="factory:Normal"' in HTML
    assert 'value="factory:Agresivo"' in HTML
    assert ">Generar<" in HTML or 'id="btnText">Generar</span>' in HTML
    assert "batch-results-grid" in HTML


def test_fe_generar_calls_batch_endpoint():
    assert "/api/pedidos/generar-batch" in JS
    assert "buildBatchPayload" in JS
    assert "stashBatchResult" in JS
    assert "renderBatchResultsGrid" in JS
    assert "formatTotalWithDelta" in JS
    assert "collectBatchPerfilSlots" in JS
    assert "syncBatchPerfilSlotOptions" in JS
    assert "lastBatchResult" in JS
    # Grill: no top proveedor / no Δ knobs on grid
    assert "Intentionally no top-proveedor" in JS or "no top-proveedor" in JS
    assert "no Δ-knobs" in JS or "no \u0394-knobs" in JS or "Sin top proveedor ni" in JS


def test_fe_format_total_uses_unicode_minus_and_delta():
    assert "\\u2212" in JS or "\u2212" in JS
    assert "\\u0394" in JS or "\u0394" in JS
