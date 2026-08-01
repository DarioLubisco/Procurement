"""MDM taxonomy → Softland SAINSTA (non-medicine, 3-level).

Grill 2026-07-22 decisions:
- Source: taxonomias_v2 / Procurement.Taxonomia (not Farma Pronto)
- Tree: Dominio → Categoría → Subcategoría (exact Descrip strings)
- Preserve Softland Medicinas untouched
- LEGACY_NO_MEDICINA (2999) holds old non-medicine nodes until phase-2 delete
- CodInst ranges: dominios 3000–3099, categorias 3100–3199, subcategorias 3200–3999
- SAPROD remap only when MDM columns exist (prefer subcategoria)

Source of truth JSON: ``backend/data/sainsta_mdm_taxonomy.json``.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "sainsta_mdm_taxonomy.json"

INSERTABLE_ROLES = frozenset({"legacy_root", "dominio", "categoria", "subcategoria"})


@lru_cache(maxsize=1)
def load_taxonomy(path: Optional[str] = None) -> Dict[str, Any]:
    p = Path(path) if path else _DATA_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "nodes" not in data:
        raise ValueError(f"Invalid taxonomy file: {p}")
    return data


def clear_taxonomy_cache() -> None:
    load_taxonomy.cache_clear()


def insertable_nodes(taxonomy: Optional[Mapping[str, Any]] = None) -> List[Dict[str, Any]]:
    tax = taxonomy or load_taxonomy()
    return [n for n in tax["nodes"] if n.get("role") in INSERTABLE_ROLES]


def resolve_mdm_cod_inst(
    dominio: Optional[str],
    categoria: Optional[str],
    subcategoria: Optional[str],
    *,
    taxonomy: Optional[Mapping[str, Any]] = None,
) -> Optional[int]:
    """Prefer subcategoria CodInst; else categoria. Exact string match."""
    tax = taxonomy or load_taxonomy()
    dom = (dominio or "").strip()
    cat = (categoria or "").strip()
    sub = (subcategoria or "").strip()
    if not dom:
        return None
    best_cat: Optional[int] = None
    for row in tax.get("mdm_path_to_cod_inst") or []:
        if row.get("dominio") != dom:
            continue
        if cat and row.get("categoria") == cat and row.get("subcategoria") is None:
            best_cat = int(row["cod_inst"])
        if cat and sub and row.get("categoria") == cat and row.get("subcategoria") == sub:
            return int(row["cod_inst"])
    return best_cat


def collect_medicinas_codinsts(
    rows: Sequence[Mapping[str, Any]],
    *,
    root_descrip: str = "Medicinas",
) -> Set[int]:
    children: Dict[int, List[int]] = {}
    root_ids: List[int] = []
    for row in rows:
        cod = int(row["CodInst"])
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
) -> Dict[str, Any]:
    """Dry-run plan against current SAINSTA rows."""
    tax = taxonomy or load_taxonomy()
    legacy_id = int(tax["legacy_root"]["cod_inst"])
    preserve = collect_medicinas_codinsts(
        existing_rows, root_descrip=str(tax["preserve"]["root_descrip"])
    )
    existing_ids = {int(r["CodInst"]) for r in existing_rows}
    mdm_range = set()
    for n in insertable_nodes(tax):
        mdm_range.add(int(n["cod_inst"]))

    reparent_legacy: List[Dict[str, Any]] = []
    for row in existing_rows:
        cod = int(row["CodInst"])
        if cod in preserve:
            continue
        if cod == legacy_id:
            continue
        if cod in mdm_range:
            continue
        # Keep Anulados tree as-is (already trash bin)
        if str(row.get("Descrip") or "").strip() in {"Anulados o Eliminadas"}:
            continue
        if int(row.get("InsPadre") or 0) == 27:
            continue
        if int(row.get("InsPadre") or 0) == legacy_id:
            continue
        reparent_legacy.append(
            {
                "CodInst": cod,
                "Descrip": row.get("Descrip"),
                "InsPadre_old": row.get("InsPadre"),
                "InsPadre_new": legacy_id,
            }
        )

    inserts = []
    for node in insertable_nodes(tax):
        cod = int(node["cod_inst"])
        inserts.append(
            {
                "CodInst": cod,
                "Descrip": node["descrip"],
                "InsPadre": int(node["ins_padre"]),
                "role": node["role"],
                "exists": cod in existing_ids,
            }
        )

    return {
        "preserve_codinsts": sorted(preserve),
        "reparent_to_legacy": reparent_legacy,
        "inserts": inserts,
        "legacy_root_id": legacy_id,
        "stats": {
            "existing": len(existing_rows),
            "preserve": len(preserve),
            "reparent_legacy": len(reparent_legacy),
            "inserts": len(inserts),
        },
    }


def render_migration_sql(
    plan: Optional[Mapping[str, Any]] = None,
    *,
    taxonomy: Optional[Mapping[str, Any]] = None,
) -> str:
    """Portable T-SQL: upsert MDM tree, reparent legacy under LEGACY_NO_MEDICINA.

    Does NOT delete legacy (phase 2). Does NOT remap SAPROD unless MDM columns exist
    (guarded dynamic SQL).
    """
    tax = taxonomy or load_taxonomy()
    legacy_id = int(tax["legacy_root"]["cod_inst"])
    legacy_name = str(tax["legacy_root"]["descrip"]).replace("'", "''")
    lines: List[str] = [
        "-- ============================================================",
        "-- 013_sainsta_mdm_non_medicine.sql",
        "-- SAINSTA 3-level MDM taxonomy (non-medicine).",
        "-- Preserves Medicinas. Legacy non-medicine → LEGACY_NO_MEDICINA.",
        "-- Phase-2 delete of legacy is a separate task.",
        "-- REVIEW + BACKUP before production.",
        "-- ============================================================",
        "SET XACT_ABORT ON;",
        "BEGIN TRANSACTION;",
        "",
        "-- 0) Snapshot",
        "IF OBJECT_ID(N'Procurement.SAINSTA_Backup_MDM', N'U') IS NULL",
        "BEGIN",
        "    SELECT * INTO Procurement.SAINSTA_Backup_MDM FROM dbo.SAINSTA;",
        "END",
        "IF OBJECT_ID(N'Procurement.SAPROD_CodInst_Backup_MDM', N'U') IS NULL",
        "BEGIN",
        "    SELECT CodProd, CodInst INTO Procurement.SAPROD_CodInst_Backup_MDM FROM dbo.SAPROD;",
        "END",
        "",
        f"-- 1) LEGACY_NO_MEDICINA root ({legacy_id})",
        # CodInst is IDENTITY on live SAINSTA — required for explicit CodInst values.
        "SET IDENTITY_INSERT dbo.SAINSTA ON;",
        f"IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = {legacy_id})",
        "    UPDATE dbo.SAINSTA SET "
        f"Descrip = N'{legacy_name}', InsPadre = 0 WHERE CodInst = {legacy_id};",
        "ELSE",
        "    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) "
        f"VALUES ({legacy_id}, N'{legacy_name}', 0);",
        "",
        "-- 2) Upsert MDM Dominio / Categoria / Subcategoria",
    ]

    for node in insertable_nodes(tax):
        if node.get("role") == "legacy_root":
            continue
        cod = int(node["cod_inst"])
        descrip = str(node["descrip"]).replace("'", "''")
        padre = int(node["ins_padre"])
        lines.append(
            f"IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = {cod})\n"
            f"    UPDATE dbo.SAINSTA SET Descrip = N'{descrip}', InsPadre = {padre} "
            f"WHERE CodInst = {cod};\n"
            f"ELSE\n"
            f"    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) "
            f"VALUES ({cod}, N'{descrip}', {padre});"
        )

    lines.extend(
        [
            "SET IDENTITY_INSERT dbo.SAINSTA OFF;",
            "",
            "-- 3) Medicinas subtree (preserve)",
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
            "-- 4) Reparent non-medicine / non-MDM / non-Anulados under LEGACY",
            "UPDATE i",
            f"SET InsPadre = {legacy_id}",
            "FROM dbo.SAINSTA AS i",
            f"WHERE i.CodInst <> {legacy_id}",
            "  AND i.CodInst <> 27",
            "  AND ISNULL(i.InsPadre, 0) <> 27",
            f"  AND ISNULL(i.InsPadre, 0) <> {legacy_id}",
            "  AND i.CodInst NOT BETWEEN 3000 AND 3999",
            "  AND i.CodInst NOT IN (SELECT CodInst FROM #MedicinasPreserve)",
            "  AND i.Descrip <> N'Anulados o Eliminadas';",
            "",
            "-- 5) Optional SAPROD remap when MDM columns exist (prefer subcategoria)",
            "IF COL_LENGTH('Procurement.por_aprobacion_equivalencias', 'dominio') IS NOT NULL",
            " AND COL_LENGTH('Procurement.por_aprobacion_equivalencias', 'categoria') IS NOT NULL",
            " AND COL_LENGTH('Procurement.por_aprobacion_equivalencias', 'subcategoria') IS NOT NULL",
            "BEGIN",
            "    ;WITH MapSub AS (",
            "        SELECT e.codbarras, s.CodInst",
            "        FROM Procurement.por_aprobacion_equivalencias e",
            "        INNER JOIN dbo.SAINSTA s ON s.Descrip = e.subcategoria",
            "        INNER JOIN dbo.SAINSTA c ON c.CodInst = s.InsPadre AND c.Descrip = e.categoria",
            "        INNER JOIN dbo.SAINSTA d ON d.CodInst = c.InsPadre AND d.Descrip = e.dominio",
            "        WHERE e.dominio IS NOT NULL AND e.categoria IS NOT NULL AND e.subcategoria IS NOT NULL",
            "          AND e.dominio <> N'MEDICAMENTO_ALOPATICO'",
            "    )",
            "    UPDATE p SET CodInst = m.CodInst",
            "    FROM dbo.SAPROD p",
            "    INNER JOIN MapSub m ON p.CodProd = m.codbarras",
            "    WHERE p.CodInst NOT IN (SELECT CodInst FROM #MedicinasPreserve);",
            "",
            "    ;WITH MapCat AS (",
            "        SELECT e.codbarras, c.CodInst",
            "        FROM Procurement.por_aprobacion_equivalencias e",
            "        INNER JOIN dbo.SAINSTA c ON c.Descrip = e.categoria",
            "        INNER JOIN dbo.SAINSTA d ON d.CodInst = c.InsPadre AND d.Descrip = e.dominio",
            "        WHERE e.dominio IS NOT NULL AND e.categoria IS NOT NULL",
            "          AND (e.subcategoria IS NULL OR LTRIM(RTRIM(e.subcategoria)) = N'')",
            "          AND e.dominio <> N'MEDICAMENTO_ALOPATICO'",
            "    )",
            "    UPDATE p SET CodInst = m.CodInst",
            "    FROM dbo.SAPROD p",
            "    INNER JOIN MapCat m ON p.CodProd = m.codbarras",
            "    WHERE p.CodInst NOT IN (SELECT CodInst FROM #MedicinasPreserve);",
            "END",
            "",
            "-- 6) Sanity",
            "IF NOT EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE Descrip = N'Medicinas' AND ISNULL(InsPadre, 0) = 0)",
            "BEGIN",
            "    RAISERROR(N'Medicinas root missing after migration', 16, 1);",
            "    ROLLBACK TRANSACTION;",
            "    RETURN;",
            "END",
            f"IF NOT EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = {legacy_id})",
            "BEGIN",
            "    RAISERROR(N'LEGACY_NO_MEDICINA missing after migration', 16, 1);",
            "    ROLLBACK TRANSACTION;",
            "    RETURN;",
            "END",
            "",
            "COMMIT TRANSACTION;",
            "GO",
            "",
            f"-- Taxonomy version: {tax.get('version')}",
            f"-- Insertable nodes: {len(insertable_nodes(tax))}",
        ]
    )
    if plan is not None:
        lines.extend(
            [
                f"-- plan preserve: {plan.get('preserve_codinsts')}",
                f"-- plan reparent: {len(plan.get('reparent_to_legacy') or [])}",
            ]
        )
    return "\n".join(lines) + "\n"


def validate_taxonomy(taxonomy: Optional[Mapping[str, Any]] = None) -> Tuple[bool, List[str]]:
    tax = taxonomy or load_taxonomy()
    errors: List[str] = []
    nodes = tax.get("nodes") or []
    ids = [int(n["cod_inst"]) for n in nodes]
    if len(ids) != len(set(ids)):
        errors.append("duplicate cod_inst")
    by_id = {int(n["cod_inst"]): n for n in nodes}
    for n in nodes:
        role = n.get("role")
        padre = int(n.get("ins_padre") or 0)
        if role == "dominio" and padre != 0:
            errors.append(f"dominio {n.get('descrip')} parent != 0")
        if role == "categoria":
            p = by_id.get(padre)
            if not p or p.get("role") != "dominio":
                errors.append(f"categoria {n.get('descrip')} parent not dominio")
        if role == "subcategoria":
            p = by_id.get(padre)
            if not p or p.get("role") != "categoria":
                errors.append(f"subcategoria {n.get('descrip')} parent not categoria")
        if role in INSERTABLE_ROLES and not str(n.get("descrip") or "").strip():
            errors.append("empty descrip")
    # ranges
    for n in nodes:
        cod = int(n["cod_inst"])
        role = n.get("role")
        if role == "dominio" and not (3000 <= cod <= 3099):
            errors.append(f"dominio id out of range: {cod}")
        if role == "categoria" and not (3100 <= cod <= 3199):
            errors.append(f"categoria id out of range: {cod}")
        if role == "subcategoria" and not (3200 <= cod <= 3999):
            errors.append(f"subcategoria id out of range: {cod}")
        if role == "legacy_root" and cod != 2999:
            errors.append("legacy_root must be 2999")
    if "MEDICAMENTO_ALOPATICO" in (tax.get("domains_included") or []):
        errors.append("MEDICAMENTO_ALOPATICO must not be inserted")
    return (len(errors) == 0, errors)
