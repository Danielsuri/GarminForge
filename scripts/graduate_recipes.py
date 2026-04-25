#!/usr/bin/env python3
"""
Recipe graduation script.

Usage:
    python scripts/graduate_recipes.py [--dry-run]

Reads all RecipeCache rows, matches each by meal_id to an entry in
web/data/meal_pool.json, and writes recipe_en / recipe_he fields onto
matching entries. Entries already having both fields are skipped.

Run from the repo root after enough recipes have been cached to make
baking them into the static pool worthwhile.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from web.db import SessionLocal
from web.models import RecipeCache

POOL_PATH = Path(__file__).parent.parent / "web" / "data" / "meal_pool.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    args = parser.parse_args()

    pool: list[dict[str, Any]] = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    pool_by_id: dict[str, dict[str, Any]] = {m["id"]: m for m in pool}

    db = SessionLocal()
    try:
        rows = db.query(RecipeCache).all()
    finally:
        db.close()

    if not rows:
        print("No RecipeCache rows found. Generate some recipes first.")
        return

    updated = 0
    skipped_no_match = 0
    skipped_already_set = 0

    for row in rows:
        meal = pool_by_id.get(row.meal_id)
        if meal is None:
            skipped_no_match += 1
            continue
        if meal.get("recipe_en") and meal.get("recipe_he"):
            skipped_already_set += 1
            continue
        try:
            recipe_en = json.loads(row.recipe_en)
            recipe_he = json.loads(row.recipe_he)
        except Exception as exc:
            print(f"WARN: Could not parse recipes for {row.meal_id}: {exc}")
            continue

        if not args.dry_run:
            meal["recipe_en"] = recipe_en
            meal["recipe_he"] = recipe_he
        print(f"[{'DRY' if args.dry_run else 'OK'}] {row.meal_id}")
        updated += 1

    print(
        f"\nDone. Updated: {updated}, "
        f"Skipped (already set): {skipped_already_set}, "
        f"Skipped (not in pool): {skipped_no_match}"
    )

    if updated and not args.dry_run:
        tmp = POOL_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(pool, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, POOL_PATH)
        print(f"Pool written to {POOL_PATH}")


if __name__ == "__main__":
    main()
