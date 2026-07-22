#!/usr/bin/env python3
"""Generate / dry-run / apply SAINSTA Farma Pronto rewrite.

Examples:
  # Validate taxonomy + emit SQL from a JSON dump of current SAINSTA
  python scripts/migrate_sainsta_pronto.py validate
  python scripts/migrate_sainsta_pronto.py plan --sainsta-json /tmp/sainsta.json
  python scripts/migrate_sainsta_pronto.py render-sql --sainsta-json /tmp/sainsta.json -o sql/013_sainsta_pronto_non_medicine.sql

  # Live DB (requires .env with DB_*). Default is dry-run.
  python scripts/migrate_sainsta_pronto.py apply --dry-run
  python scripts/migrate_sainsta_pronto.py apply --execute
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services.sainsta_pronto_taxonomy import (  # noqa: E402
    load_taxonomy,
    plan_sainsta_rewrite,
    render_migration_sql,
    validate_taxonomy,
)


def _load_sainsta_json(path: Path) -> List[Dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "categories" in raw:
        # API shape {id,name,parentId}
        rows = []
        for c in raw["categories"]:
            rows.append(
                {
                    "CodInst": int(c["id"]),
                    "Descrip": c["name"],
                    "InsPadre": int(c.get("parentId") or 0),
                }
            )
        return rows
    if isinstance(raw, list):
        rows = []
        for c in raw:
            if "CodInst" in c:
                rows.append(
                    {
                        "CodInst": int(c["CodInst"]),
                        "Descrip": c.get("Descrip"),
                        "InsPadre": int(c.get("InsPadre") or 0),
                    }
                )
            else:
                rows.append(
                    {
                        "CodInst": int(c["id"]),
                        "Descrip": c["name"],
                        "InsPadre": int(c.get("parentId") or 0),
                    }
                )
        return rows
    raise SystemExit(f"Unrecognized SAINSTA JSON shape in {path}")


def _fetch_sainsta_live() -> List[Dict[str, Any]]:
    from backend.database import get_connection

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT CodInst, Descrip, InsPadre FROM dbo.SAINSTA ORDER BY CodInst")
        rows = []
        for r in cur.fetchall():
            rows.append(
                {
                    "CodInst": int(r[0]),
                    "Descrip": r[1],
                    "InsPadre": int(r[2] or 0),
                }
            )
        return rows
    finally:
        conn.close()


def cmd_validate(_: argparse.Namespace) -> int:
    ok, errors = validate_taxonomy()
    tax = load_taxonomy()
    print(f"taxonomy version={tax.get('version')} nodes={len(tax.get('nodes') or [])}")
    if ok:
        print("OK")
        return 0
    for e in errors:
        print(f"ERROR: {e}")
    return 1


def cmd_plan(args: argparse.Namespace) -> int:
    rows = _load_sainsta_json(Path(args.sainsta_json)) if args.sainsta_json else _fetch_sainsta_live()
    plan = plan_sainsta_rewrite(rows)
    out = {
        "stats": plan["stats"],
        "preserve_codinsts": plan["preserve_codinsts"],
        "unmapped_legacy": plan["unmapped_legacy"],
        "sample_retire": plan["retire_to_anulados"][:10],
        "sample_inserts": plan["inserts"][:10],
        "remap_count": len(plan["product_remap_by_old_cod"]),
    }
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


def cmd_render_sql(args: argparse.Namespace) -> int:
    plan = None
    if args.sainsta_json:
        rows = _load_sainsta_json(Path(args.sainsta_json))
        plan = plan_sainsta_rewrite(rows)
    sql = render_migration_sql(plan, portable=True)
    out = Path(args.out or (ROOT / "sql" / "013_sainsta_pronto_non_medicine.sql"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(sql, encoding="utf-8")
    extra = f" plan_stats={plan['stats']}" if plan else ""
    print(f"wrote {out} ({len(sql)} bytes){extra}")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    rows = _fetch_sainsta_live()
    plan = plan_sainsta_rewrite(rows)
    sql = render_migration_sql(plan)
    print(json.dumps(plan["stats"], indent=2))
    if args.dry_run or not args.execute:
        print("DRY-RUN — not executing. Pass --execute to apply.")
        preview = ROOT / "sql" / "013_sainsta_pronto_non_medicine.preview.sql"
        preview.write_text(sql, encoding="utf-8")
        print(f"preview SQL: {preview}")
        return 0

    from backend.database import get_connection

    conn = get_connection()
    try:
        cur = conn.cursor()
        # pyodbc: run batches split on GO
        for batch in sql.split("\nGO\n"):
            batch = batch.strip()
            if not batch or batch.upper().startswith("GO"):
                continue
            cur.execute(batch)
        conn.commit()
        print("APPLY OK")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate")
    v.set_defaults(func=cmd_validate)

    pl = sub.add_parser("plan")
    pl.add_argument("--sainsta-json", help="Offline dump (API or CodInst rows)")
    pl.add_argument("-o", "--out")
    pl.set_defaults(func=cmd_plan)

    rs = sub.add_parser("render-sql")
    rs.add_argument("--sainsta-json")
    rs.add_argument("-o", "--out")
    rs.set_defaults(func=cmd_render_sql)

    ap = sub.add_parser("apply")
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--execute", action="store_true", help="Actually run against DB")
    ap.set_defaults(func=cmd_apply)

    args = p.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
