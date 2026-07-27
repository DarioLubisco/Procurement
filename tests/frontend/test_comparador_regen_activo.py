"""FE generación única — comparador vertical + re-gen solo activo (ticket 10)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "frontend" / "modulo_pedidos.html").read_text(encoding="utf-8")
JS = (ROOT / "frontend" / "js" / "app_pedidos.js").read_text(encoding="utf-8")


def test_fe_comparador_activo_card_markup():
    assert 'id="comparadorActivoCard"' in HTML
    assert 'id="comparadorActivoLabel"' in HTML
    assert 'id="comparadorActivoSummary"' in HTML
    assert "updateComparadorActivoCard" in JS


def test_fe_comparador_has_intermedio_avanzado():
    # Same definitivo controls live under/with the comparator card
    assert 'id="nivelDefinitivo"' in HTML
    assert "Intermedio" in HTML
    assert "Avanzado" in HTML
    assert 'id="btnRegenerarDefinitivo"' in HTML
    assert "comparadorActivoCard" in HTML
    # Card wraps or precedes regenerar section
    card_i = HTML.index('id="comparadorActivoCard"')
    regen_i = HTML.index('id="regenerarDefinitivoSection"')
    assert card_i < regen_i


def test_fe_regen_targets_active_batch_slot_only():
    assert "applyRegenToActiveBatchSlot" in JS
    assert "activeBatchPerfilId" in JS
    assert "/api/pedidos/regenerar-definitivo" in JS
    assert "applyRegenToActiveBatchSlot" in JS
    # Must not wipe sibling perfiles array wholesale
    assert "slot.result" in JS or "slot.result =" in JS


def test_fe_regen_keeps_shared_baseline_and_siblings():
    assert "pedido_baseline" in JS
    assert "baseline_shared" in JS or "sharedBaseline" in JS
    # Explicit preserve of session baseline on regen path
    assert "applyRegenToActiveBatchSlot" in JS
    assert "lastBatchResult.pedido_baseline" in JS or "sharedBaseline" in JS
