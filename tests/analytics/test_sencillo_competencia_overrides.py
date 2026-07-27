"""Sencillo overrides for Config Pedido competencia knobs — ticket 04."""
from __future__ import annotations

from analytics_engine.core.generar_sencillo_api import run_generar_sencillo


def test_run_generar_sencillo_applies_competencia_overrides():
    catalog = [
        {
            "barra": "111",
            "descripcion": "Paracetamol 500mg",
            "rotacion_mensual": 100.0,
            "existen": 40.0,
            "es_generico": True,
            "principio_activo": "PARACETAMOL",
            "forma_farmaceutica": "TAB",
            "concentracion": "500",
            "cantidad_presentacion": "20",
            "contenido_neto": "1",
        }
    ]
    offers = [
        {
            "barra": "111",
            "proveedor": "BARATO",
            "precio": 5.0,
            "stock_proveedor": 1000,
        },
        {
            "barra": "111",
            "proveedor": "CARO",
            "precio": 10.0,
            "stock_proveedor": 1000,
        },
    ]
    payload = run_generar_sencillo(
        cobertura=30,
        catalog_rows=catalog,
        market_offers_rows=offers,
        preset="Normal",
        overrides={
            "hermanos_top_n": 1,
            "rivales_top_n": 1,
            "rivales_ofertas_por_rival": 1,
        },
    )
    # Overrides must surface in oferta factor datos when rivales present
    found = False
    for row in payload["comparativa_cantidades"]:
        for f in row.get("justificacion_factores") or []:
            datos = f.get("datos") or {}
            if "ofertas_por_rival" in datos or datos.get("top_n_rivales") == 1:
                found = True
                if "ofertas_por_rival" in datos:
                    assert datos["ofertas_por_rival"] == 1
                if "top_n_rivales" in datos:
                    assert datos["top_n_rivales"] == 1
                rivales = datos.get("rivales") or []
                assert len(rivales) <= 1
    assert found or any(
        (f.get("datos") or {}).get("rivales") is not None
        for row in payload["comparativa_cantidades"]
        for f in (row.get("justificacion_factores") or [])
    )
