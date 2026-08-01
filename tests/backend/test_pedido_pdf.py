"""Tests for pedido PDF totals helpers."""
from backend.services.pedido_pdf import (
    build_pedido_pdf_bytes,
    compute_propuesto_totals,
    _line_delta_usd,
)


def test_compute_propuesto_totals_global_and_by_prov():
    prop = [
        {"barra": "1", "proveedor": "A", "cantidad": 2, "precio": 5.0},
        {"barra": "2", "proveedor": "B", "cantidad": 1, "precio": 10.0},
        {"barra": "3", "proveedor": "A", "cantidad": 3, "precio": 1.0},
    ]
    t = compute_propuesto_totals(prop)
    assert t["total_usd"] == 23.0  # 10 + 10 + 3
    assert t["by_proveedor"]["A"] == 13.0
    assert t["by_proveedor"]["B"] == 10.0
    assert t["missing_precios"] == 0
    assert t["partial"] is False


def test_compute_propuesto_totals_partial_missing_precio():
    prop = [
        {"barra": "1", "proveedor": "A", "cantidad": 2, "precio": 5.0},
        {"barra": "2", "proveedor": "A", "cantidad": 1, "precio": None},
    ]
    t = compute_propuesto_totals(prop)
    assert t["total_usd"] == 10.0
    assert t["missing_precios"] == 1
    assert t["partial"] is True


def test_line_delta_usd():
    assert _line_delta_usd(qty_b=2, qty_p=3, precio_b=1.0, precio_p=1.5) == 2.5
    assert _line_delta_usd(qty_b=1, qty_p=1, precio_b=None, precio_p=1.0) is None


def test_sucedaneo_precios_helpers():
    from backend.services.pedido_pdf import (
        _oferta_baseline_precio,
        _precio_propuesto_for_row,
        _line_delta_usd,
    )

    row = {
        "barra_baseline": "OLD",
        "barra_propuesto": "NEW",
        "qty_baseline": 2,
        "qty_propuesto": 2,
        "justificacion_factores": [
            {
                "codigo": "sucedaneo",
                "datos": {
                    "oferta_baseline": {
                        "barra": "OLD",
                        "precio": 1.68,
                        "proveedor": "INTERCONTINENTAL",
                    }
                },
            },
            {
                "codigo": "oferta",
                "datos": {"precio": 1.51, "proveedor": "CRISTMEDICAL"},
            },
        ],
    }
    pb = _oferta_baseline_precio(row)
    pp = _precio_propuesto_for_row(row, {"NEW": 1.51})
    assert pb == 1.68
    assert pp == 1.51
    assert round(_line_delta_usd(qty_b=2, qty_p=2, precio_b=pb, precio_p=pp), 4) == -0.34


def test_oferta_hist_independent_of_elasticidad():
    from backend.services.pedido_pdf import _oferta_hist_from_row

    row = {
        "justificacion_factores": [
            {
                "codigo": "oferta",
                "datos": {
                    "precio": 1.51,
                    "media_de_mediana": 1.5225,
                    "desvio": -0.008,
                    "delta_vs_media_usd": -0.0125,
                },
            }
        ]
    }
    h = _oferta_hist_from_row(row)
    assert h["media"] == 1.5225
    assert h["desvio"] == -0.008
    # No elasticidad field required
    assert "elasticidad" not in (row["justificacion_factores"][0]["datos"] or {})


def test_build_pdf_bytes_produces_valid_pdf():
    pdf = build_pedido_pdf_bytes(
        propuesta_id=99,
        cod_prov="ZAKI",
        estado="BORRADOR",
        revision=2,
        snapshot_hash="abc123deadbeef",
        comparativa=[
            {
                "barra_baseline": "OLD",
                "barra_propuesto": "NEW",
                "qty_baseline": 1,
                "qty_propuesto": 2,
                "desc_baseline": "Old prod",
                "desc_propuesto": "New prod",
                "justificacion_delta": "mejor precio",
                "justificacion_factores": [
                    {
                        "datos": {
                            "oferta_baseline": {"barra": "OLD", "precio": 4.0},
                            "precio": 3.0,
                        }
                    }
                ],
            }
        ],
        propuesto=[
            {
                "barra": "NEW",
                "descripcion": "New prod",
                "proveedor": "ZAKI",
                "cantidad": 2,
                "precio": 3.0,
            }
        ],
    )
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 800
    # Hash must not appear in cleartext trailer/meta (cabecera limpia)
    assert b"abc123deadbeef" not in pdf
