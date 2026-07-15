"""ProveedorConfig groups + CodProv aliases."""
from __future__ import annotations

from backend.services.proveedor_config_loader import (
    alias_index_from_groups,
    build_proveedor_groups,
    groups_from_flat_minimos,
    minimos_usd_from_groups,
)


def test_build_groups_merges_aliases_onto_active_canonical():
    active = [
        {
            "proveedor_id": 7,
            "cod_prov": "Insuaminca",
            "nombre_corto": "Insuaminca",
            "monto_minimo_pedido_usd": 50.0,
        },
        {
            "proveedor_id": 11,
            "cod_prov": "MASTRANTO_B",
            "nombre_corto": "Mastranto",
            "monto_minimo_pedido_usd": 50.0,
        },
    ]
    aliases = [
        {"cod_prov": "Insuaminca", "proveedor_id": 7},
        {"cod_prov": "INSUAMINCA_G", "proveedor_id": 7},
        {"cod_prov": "INSUAMINCA_M", "proveedor_id": 7},
        {"cod_prov": "MASTRANTO_B", "proveedor_id": 11},
        {"cod_prov": "MASTRANTO_C", "proveedor_id": 11},
    ]
    groups = build_proveedor_groups(active, aliases)
    assert len(groups) == 2
    ins = next(g for g in groups if g["proveedor_id"] == 7)
    assert ins["cod_prov"] == "Insuaminca"
    assert set(ins["aliases"]) == {"Insuaminca", "INSUAMINCA_G", "INSUAMINCA_M"}
    idx = alias_index_from_groups(groups)
    assert idx["INSUAMINCA_G"]["proveedor_id"] == 7
    assert idx["MASTRANTO_C"]["cod_prov"] == "MASTRANTO_B"
    flat = minimos_usd_from_groups(groups)
    assert flat["INSUAMINCA_M"] == 50.0
    assert flat["MASTRANTO_C"] == 50.0


def test_groups_from_flat_minimos_one_per_cod():
    g = groups_from_flat_minimos({"CHEAP": 50.0, "EXPENSIVE": 15.0})
    assert {x["cod_prov"] for x in g} == {"CHEAP", "EXPENSIVE"}
    assert all(x["aliases"] == [x["cod_prov"]] for x in g)
