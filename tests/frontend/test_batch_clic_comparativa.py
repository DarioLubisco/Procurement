"""FE generación única — clic columna → Comparativa (ticket 07)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "frontend" / "modulo_pedidos.html").read_text(encoding="utf-8")
JS = (ROOT / "frontend" / "js" / "app_pedidos.js").read_text(encoding="utf-8")


def test_fe_hydrate_comparativa_from_batch_slot():
    assert "hydrateComparativaFromBatchSlot" in JS
    assert "activeBatchPerfilId" in JS
    assert "markActiveBatchColumn" in JS
    assert "is-active" in JS or "is-active" in HTML
    assert "pedido_baseline: sharedBaseline" in JS or "sharedBaseline" in JS
    assert "baseline_shared" in JS
    # Click + keyboard on columns
    assert "addEventListener('click'" in JS
    assert "hydrateComparativaFromBatchSlot(slot.id" in JS
    # Must not re-call generar-batch on column switch
    assert JS.count("/api/pedidos/generar-batch") == 1


def test_fe_batch_hint_mentions_click_comparativa():
    assert "Clic en una columna" in HTML or "Clic en una columna" in JS
