"""FE generación única — ValidarMinimos post-elección (ticket 11)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "frontend" / "modulo_pedidos.html").read_text(encoding="utf-8")
JS = (ROOT / "frontend" / "js" / "app_pedidos.js").read_text(encoding="utf-8")


def test_fe_batch_completion_does_not_force_validar_minimos():
    assert "stashBatchResult" in JS
    assert "/api/pedidos/generar-batch" in JS
    gen_batch_idx = JS.index("/api/pedidos/generar-batch")
    window = JS[gen_batch_idx : gen_batch_idx + 800]
    assert "stashBatchResult" in window
    assert "callValidarMinimos" not in window
    assert "validar-minimos" not in window


def test_fe_vm_alarm_after_profile_selection():
    assert 'id="validarMinimosAlarm"' in HTML
    assert "showValidarMinimosAlarm" in JS
    assert "showValidarMinimosAlarm({ afterSelection: true })" in JS
    assert "function hydrateComparativaFromBatchSlot" in JS


def test_fe_vm_button_opens_existing_panel_flow():
    assert 'id="btnValidarMinimos"' in HTML
    assert 'id="validarMinimosPanel"' in HTML
    assert 'id="btnVmAceptar"' in HTML
    assert 'id="btnVmRedistribuir"' in HTML
    assert "callValidarMinimos('evaluar')" in JS


def test_fe_vm_operates_on_active_perfil_only():
    assert "callValidarMinimos" in JS
    assert "syncActiveBatchSlotFromLastGenerar" in JS
    assert "applyValidarMinimosResponse" in JS
    assert "activeBatchPerfilId" in JS
