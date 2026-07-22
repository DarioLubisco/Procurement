"""Farma Pronto → Softland SAINSTA taxonomy (non-medicine rewrite).

Medicinas (and its InsPadre subtree) are preserved. All other category nodes
are replaced by a 2-level tree whose leaves match Farma Pronto `product_cat`
names. Parents are synthetic groupings for the Pedidos modal hierarchy.

Source of truth: ``backend/data/sainsta_pronto_taxonomy.json``.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "sainsta_pronto_taxonomy.json"


@lru_cache(maxsize=1)
def load_taxonomy(path: Optional[str] = None) -> Dict[str, Any]:
    p = Path(path) if path else _DATA_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "nodes" not in data:
        raise ValueError(f"Invalid taxonomy file: {p}")
    return data


def clear_taxonomy_cache() -> None:
    load_taxonomy.cache_clear()


def pronto_leaf_nodes(taxonomy: Optional[Mapping[str, Any]] = None) -> List[Dict[str, Any]]:
    tax = taxonomy or load_taxonomy()
    return [n for n in tax["nodes"] if n.get("role") == "leaf"]


def parent_nodes(taxonomy: Optional[Mapping[str, Any]] = None) -> List[Dict[str, Any]]:
    tax = taxonomy or load_taxonomy()
    return [n for n in tax["nodes"] if n.get("role") == "parent"]


def insertable_nodes(taxonomy: Optional[Mapping[str, Any]] = None) -> List[Dict[str, Any]]:
    """Nodes to INSERT into SAINSTA (parents + leaves). Preserve markers excluded."""
    tax = taxonomy or load_taxonomy()
    return [n for n in tax["nodes"] if n.get("role") in ("parent", "leaf")]


def medicinas_preserve_names(taxonomy: Optional[Mapping[str, Any]] = None) -> Set[str]:
    tax = taxonomy or load_taxonomy()
    names = {str(tax["preserve"]["root_descrip"])}
    for n in tax["preserve"].get("child_names") or []:
        names.add(str(n))
    return names


def resolve_legacy_descrip(
    descrip: str,
    *,
    taxonomy: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Map a current SAINSTA Descrip to remap action.

    Returns dict with keys:
      action: preserve_medicinas | remap | unmapped
      new_cod_inst: optional int
      new_descrip: optional str
    """
    tax = taxonomy or load_taxonomy()
    name = (descrip or "").strip()
    if not name:
        return {"action": "unmapped", "new_cod_inst": None, "new_descrip": None}
    if name in medicinas_preserve_names(tax):
        return {"action": "preserve_medicinas", "new_cod_inst": None, "new_descrip": None}
    hit = (tax.get("legacy_name_to_new") or {}).get(name)
    if not hit:
        return {"action": "unmapped", "new_cod_inst": None, "new_descrip": None}
    return {
        "action": hit.get("action", "unmapped"),
        "new_cod_inst": hit.get("new_cod_inst"),
        "new_descrip": hit.get("new_descrip"),
    }


def collect_medicinas_codinsts(
    rows: Sequence[Mapping[str, Any]],
    *,
    root_descrip: str = "Medicinas",
) -> Set[int]:
    """Return CodInst set for Medicinas root + all descendants via InsPadre."""
    by_id: Dict[int, Mapping[str, Any]] = {}
    children: Dict[int, List[int]] = {}
    root_ids: List[int] = []
    for row in rows:
        cod = int(row["CodInst"])
        by_id[cod] = row
        padre = int(row.get("InsPadre") or 0)
        children.setdefault(padre, []).append(cod)
        if str(row.get("Descrip") or "").strip() == root_descrip and padre == 0:
            root_ids.append(cod)

    out: Set[int] = set()
    stack = list(root_ids)
    while stack:
        cur = stack.pop()
        if cur in out:
            continue
        out.add(cur)
        stack.extend(children.get(cur, []))
    return out


