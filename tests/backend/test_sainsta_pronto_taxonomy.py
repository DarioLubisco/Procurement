"""Unit tests for Farma Pronto → SAINSTA taxonomy rewrite (no live DB)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.services.sainsta_pronto_taxonomy import (
    collect_medicinas_codinsts,
    insertable_nodes,
    load_taxonomy,
    plan_sainsta_rewrite,
    render_migration_sql,
    resolve_legacy_descrip,
    validate_taxonomy,
)


@pytest.fixture(scope="module")
def tax():
    return load_taxonomy()


def test_taxonomy_valid(tax):
    ok, errors = validate_taxonomy(tax)
    assert ok, errors


def test_medicinas_preserved_marker(tax):
    assert tax["preserve"]["root_descrip"] == "Medicinas"
    assert "OTC" in tax["preserve"]["child_names"]


def test_no_medicine_pronto_leaves(tax):
    medicine = set(tax["medicine_pronto_excluded"])
    for n in insertable_nodes(tax):
        if n["role"] == "leaf":
            assert n["descrip"] not in medicine


def test_leaf_parents_exist(tax):
    parents = {n["cod_inst"] for n in tax["nodes"] if n["role"] == "parent"}
    for n in tax["nodes"]:
        if n["role"] == "leaf":
            assert n["ins_padre"] in parents


def test_legacy_desodorantes_remaps(tax):
    d = resolve_legacy_descrip("Desodorantes", taxonomy=tax)
    assert d["action"] == "remap"
    assert d["new_descrip"] == "DESODORANTES"
    assert isinstance(d["new_cod_inst"], int)


def test_legacy_medicinas_child_preserved(tax):
    d = resolve_legacy_descrip("OTC", taxonomy=tax)
    assert d["action"] == "preserve_medicinas"


def test_collect_medicinas_subtree():
    rows = [
        {"CodInst": 2, "Descrip": "Medicinas", "InsPadre": 0},
        {"CodInst": 50, "Descrip": "OTC", "InsPadre": 2},
        {"CodInst": 51, "Descrip": "Ampollas", "InsPadre": 2},
        {"CodInst": 9, "Descrip": "Cuidado Personal", "InsPadre": 0},
        {"CodInst": 91, "Descrip": "Desodorantes", "InsPadre": 9},
    ]
    got = collect_medicinas_codinsts(rows)
    assert got == {2, 50, 51}


def test_plan_retires_non_medicine_keeps_medicinas():
    rows = [
        {"CodInst": 2, "Descrip": "Medicinas", "InsPadre": 0},
        {"CodInst": 50, "Descrip": "OTC", "InsPadre": 2},
        {"CodInst": 9, "Descrip": "Cuidado Personal", "InsPadre": 0},
        {"CodInst": 91, "Descrip": "Desodorantes", "InsPadre": 9},
        {"CodInst": 27, "Descrip": "Anulados o Eliminadas", "InsPadre": 0},
        {"CodInst": 4, "Descrip": "xx", "InsPadre": 27},
    ]
    plan = plan_sainsta_rewrite(rows)
    assert 2 in plan["preserve_codinsts"]
    assert 50 in plan["preserve_codinsts"]
    retired_ids = {r["CodInst"] for r in plan["retire_to_anulados"]}
    assert 9 in retired_ids
    assert 91 in retired_ids
    assert 2 not in retired_ids
    assert 50 not in retired_ids
    assert 4 not in retired_ids  # already under Anulados
    assert plan["product_remap_by_old_cod"][91]  # Desodorantes → DESODORANTES leaf
    assert any(i["Descrip"] == "DESODORANTES" for i in plan["inserts"])
    assert any(i["Descrip"] == "Cuidado Personal" and i["role"] == "parent" for i in plan["inserts"])


def test_render_sql_mentions_medicinas_guard():
    rows = [
        {"CodInst": 2, "Descrip": "Medicinas", "InsPadre": 0},
        {"CodInst": 9, "Descrip": "Cuidado Personal", "InsPadre": 0},
        {"CodInst": 91, "Descrip": "Desodorantes", "InsPadre": 9},
        {"CodInst": 27, "Descrip": "Anulados o Eliminadas", "InsPadre": 0},
    ]
    plan = plan_sainsta_rewrite(rows)
    sql = render_migration_sql(plan)
    assert "Medicinas" in sql
    assert "BEGIN TRANSACTION" in sql
    assert "#ProntoLegacyMap" in sql
    assert "#MedicinasPreserve" in sql
    assert "DESODORANTES" in sql
    assert "UPDATE p" in sql and "SET CodInst = m.NewCodInst" in sql


def test_taxonomy_json_on_disk_matches_loader():
    path = Path(__file__).resolve().parents[2] / "backend" / "data" / "sainsta_pronto_taxonomy.json"
    disk = json.loads(path.read_text(encoding="utf-8"))
    assert disk["version"] == load_taxonomy()["version"]
    assert len(disk["nodes"]) == len(load_taxonomy()["nodes"])
