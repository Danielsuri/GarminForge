#!/usr/bin/env python3
"""
Download animated GIFs from a local ExerciseDB API for all exercises in _POOL.

Usage:
    python scripts/fetch_exercise_gifs.py                          # default http://localhost:3000
    python scripts/fetch_exercise_gifs.py --api-url http://host:3000
    python scripts/fetch_exercise_gifs.py --dry-run                # preview without downloading

Output: web/static/gifs/<GARMIN_KEY>.gif  (e.g. BARBELL_BENCH_PRESS.gif)
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.parse
import urllib.request

_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
_GIF_DIR = _PROJECT_ROOT / "web" / "static" / "gifs"

sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

from web.workout_generator import _POOL  # noqa: E402
from exercisedb_map import garmin_to_exercisedb_name  # noqa: E402


def _fetch_gif_url(api_url: str, exercise_name: str) -> str | None:
    """Query ExerciseDB; return the gifUrl of the first result or None."""
    encoded = urllib.parse.quote(exercise_name)
    url = f"{api_url.rstrip('/')}/api/v1/exercises?name={encoded}&limit=1"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        print(f"  [ERROR] HTTP request failed for '{exercise_name}': {exc}")
        return None
    if not data:
        return None
    return data[0].get("gifUrl")


def _download_gif(gif_url: str, dest: pathlib.Path) -> bool:
    """Download gif_url to dest. Returns True on success."""
    try:
        with urllib.request.urlopen(gif_url, timeout=30) as resp:
            dest.write_bytes(resp.read())
        return True
    except Exception as exc:
        print(f"  [ERROR] Download failed from '{gif_url}': {exc}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Download ExerciseDB GIFs")
    parser.add_argument(
        "--api-url", default="http://localhost:3000", help="Base URL of local ExerciseDB API"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be downloaded without writing files",
    )
    args = parser.parse_args()

    _GIF_DIR.mkdir(parents=True, exist_ok=True)

    unique_keys = sorted({tmpl.name for tmpl in _POOL})
    counts = {
        "downloaded": 0,
        "dry_run": 0,
        "skipped_exists": 0,
        "not_found": 0,
        "overridden_skip": 0,
        "error": 0,
    }

    for key in unique_keys:
        dest = _GIF_DIR / f"{key}.gif"

        if dest.exists():
            print(f"  [SKIP]   {key} — already exists")
            counts["skipped_exists"] += 1
            continue

        search_name = garmin_to_exercisedb_name(key)
        if search_name is None:
            print(f"  [SKIP]   {key} — no ExerciseDB match (None override)")
            counts["overridden_skip"] += 1
            continue

        print(f"  [QUERY]  {key} → '{search_name}' ...", end=" ", flush=True)

        if args.dry_run:
            print("(dry-run)")
            counts["dry_run"] += 1
            continue

        gif_url = _fetch_gif_url(args.api_url, search_name)
        if gif_url is None:
            print("NOT FOUND")
            counts["not_found"] += 1
            continue

        ok = _download_gif(gif_url, dest)
        if ok:
            print(f"OK → {dest.name}")
            counts["downloaded"] += 1
        else:
            counts["error"] += 1

    print("\n--- Summary ---")
    for label, key in [
        ("Downloaded", "downloaded"),
        ("Would download (dry-run)", "dry_run"),
        ("Skipped (exists)", "skipped_exists"),
        ("Not found", "not_found"),
        ("Skipped (override)", "overridden_skip"),
        ("Errors", "error"),
    ]:
        print(f"  {label:22}: {counts[key]}")


if __name__ == "__main__":
    main()
