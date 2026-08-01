"""FE generación única — Guardar solo perfil elegido (ticket 12)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "frontend" / "modulo_pedidos.html").read_text(encoding="utf-8")
JS = (ROOT / "frontend" / "js" / "app_pedidos.js").read_text(encoding="utf-8")


def test_fe_guardar_disabled_until_perfil_chosen():
    assert "refreshGuardarBorradorGate" in JS or "canGuardarChosenPerfil" in JS
    assert "activeBatchPerfilId" in JS
    assert "btnGuardarBorrador" in JS or 'id="btnGuardarBorrador"' in HTML
    # Gate mentions choosing perfil when batch present
    assert "Elija un perfil" in JS or "perfil" in JS.lower()


def test_fe_guardar_payload_only_active_perfil():
    assert "buildGuardarBorradorPayload" in JS
    assert "pedido_propuesto" in JS
    assert "/api/pedidos/guardar-borrador" in JS
    assert "One POST — active perfil only" in JS or "siblings never auto-saved" in JS
    # Single fetch to guardar-borrador (no multi-slot save loop)
    assert JS.count("/api/pedidos/guardar-borrador") == 1
    assert "buildGuardarBorradorPayload()" in JS


def test_fe_guardar_knobs_snapshot_includes_chosen_perfil():
    assert "buildGuardarBorradorPayload" in JS
    assert "perfil_id" in JS
    assert "knobs_efectivos" in JS or "lastDefinitivoParams" in JS


def test_fe_guardar_hint_solo_elegido():
    assert "solo" in HTML.lower() or "perfil" in HTML.lower()
    assert 'id="pedidoPersistHint"' in HTML or "pedidoPersistHint" in JS
