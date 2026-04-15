#!/usr/bin/env python3
"""
Download animated GIFs from the ExerciseDB OSS API for all exercises in _POOL.

Usage:
    python scripts/fetch_exercise_gifs.py                          # uses oss.exercisedb.dev
    python scripts/fetch_exercise_gifs.py --api-url https://...    # override API base URL
    python scripts/fetch_exercise_gifs.py --dry-run                # preview without downloading

Output: web/static/gifs/<GARMIN_KEY>.gif  (e.g. BARBELL_BENCH_PRESS.gif)
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request

_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
_GIF_DIR = _PROJECT_ROOT / "web" / "static" / "gifs"

sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

from web.workout_generator import _POOL  # noqa: E402
from exercisedb_map import garmin_to_exercisedb_name  # noqa: E402


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, image/gif, */*",
}


def _fetch_gif_url(api_url: str, exercise_name: str) -> str | None:
    """Query ExerciseDB; return the gifUrl of the first result or None.

    Handles both response shapes:
      - oss.exercisedb.dev: {"success": true, "data": [...]}
      - legacy local API:   [...]
    Retries once after a 60 s back-off on HTTP 429.
    """
    encoded = urllib.parse.quote(exercise_name)
    url = f"{api_url.rstrip('/')}/api/v1/exercises?name={encoded}&limit=1"
    for attempt in range(2):
        req = urllib.request.Request(url, headers=_HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                payload = json.loads(resp.read().decode())
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt == 0:
                print("\n  [RATE]   429 -- waiting 60 s ...", flush=True)
                time.sleep(60)
                continue
            print(f"  [ERROR] HTTP request failed for '{exercise_name}': {exc}")
            return None
        except Exception as exc:
            print(f"  [ERROR] HTTP request failed for '{exercise_name}': {exc}")
            return None
    else:
        return None
    # Unwrap envelope if present
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    if not data:
        return None
    return data[0].get("gifUrl")


def _download_gif(gif_url: str, dest: pathlib.Path) -> bool:
    """Download gif_url to dest. Returns True on success."""
    req = urllib.request.Request(gif_url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            dest.write_bytes(resp.read())
        return True
    except Exception as exc:
        print(f"  [ERROR] Download failed from '{gif_url}': {exc}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Download ExerciseDB GIFs")
    parser.add_argument(
        "--api-url",
        default="https://oss.exercisedb.dev",
        help="ExerciseDB API base URL (default: https://oss.exercisedb.dev)",
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
            print(f"  [SKIP]   {key} -- already exists")
            counts["skipped_exists"] += 1
            continue

        search_name = garmin_to_exercisedb_name(key)
        if search_name is None:
            print(f"  [SKIP]   {key} -- no ExerciseDB match (None override)")
            counts["overridden_skip"] += 1
            continue

        print(f"  [QUERY]  {key} -> '{search_name}' ...", end=" ", flush=True)

        if args.dry_run:
            print("(dry-run)")
            counts["dry_run"] += 1
            continue

        gif_url = _fetch_gif_url(args.api_url, search_name)
        time.sleep(3)
        if gif_url is None:
            print("NOT FOUND")
            counts["not_found"] += 1
            continue

        ok = _download_gif(gif_url, dest)
        if ok:
            print(f"OK -> {dest.name}")
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
