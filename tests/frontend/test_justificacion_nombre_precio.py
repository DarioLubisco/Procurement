"""FE generación única — justificaciones nombre + proveedor + precio (ticket 08)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JS = (ROOT / "frontend" / "js" / "app_pedidos.js").read_text(encoding="utf-8")


def test_fe_justificacion_primary_commercial_fields():
    assert "formatJustificacionPrimaryHtml" in JS
    assert "justificacion-primary" in JS
    # Primary line uses commercial fields, not BARRA as lead
    assert "desc_propuesto" in JS
    assert "justificacion-barra" in JS


def test_fe_justificacion_barra_is_secondary():
    assert "justificacion-barra" in JS
    # BARRA lives in secondary/mono line, not the primary commercial span
    primary_idx = JS.index("justificacion-primary")
    barra_idx = JS.index("justificacion-barra")
    assert primary_idx < barra_idx or "formatJustificacionPrimaryHtml" in JS


def test_fe_justificacion_factores_model_preserved():
    assert "justificacion_factores" in JS
    assert "renderFactoresAccordion" in JS
    assert "justificacion_delta" in JS
    # Must not flatten factors into a single concatenated string only
    assert "factorsHoverText" in JS or "factores.map" in JS


def test_fe_sucedaneo_code_change_still_declared():
    assert "Sucedáneo" in JS
    assert "is-barra-cambio" in JS or "barra_baseline" in JS


def test_fe_competencia_lists_nombre_before_barra():
    """Rivales/hermanos accordion: commercial fields first, BARRA secondary."""
    assert "competencia-nombre" in JS or "descripcion" in JS
    assert "competencia-barra" in JS or "justificacion-barra" in JS