def plan_sainsta_rewrite(
    existing_rows: Sequence[Mapping[str, Any]],
    *,
    taxonomy: Optional[Mapping[str, Any]] = None,
    anulados_root: int = 27,
) -> Dict[str, Any]:
    """Build a dry-run plan: which rows to keep, retire, insert, and product remaps.

    ``existing_rows``: list of {CodInst, Descrip, InsPadre}.
    """
    tax = taxonomy or load_taxonomy()
    preserve = collect_medicinas_codinsts(
        existing_rows, root_descrip=str(tax["preserve"]["root_descrip"])
    )
    existing_by_id = {int(r["CodInst"]): r for r in existing_rows}
    existing_ids = set(existing_by_id)

    retire: List[Dict[str, Any]] = []
    for row in existing_rows:
        cod = int(row["CodInst"])
        if cod in preserve:
            continue
        if cod == int(anulados_root):
            continue
        # Already under Anulados — leave
        if int(row.get("InsPadre") or 0) == int(anulados_root):
            continue
        retire.append(
            {
                "CodInst": cod,
                "Descrip": row.get("Descrip"),
                "InsPadre_old": row.get("InsPadre"),
                "InsPadre_new": int(anulados_root),
                "Descrip_new": f"OLD::{str(row.get('Descrip') or '').strip()}"[:40],
            }
        )

    inserts = []
    for node in insertable_nodes(tax):
        cod = int(node["cod_inst"])
        if cod in existing_ids and cod in preserve:
            continue
        inserts.append(
            {
                "CodInst": cod,
                "Descrip": node["descrip"],
                "InsPadre": int(node["ins_padre"]),
                "role": node["role"],
                "pronto_id": node.get("pronto_id"),
                "exists": cod in existing_ids,
            }
        )

    product_remap_by_old_cod: Dict[int, int] = {}
    unmapped_legacy: List[Dict[str, Any]] = []
    for row in existing_rows:
        cod = int(row["CodInst"])
        if cod in preserve or cod == int(anulados_root):
            continue
        if int(row.get("InsPadre") or 0) == int(anulados_root):
            continue
        decision = resolve_legacy_descrip(str(row.get("Descrip") or ""), taxonomy=tax)
        if decision["action"] == "remap" and decision["new_cod_inst"] is not None:
            product_remap_by_old_cod[cod] = int(decision["new_cod_inst"])
        elif decision["action"] != "preserve_medicinas":
            unmapped_legacy.append(
                {
                    "CodInst": cod,
                    "Descrip": row.get("Descrip"),
                    "decision": decision["action"],
                }
            )

    return {
        "preserve_codinsts": sorted(preserve),
        "retire_to_anulados": retire,
        "inserts": inserts,
        "product_remap_by_old_cod": product_remap_by_old_cod,
        "unmapped_legacy": unmapped_legacy,
        "stats": {
            "existing": len(existing_rows),
            "preserve": len(preserve),
            "retire": len(retire),
            "inserts": len(inserts),
            "remap_rules": len(product_remap_by_old_cod),
            "unmapped": len(unmapped_legacy),
        },
    }


