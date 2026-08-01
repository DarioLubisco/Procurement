"""Unit tests for MDM → SAINSTA taxonomy rewrite (no live DB)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.services.sainsta_mdm_taxonomy import (
    collect_medicinas_codinsts,
    insertable_nodes,
    load_taxonomy,
    plan_sainsta_rewrite,
    render_migration_sql,
    resolve_mdm_cod_inst,
    validate_taxonomy,
)


@pytest.fixture(scope="module")
def tax():
    return load_taxonomy()


def test_taxonomy_valid(tax):
    ok, errors = validate_taxonomy(tax)
    assert ok, errors


def test_three_levels_and_ranges(tax):
    assert tax["stats"]["dominios"] == 5
    assert tax["stats"]["categorias"] == 36
    assert tax["stats"]["subcategorias"] == 98
    roles = {n["role"] for n in insertable_nodes(tax)}
    assert "dominio" in roles and "categoria" in roles and "subcategoria" in roles
    assert tax["legacy_root"]["cod_inst"] == 2999


def test_no_medicamento_alopatico_inserted(tax):
    assert "MEDICAMENTO_ALOPATICO" not in tax["domains_included"]
    assert all(n.get("descrip") != "MEDICAMENTO_ALOPATICO" for n in insertable_nodes(tax))


def test_exact_descrip_from_mdm(tax):
    leaves = [n for n in tax["nodes"] if n["role"] == "subcategoria"]
    assert any(n["descrip"] == "DESODORANTES Y ANTITRANSPIRANTES" for n in leaves)
    assert any(n["descrip"] == "CHAMPU Y ACONDICIONADOR" for n in leaves)


def test_resolve_prefers_subcategoria(tax):
    cod = resolve_mdm_cod_inst(
        "COSMETICO_CUIDADO_PERSONAL",
        "CUIDADO CORPORAL",
        "DESODORANTES Y ANTITRANSPIRANTES",
        taxonomy=tax,
    )
    assert isinstance(cod, int) and 3200 <= cod <= 3999
    cat_only = resolve_mdm_cod_inst(
        "COSMETICO_CUIDADO_PERSONAL", "CUIDADO CORPORAL", None, taxonomy=tax
    )
    assert isinstance(cat_only, int) and 3100 <= cat_only <= 3199
    assert cat_only != cod


def test_collect_medicinas():
    rows = [
        {"CodInst": 2, "Descrip": "Medicinas", "InsPadre": 0},
        {"CodInst": 50, "Descrip": "OTC", "InsPadre": 2},
        {"CodInst": 9, "Descrip": "Cuidado Personal", "InsPadre": 0},
    ]
    assert collect_medicinas_codinsts(rows) == {2, 50}


def test_plan_reparents_legacy_keeps_medicinas():
    rows = [
        {"CodInst": 2, "Descrip": "Medicinas", "InsPadre": 0},
        {"CodInst": 50, "Descrip": "OTC", "InsPadre": 2},
        {"CodInst": 9, "Descrip": "Cuidado Personal", "InsPadre": 0},
        {"CodInst": 55, "Descrip": "Desodorantes", "InsPadre": 9},
        {"CodInst": 27, "Descrip": "Anulados o Eliminadas", "InsPadre": 0},
        {"CodInst": 4, "Descrip": "xx", "InsPadre": 27},
    ]
    plan = plan_sainsta_rewrite(rows)
    assert 2 in plan["preserve_codinsts"] and 50 in plan["preserve_codinsts"]
    reparented = {r["CodInst"] for r in plan["reparent_to_legacy"]}
    assert 9 in reparented and 55 in reparented
    assert 2 not in reparented and 4 not in reparented
    assert any(i["Descrip"] == "LEGACY_NO_MEDICINA" for i in plan["inserts"])
    assert any(i["Descrip"] == "COSMETICO_CUIDADO_PERSONAL" for i in plan["inserts"])


def test_render_sql_guards():
    sql = render_migration_sql()
    assert "LEGACY_NO_MEDICINA" in sql
    assert "Medicinas" in sql
    assert "COSMETICO_CUIDADO_PERSONAL" in sql
    assert "por_aprobacion_equivalencias" in sql
    assert "BEGIN TRANSACTION" in sql
    assert "2999" in sql


def test_json_on_disk_matches_loader():
    path = (
        Path(__file__).resolve().parents[2]
        / "backend"
        / "data"
        / "sainsta_mdm_taxonomy.json"
    )
    disk = json.loads(path.read_text(encoding="utf-8"))
    assert disk["version"] == load_taxonomy()["version"]
    assert len(disk["nodes"]) == len(load_taxonomy()["nodes"])
