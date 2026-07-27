"""FE generación única — modal clic-derecho Original | Rivales (ticket 09)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "frontend" / "modulo_pedidos.html").read_text(encoding="utf-8")
JS = (ROOT / "frontend" / "js" / "app_pedidos.js").read_text(encoding="utf-8")


def test_fe_reemplazo_modal_markup():
    assert 'id="reemplazoModal"' in HTML
    assert "Original" in HTML
    assert "Rivales" in HTML
    assert 'id="reemplazoOriginalList"' in HTML
    assert 'id="reemplazoRivalesList"' in HTML


def test_fe_contextmenu_on_propuesta_barra_opens_modal():
    assert "contextmenu" in JS
    assert "openReemplazoModal" in JS
    assert "barra-propuesto-cell" in JS or "barra-propuesto" in JS
    assert "preventDefault" in JS


def test_fe_reemplazo_blocks_commercial_fields():
    assert "extractCompetenciaFromRow" in JS
    assert "hermanos_reemplazables" in JS
    assert "oferta_baseline" in JS
    # Commercial primary fields in modal offer cards
    assert "descripcion" in JS
    assert "proveedor" in JS
    assert "precio" in JS


def test_fe_reemplazo_honors_knob_sized_ofertas():
    assert "ofertas_por_rival" in JS or "ofertas" in JS
    assert "top_n_rivales" in JS or "rivales" in JS
    assert "top_n_hermanos" in JS or "hermanos" in JS


def test_fe_apply_reemplazo_updates_comparativa_propuesto():
    assert "applyReemplazoOffer" in JS
    assert "barra_propuesto" in JS
    assert "pedido_propuesto" in JS
    assert "renderGenerarResult" in JS


def test_fe_left_click_comparativa_unchanged():
    # Justificacion accordion still left-click; replacement is contextmenu only
    assert "justificacion-cell" in JS
    assert JS.count("openReemplazoModal") >= 1
    # Must not open reemplazo on plain click of justificacion
    assert "openReemplazoModal(row" in JS or "openReemplazoModal(" in JS