def render_migration_sql(
    plan: Optional[Mapping[str, Any]] = None,
    *,
    taxonomy: Optional[Mapping[str, Any]] = None,
    portable: bool = True,
) -> str:
    """Render transactional T-SQL.

    Default ``portable=True``: preserves Medicinas by name/InsPadre CTE and remaps
    SAPROD via legacy Descrip → new CodInst (safe across DB id differences).

    If ``portable=False`` and ``plan`` is provided, also emits CodInst-specific
    retire/remap lines useful for dry-run audits against a known dump.
    """
    tax = taxonomy or load_taxonomy()
    lines: List[str] = [
        "-- ============================================================",
        "-- 013_sainsta_pronto_non_medicine.sql",
        "-- Rewrite non-medicine SAINSTA nodes to Farma Pronto leaves.",
        "-- Preserves Medicinas subtree (by Descrip/InsPadre, not fixture ids).",
        "-- Retires other nodes under Anulados; remaps dbo.SAPROD.CodInst.",
        "-- REVIEW + BACKUP before running against production.",
        "-- ============================================================",
        "SET XACT_ABORT ON;",
        "BEGIN TRANSACTION;",
        "",
        "-- 0) Snapshot",
        "IF OBJECT_ID(N'Procurement.SAINSTA_Backup_Pronto', N'U') IS NULL",
        "BEGIN",
        "    SELECT * INTO Procurement.SAINSTA_Backup_Pronto FROM dbo.SAINSTA;",
        "END",
        "IF OBJECT_ID(N'Procurement.SAPROD_CodInst_Backup_Pronto', N'U') IS NULL",
        "BEGIN",
        "    SELECT CodProd, CodInst INTO Procurement.SAPROD_CodInst_Backup_Pronto FROM dbo.SAPROD;",
        "END",
        "",
        "-- 1) Anulados root",
        "IF NOT EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 27)",
        "BEGIN",
        "    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre)",
        "    VALUES (27, N'Anulados o Eliminadas', 0);",
        "END",
        "",
        "-- 2) Upsert Pronto parents + leaves (CodInst 2100+/2200+)",
    ]

    for node in insertable_nodes(tax):
        cod = int(node["cod_inst"])
        descrip = str(node["descrip"]).replace("'", "''")
        padre = int(node["ins_padre"])
        lines.append(
            "IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = "
            f"{cod})\n"
            "    UPDATE dbo.SAINSTA SET "
            f"Descrip = N'{descrip}', InsPadre = {padre} WHERE CodInst = {cod};\n"
            "ELSE\n"
            "    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) "
            f"VALUES ({cod}, N'{descrip}', {padre});"
        )

    # Legacy Descrip → new leaf CodInst map
    lines.extend(
        [
            "",
            "-- 3) Legacy Descrip → new CodInst map (name-based; DB-id agnostic)",
            "IF OBJECT_ID(N'tempdb..#ProntoLegacyMap') IS NOT NULL DROP TABLE #ProntoLegacyMap;",
            "CREATE TABLE #ProntoLegacyMap (",
            "    OldDescrip NVARCHAR(100) NOT NULL PRIMARY KEY,",
            "    NewCodInst INT NOT NULL",
            ");",
        ]
    )
    legacy = tax.get("legacy_name_to_new") or {}
    for old_name, hit in sorted(legacy.items()):
        if hit.get("action") != "remap" or hit.get("new_cod_inst") is None:
            continue
        old_sql = str(old_name).replace("'", "''")
        lines.append(
            f"INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) "
            f"VALUES (N'{old_sql}', {int(hit['new_cod_inst'])});"
        )

    lines.extend(
        [
            "",
            "-- 4) Medicinas subtree (preserve)",
            ";WITH MedicinasTree AS (",
            "    SELECT CodInst FROM dbo.SAINSTA",
            "    WHERE Descrip = N'Medicinas' AND ISNULL(InsPadre, 0) = 0",
            "    UNION ALL",
            "    SELECT c.CodInst",
            "    FROM dbo.SAINSTA c",
            "    INNER JOIN MedicinasTree p ON c.InsPadre = p.CodInst",
            ")",
            "SELECT CodInst INTO #MedicinasPreserve FROM MedicinasTree;",
            "",
            "-- 5) Remap SAPROD while old Descrip values still intact",
            "UPDATE p",
            "SET CodInst = m.NewCodInst",
            "FROM dbo.SAPROD AS p",
            "INNER JOIN dbo.SAINSTA AS i ON p.CodInst = i.CodInst",
            "INNER JOIN #ProntoLegacyMap AS m ON i.Descrip = m.OldDescrip",
            "WHERE p.CodInst NOT IN (SELECT CodInst FROM #MedicinasPreserve);",
            "",
            "-- 6) Retire non-medicine / non-Pronto-range / non-Anulados nodes",
            "UPDATE i",
            "SET InsPadre = 27,",
            "    Descrip = LEFT(N'OLD::' + LTRIM(RTRIM(i.Descrip)), 40)",
            "FROM dbo.SAINSTA AS i",
            "WHERE i.CodInst <> 27",
            "  AND ISNULL(i.InsPadre, 0) <> 27",
            "  AND i.Descrip NOT LIKE N'OLD::%'",
            "  AND i.CodInst NOT BETWEEN 2100 AND 2499",
            "  AND i.CodInst NOT IN (SELECT CodInst FROM #MedicinasPreserve);",
            "",
            "-- 7) Sanity",
            "IF NOT EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE Descrip = N'Medicinas' AND ISNULL(InsPadre, 0) = 0)",
            "BEGIN",
            "    RAISERROR(N'Medicinas root missing after migration', 16, 1);",
            "    ROLLBACK TRANSACTION;",
            "    RETURN;",
            "END",
            "",
            "COMMIT TRANSACTION;",
            "GO",
            "",
            f"-- Taxonomy version: {tax.get('version')}",
            f"-- Insertable nodes: {len(insertable_nodes(tax))}",
            f"-- Legacy remap rules: {sum(1 for h in legacy.values() if h.get('action')=='remap')}",
        ]
    )

    if not portable and plan is not None:
        lines.extend(
            [
                "",
                "-- ---- Audit appendix (from plan; not executed) ----",
                f"-- preserve_codinsts: {plan.get('preserve_codinsts')}",
                f"-- retire_count: {len(plan.get('retire_to_anulados') or [])}",
                f"-- plan_remap_count: {len(plan.get('product_remap_by_old_cod') or {})}",
            ]
        )
    return "\n".join(lines) + "\n"


def validate_taxonomy(taxonomy: Optional[Mapping[str, Any]] = None) -> Tuple[bool, List[str]]:
    """Structural checks; returns (ok, errors)."""
    tax = taxonomy or load_taxonomy()
    errors: List[str] = []
    nodes = tax.get("nodes") or []
    ids = [int(n["cod_inst"]) for n in nodes]
    if len(ids) != len(set(ids)):
        errors.append("duplicate cod_inst in nodes")
    parents = {int(n["cod_inst"]) for n in nodes if n.get("role") == "parent"}
    for n in nodes:
        if n.get("role") != "leaf":
            continue
        padre = int(n.get("ins_padre") or 0)
        if padre not in parents:
            errors.append(f"leaf {n.get('descrip')} parent {padre} missing")
        if not n.get("descrip"):
            errors.append("leaf with empty descrip")
    if tax.get("orphan_pronto_non_medicine"):
        errors.append(
            f"orphan pronto cats not in tree: {tax['orphan_pronto_non_medicine']}"
        )
    for old, hit in (tax.get("legacy_name_to_new") or {}).items():
        if hit.get("action") == "remap" and hit.get("new_cod_inst") is None:
            errors.append(f"legacy map {old} remap without new_cod_inst")
    return (len(errors) == 0, errors)
