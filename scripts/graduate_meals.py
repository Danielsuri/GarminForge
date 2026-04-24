#!/usr/bin/env python3
"""
Meal suggestion graduation script.

Usage:
    python scripts/graduate_meals.py

For each pending MealSuggestion (oldest first):
  - Print the full meal JSON
  - Prompt: [a]pprove / [r]eject / [s]kip
  - Approve: assign next sequential ID, append to meal_pool.json, mark approved in DB
  - Reject: mark rejected in DB
  - Skip: leave as pending for next run

Run from the repo root. Requires the app DB to be accessible.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Allow running from repo root without installing
sys.path.insert(0, str(Path(__file__).parent.parent))

from web.db import SessionLocal
from web.models import MealSuggestion

POOL_PATH = Path(__file__).parent.parent / "web" / "data" / "meal_pool.json"


def _next_id(pool: list[dict[str, Any]], meal_type: str) -> str:
    """Return the next sequential ID for the given meal type."""
    prefix = meal_type + "_"
    existing = [m["id"] for m in pool if m.get("id", "").startswith(prefix)]
    if not existing:
        return f"{prefix}001"
    nums: list[int] = []
    for eid in existing:
        try:
            nums.append(int(eid.split("_")[-1]))
        except ValueError:
            pass
    next_num = max(nums) + 1 if nums else 1
    return f"{prefix}{next_num:03d}"


def main() -> None:
    db = SessionLocal()
    try:
        pending = (
            db.query(MealSuggestion)
            .filter_by(status="pending")
            .order_by(MealSuggestion.created_at)
            .all()
        )
        if not pending:
            print("No pending suggestions.")
            return

        pool: list[dict[str, Any]] = json.loads(POOL_PATH.read_text(encoding="utf-8"))
        approved_count = 0
        rejected_count = 0
        skipped_count = 0

        for suggestion in pending:
            print("\n" + "=" * 60)
            print(f"Suggestion ID: {suggestion.id}")
            print(f"User:          {suggestion.user_id}")
            print(f"Created:       {suggestion.created_at}")
            try:
                meal: dict[str, Any] = json.loads(suggestion.meal_json)
            except Exception as exc:
                print(f"ERROR: Could not parse meal_json: {exc}")
                print("Skipping.")
                skipped_count += 1
                continue

            print("\nMeal JSON:")
            print(json.dumps(meal, ensure_ascii=False, indent=2))
            print()

            while True:
                choice = input("[a]pprove / [r]eject / [s]kip: ").strip().lower()
                if choice in ("a", "r", "s"):
                    break
                print("Please enter a, r, or s.")

            if choice == "a":
                meal_type = meal.get("type", "dinner")
                new_id = _next_id(pool, meal_type)
                meal["id"] = new_id
                pool.append(meal)
                POOL_PATH.write_text(
                    json.dumps(pool, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                suggestion.status = "approved"
                db.commit()
                print(f"✅ Approved as {new_id}, appended to meal_pool.json")
                approved_count += 1

            elif choice == "r":
                suggestion.status = "rejected"
                db.commit()
                print("❌ Rejected.")
                rejected_count += 1

            else:
                print("⏭ Skipped.")
                skipped_count += 1

        print("\n" + "=" * 60)
        print(
            f"Done. Approved: {approved_count}, Rejected: {rejected_count},"
            f" Skipped: {skipped_count}"
        )
        if approved_count:
            print(f"Pool now has {len(pool)} meals. Restart the server to pick up new meals.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
