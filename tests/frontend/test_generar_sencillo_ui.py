"""FE generación única — structural checks (evolved from Generar Sencillo UI)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "frontend" / "modulo_pedidos.html").read_text(encoding="utf-8")
JS = (ROOT / "frontend" / "js" / "app_pedidos.js").read_text(encoding="utf-8")


def test_fe_has_batch_controls_and_comparativa_tables():
    # Ticket 13: single presetSencillo retired from primary path
    assert 'id="presetSencillo"' not in HTML
    assert "batch-perfil-slot" in HTML
    assert 'id="criteriosAgrupacion"' in HTML
    assert 'id="presupuestoMaximo"' in HTML
    assert 'id="comparativaTableBody"' in HTML
    assert 'id="propuestoTableBody"' in HTML
    assert "Justificación" in HTML
    assert "Proveedor" in HTML
    assert 'id="btnText">Generar</span>' in HTML or ">Generar<" in HTML
    assert 'id="categoriesBar"' in HTML or 'id="btnEditCategories"' in HTML
    assert 'id="categoriesModal"' in HTML
    assert 'id="configBody"' in HTML
    assert 'id="btnToggleConfig"' in HTML
    assert "avanzadas-contingencia" in HTML or "Opciones avanzadas" in HTML
    assert "pedidos-table-scroll" in HTML


def test_fe_config_pedido_competencia_knobs():
    """Ticket 04 — hermanos / rivales / ofertas por rival in Config Pedido."""
    assert 'id="hermanosTopN"' in HTML
    assert 'id="rivalesTopN"' in HTML
    assert 'id="rivalesOfertasPorRival"' in HTML
    assert 'value="3"' in HTML[HTML.index('id="hermanosTopN"') : HTML.index('id="hermanosTopN"') + 120]
    assert 'value="3"' in HTML[HTML.index('id="rivalesTopN"') : HTML.index('id="rivalesTopN"') + 120]
    assert 'value="2"' in HTML[HTML.index('id="rivalesOfertasPorRival"') : HTML.index('id="rivalesOfertasPorRival"') + 140]
    assert "collectCompetenciaOverrides" in JS
    assert "hermanos_top_n" in JS
    assert "rivales_ofertas_por_rival" in JS
    assert "overrides: collectCompetenciaOverrides()" in JS or "overrides: collectCompetenciaOverrides" in JS


def test_fe_calls_generar_batch_endpoint():
    assert "/api/pedidos/generar-batch" in JS
    assert "renderGenerarResult" in JS
    assert "criterios_agrupacion" in JS
    assert "buildSencilloPayload" in JS or "buildBatchPayload" in JS
    assert "/api/rotacion-grupal/atributos" in JS
    assert "fetchCriteriosAtributos" in JS
    assert "openCategoriesModal" in JS
    assert "setConfigCollapsed" in JS
    assert "syn_ped_defaults_v2" in JS
    assert "collectDefaultsSnapshot" in JS


def test_fe_regenerar_activo_on_comparador():
    assert 'id="comparadorActivoCard"' in HTML
    assert 'id="btnRegenerarDefinitivo"' in HTML
    assert 'id="nivelDefinitivo"' in HTML
    assert 'id="definitivoOverridesHost"' in HTML
    assert 'id="btnResetDefinitivoOverrides"' in HTML
    assert 'id="definitivoAmpSection"' in HTML
    assert 'id="comparativaSoloCambios"' in HTML
    assert 'id="btnSaveCustomPreset"' in HTML
    assert "/api/pedidos/regenerar-definitivo" in JS
    assert "/api/pedidos/overrides-schema" in JS
    assert "base_preset" in JS
    assert "renderDefinitivoOverrideFields" in JS
    assert "loadDefinitivoOverrideSchema" in JS
    assert "fillDefinitivoFromSchemaDefaults" in JS
    assert "comparativaSoloCambios" in JS
    assert "isComparativaIdentityRow" in JS
    assert "/api/pedidos/presets" in JS
    assert "s4_enabled" in HTML  # documented as excluded
    assert "sucedáneos" in HTML or "κ" in HTML  # κ opt-in copy ADR-0017
    assert "field.help" in JS or "field.hint" in JS
    assert "forced_includes" not in JS or "deprecated" in JS.lower()
    assert "justificacion-resumen" in JS or "justificacion_factores" in JS
    assert "comparativa-detail-row" in JS
    assert "ⓘ" in JS or "aria-label', 'Información'" in JS or 'Información' in JS


def test_fe_preset_order_conservador_normal_agresivo():
    # Batch slots + Definitivo base: Conservador → Normal → Agresivo
    for select_id in ('batchPerfilSlot1', 'basePresetDefinitivo'):
        start = HTML.index(f'id="{select_id}"')
        chunk = HTML[start : start + 450]
        i_c = chunk.index("Conservador")
        i_n = chunk.index("Normal")
        i_a = chunk.index("Agresivo")
        assert i_c < i_n < i_a


def test_fe_guardar_borrador_after_definitivo():
    assert 'id="btnGuardarBorrador"' in HTML
    assert "Guardar borrador" in HTML
    assert "/api/pedidos/guardar-borrador" in JS
    assert "setDefinitivoReadyForBorrador" in JS
    assert "definitivoReadyForBorrador" in JS
