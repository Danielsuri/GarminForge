"""
Maps GarminForge exercise keys to ExerciseDB search names.

Auto-conversion: key.lower().replace('_', ' ')
  e.g.  BARBELL_BENCH_PRESS  →  "barbell bench press"

MANUAL_OVERRIDES:
  str  → use this name in the API query instead of auto-conversion
  None → exercise not in ExerciseDB; skip download for this key

Note: The ``key`` parameter is the exercise ``name`` field (not category-qualified).
For name keys that appear in multiple Garmin categories, the same mapping applies
to all of them — this is by design for the download use case.
"""

from __future__ import annotations

MANUAL_OVERRIDES: dict[str, str | None] = {
    # ExerciseDB omits "back" from the squat name
    "BARBELL_BACK_SQUAT": "barbell squat",
    # ExerciseDB drops the equipment prefix
    "DUMBBELL_LATERAL_RAISE": "lateral raise",
    # Fuzzy search returns cable exercises first; pin to the correct name
    "GOBLET_SQUAT": "dumbbell goblet squat",
    # Single-word category keys used by sled/sandbag/suspension variants — too ambiguous
    "PUSH": None,
    "ROW": None,
    "LUNGE": None,
    "SQUAT": None,
    "CURL": None,
    "BACK_SQUAT": None,
    # Sled / sandbag movements — use barbell equivalent where available
    "CLEAN_AND_PRESS": "barbell clean and press",
    # No ExerciseDB equivalent for these
    "FORWARD_DRAG": None,
    "BACKWARD_DRAG": None,
    "SHOULDERING": None,
    "OVERHEAD_CARRY": None,
    # Specialty movements with low or absent coverage
    "ROPE_CLIMB": "rope climbing",
    "KNEELING_AB_WHEEL": "ab wheel rollout",
    "BARBELL_ROLLOUT": None,
    "ALTERNATING_WAVE": "battle ropes",
    "ALTERNATING_SQUAT_WAVE": "battle ropes",
    "ALTERNATING_LUNGE_WAVE": "battle ropes",
    "SWISS_BALL_HIP_RAISE_AND_LEG_CURL": None,
    "SWISS_BALL_PIKE": None,
}


def garmin_to_exercisedb_name(key: str) -> str | None:
    """Return the ExerciseDB search name for a Garmin exercise key.

    Returns str  — pass as ``?name=`` to the ExerciseDB API.
    Returns None — skip this exercise (not available in ExerciseDB).
    Never raises for valid string keys.
    """
    if key in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[key]
    return key.lower().replace("_", " ")
