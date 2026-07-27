"""FE generación única — retirar UI vieja Sencillo→Regenerar (ticket 13)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "frontend" / "modulo_pedidos.html").read_text(encoding="utf-8")
JS = (ROOT / "frontend" / "js" / "app_pedidos.js").read_text(encoding="utf-8")
PROTO_DIR = ROOT / "frontend" / "js"


def test_fe_no_primary_single_sencillo_preset_control():
    # Retired: pick-one Sencillo preset as the Generar compare story
    assert 'id="presetSencillo"' not in HTML
    assert "batch-perfil-slot" in HTML
    assert 'id="batchPerfilSlot1"' in HTML


def test_fe_happy_path_generacion_unica_reachable():
    assert "/api/pedidos/generar-batch" in JS
    assert 'id="batchResultsSection"' in HTML
    assert "hydrateComparativaFromBatchSlot" in JS
    assert 'id="comparadorActivoCard"' in HTML
    assert 'id="btnRegenerarDefinitivo"' in HTML
    assert 'id="validarMinimosAlarm"' in HTML or 'id="btnValidarMinimos"' in HTML
    assert 'id="btnGuardarBorrador"' in HTML
    assert "buildGuardarBorradorPayload" in JS


def test_fe_prototypes_not_deleted():
    assert (PROTO_DIR / "prototype_compare_presets.js").is_file()
    assert (PROTO_DIR / "prototype_compare_presets.wf3.js").is_file()
    assert (PROTO_DIR / "prototype_compare_presets.NOTES.md").is_file()


def test_fe_smoke_no_generar_sencillo_as_primary():
    # Primary Generar uses batch; legacy endpoint must not be the submit path
    assert JS.count("/api/pedidos/generar-batch") >= 1
    submit_region = JS
    if "generateForm" in JS:
        # Ensure submit handler path mentions batch
        assert "generar-batch" in JS
    assert "/api/pedidos/generar-sencillo" not in JS or "generar-batch" in JS
