"""FE Generar Sencillo — structural checks for ticket 10 (no browser)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "frontend" / "modulo_pedidos.html").read_text(encoding="utf-8")
JS = (ROOT / "frontend" / "js" / "app_pedidos.js").read_text(encoding="utf-8")


def test_fe_has_sencillo_controls_and_comparativa_tables():
    assert 'id="presetSencillo"' in HTML
    assert 'id="criteriosAgrupacion"' in HTML
    assert 'id="presupuestoMaximo"' in HTML
    assert 'id="comparativaTableBody"' in HTML
    assert 'id="propuestoTableBody"' in HTML
    assert "Justificación" in HTML
    assert "Proveedor" in HTML
    assert "Generar (Sencillo)" in HTML


def test_fe_calls_unified_generar_sencillo_endpoint():
    assert "/api/pedidos/generar-sencillo" in JS
    assert "renderGenerarResult" in JS
    assert "criterios_agrupacion" in JS
    assert "buildSencilloPayload" in JS


def test_fe_regenerar_definitivo_distinct_from_sencillo():
    assert "Regenerar Pedido Definitivo" in HTML
    assert 'id="btnRegenerarDefinitivo"' in HTML
    assert 'id="nivelDefinitivo"' in HTML
    assert 'id="definitivoOverridesHost"' in HTML
    assert "/api/pedidos/regenerar-definitivo" in JS
    assert "/api/pedidos/overrides-schema" in JS
    assert "renderDefinitivoOverrideFields" in JS
    assert "loadDefinitivoOverrideSchema" in JS
    assert "s4_enabled" in HTML  # documented as excluded
    assert "sucedáneos" in HTML or "κ" in HTML  # κ opt-in copy ADR-0017
    assert "field.help" in JS or "field.hint" in JS
    assert "forced_includes" not in JS or "deprecated" in JS.lower()
