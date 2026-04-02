"""
Exercise catalog for strength/fitness workouts.

Garmin's full catalog contains 1,600+ exercises defined in the FIT SDK's
``Profile.xlsx``.  No public API endpoint exists to retrieve them at runtime.
This module provides:

1. A curated ``EXERCISES`` mapping of the most common strength movements —
   enough to build full programmes.
2. ``resolve()`` — fuzzy name matching so callers can use natural language
   (e.g. ``"barbell bench press"``) instead of raw ALL_CAPS enums.
3. ``validate()`` — checks that a category/name pair is known before
   uploading, avoiding Garmin's opaque 400 errors.

Extending the catalog
---------------------
Add entries to ``EXERCISES`` as:
    "<CATEGORY>": {"<NAME>": "<human label>", ...}

The authoritative source for new entries is ``Profile.xlsx`` from the Garmin
FIT SDK (developer.garmin.com/fit) and the community list at
github.com/mrnabilnoh/workout-plan-garmin-connect.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class Exercise:
    """An exercise as stored in the Garmin workout schema."""
    category: str   # e.g. "BENCH_PRESS"
    name: str       # e.g. "BARBELL_BENCH_PRESS"
    label: str      # human-readable, e.g. "Barbell Bench Press"


# ---------------------------------------------------------------------------
# Master catalog
# ---------------------------------------------------------------------------
# Structure: { CATEGORY: { NAME: "Human Label" } }

EXERCISES: dict[str, dict[str, str]] = {
    # -----------------------------------------------------------------------
    # CHEST
    # -----------------------------------------------------------------------
    "BENCH_PRESS": {
        "BARBELL_BENCH_PRESS":                   "Barbell Bench Press",
        "DUMBBELL_BENCH_PRESS":                  "Dumbbell Bench Press",
        "INCLINE_BARBELL_BENCH_PRESS":           "Incline Barbell Bench Press",
        "INCLINE_DUMBBELL_BENCH_PRESS":          "Incline Dumbbell Bench Press",
        "DECLINE_BARBELL_BENCH_PRESS":           "Decline Barbell Bench Press",
        "DECLINE_DUMBBELL_BENCH_PRESS":          "Decline Dumbbell Bench Press",
        "CLOSE_GRIP_BARBELL_BENCH_PRESS":        "Close-Grip Barbell Bench Press",
        "BOARD_PRESS":                           "Board Press",
    },
    "FLYE": {
        "DUMBBELL_FLYE":                         "Dumbbell Flye",
        "INCLINE_DUMBBELL_FLYE":                 "Incline Dumbbell Flye",
        "CABLE_CROSSOVER":                       "Cable Crossover",
        "CHEST_FLY_MACHINE":                     "Chest Fly Machine",
        "PEC_DECK":                              "Pec Deck",
    },
    "PUSH_UP": {
        "PUSH_UP":                               "Push-Up",
        "WIDE_GRIP_PUSH_UP":                     "Wide-Grip Push-Up",
        "CLOSE_GRIP_PUSH_UP":                    "Close-Grip Push-Up",
        "DECLINE_PUSH_UP":                       "Decline Push-Up",
        "INCLINE_PUSH_UP":                       "Incline Push-Up",
        "DIAMOND_PUSH_UP":                       "Diamond Push-Up",
        "PLYOMETRIC_PUSH_UP":                    "Plyometric Push-Up",
    },

    # -----------------------------------------------------------------------
    # BACK
    # -----------------------------------------------------------------------
    "DEADLIFT": {
        "BARBELL_DEADLIFT":                      "Barbell Deadlift",
        "ROMANIAN_DEADLIFT":                     "Romanian Deadlift",
        "DUMBBELL_ROMANIAN_DEADLIFT":            "Dumbbell Romanian Deadlift",
        "SUMO_DEADLIFT":                         "Sumo Deadlift",
        "TRAP_BAR_DEADLIFT":                     "Trap Bar Deadlift",
        "SINGLE_LEG_DEADLIFT_WITH_BARBELL":      "Single-Leg Deadlift (Barbell)",
        "STIFF_LEG_DEADLIFT":                    "Stiff-Leg Deadlift",
    },
    "ROW": {
        "BARBELL_ROW":                           "Barbell Row",
        "DUMBBELL_ROW":                          "Dumbbell Row",
        "CABLE_ROW":                             "Cable Row",
        "T_BAR_ROW":                             "T-Bar Row",
        "SEATED_CABLE_ROW":                      "Seated Cable Row",
        "MACHINE_ROW":                           "Machine Row",
        "PENDLAY_ROW":                           "Pendlay Row",
        "INVERTED_ROW":                          "Inverted Row",
        "CHEST_SUPPORTED_DUMBBELL_ROW":          "Chest-Supported Dumbbell Row",
        "FACE_PULL":                             "Face Pull",
    },
    "PULL_UP": {
        "PULL_UP":                               "Pull-Up",
        "CHIN_UP":                               "Chin-Up",
        "WIDE_GRIP_PULL_UP":                     "Wide-Grip Pull-Up",
        "NEUTRAL_GRIP_PULL_UP":                  "Neutral-Grip Pull-Up",
        "ASSISTED_PULL_UP":                      "Assisted Pull-Up",
        "BANDED_PULL_UP":                        "Banded Pull-Up",
        "WEIGHTED_PULL_UP":                      "Weighted Pull-Up",
        "LAT_PULLDOWN":                          "Lat Pulldown",
        "CLOSE_GRIP_LAT_PULLDOWN":               "Close-Grip Lat Pulldown",
    },
    "SHRUG": {
        "BARBELL_SHRUG":                         "Barbell Shrug",
        "DUMBBELL_SHRUG":                        "Dumbbell Shrug",
        "CABLE_SHRUG":                           "Cable Shrug",
    },
    "HYPEREXTENSION": {
        "BACK_EXTENSION":                        "Back Extension",
        "BARBELL_DEADLIFT_TO_ROW":               "Deadlift to Row",
        "REVERSE_HYPEREXTENSION":                "Reverse Hyperextension",
        "SUPERMAN":                              "Superman",
    },

    # -----------------------------------------------------------------------
    # SHOULDERS
    # -----------------------------------------------------------------------
    "SHOULDER_PRESS": {
        "BARBELL_SHOULDER_PRESS":                "Barbell Shoulder Press",
        "DUMBBELL_SHOULDER_PRESS":               "Dumbbell Shoulder Press",
        "SEATED_BARBELL_SHOULDER_PRESS":         "Seated Barbell Shoulder Press",
        "SEATED_DUMBBELL_SHOULDER_PRESS":        "Seated Dumbbell Shoulder Press",
        "ARNOLD_PRESS":                          "Arnold Press",
        "MACHINE_SHOULDER_PRESS":                "Machine Shoulder Press",
        "PUSH_PRESS":                            "Push Press",
    },
    "LATERAL_RAISE": {
        "DUMBBELL_LATERAL_RAISE":                "Dumbbell Lateral Raise",
        "CABLE_LATERAL_RAISE":                   "Cable Lateral Raise",
        "MACHINE_LATERAL_RAISE":                 "Machine Lateral Raise",
    },

    # -----------------------------------------------------------------------
    # ARMS — BICEPS
    # -----------------------------------------------------------------------
    "CURL": {
        "BARBELL_CURL":                          "Barbell Curl",
        "DUMBBELL_CURL":                         "Dumbbell Curl",
        "HAMMER_CURL":                           "Hammer Curl",
        "INCLINE_DUMBBELL_CURL":                 "Incline Dumbbell Curl",
        "CABLE_CURL":                            "Cable Curl",
        "PREACHER_CURL":                         "Preacher Curl",
        "CONCENTRATION_CURL":                    "Concentration Curl",
        "EZ_BAR_CURL":                           "EZ-Bar Curl",
    },

    # -----------------------------------------------------------------------
    # ARMS — TRICEPS
    # -----------------------------------------------------------------------
    "TRICEPS_EXTENSION": {
        "TRICEPS_PUSHDOWN":                      "Triceps Pushdown",
        "SKULL_CRUSHER":                         "Skull Crusher",
        "OVERHEAD_DUMBBELL_TRICEPS_EXTENSION":   "Overhead Dumbbell Triceps Extension",
        "CABLE_OVERHEAD_TRICEPS_EXTENSION":      "Cable Overhead Triceps Extension",
        "CLOSE_GRIP_BENCH_PRESS":                "Close-Grip Bench Press",
        "TRICEPS_DIP":                           "Triceps Dip",
    },

    # -----------------------------------------------------------------------
    # LEGS — QUADS
    # -----------------------------------------------------------------------
    "SQUAT": {
        "BARBELL_BACK_SQUAT":                    "Barbell Back Squat",
        "BARBELL_FRONT_SQUAT":                   "Barbell Front Squat",
        "GOBLET_SQUAT":                          "Goblet Squat",
        "DUMBBELL_SQUAT":                        "Dumbbell Squat",
        "HACK_SQUAT":                            "Hack Squat",
        "LEG_PRESS":                             "Leg Press",
        "SPLIT_SQUAT":                           "Split Squat",
        "BULGARIAN_SPLIT_SQUAT":                 "Bulgarian Split Squat",
        "BOX_SQUAT":                             "Box Squat",
        "PAUSE_SQUAT":                           "Pause Squat",
        "ZERCHER_SQUAT":                         "Zercher Squat",
    },
    "LUNGE": {
        "BARBELL_LUNGE":                         "Barbell Lunge",
        "DUMBBELL_LUNGE":                        "Dumbbell Lunge",
        "WALKING_LUNGE":                         "Walking Lunge",
        "REVERSE_LUNGE":                         "Reverse Lunge",
        "LATERAL_LUNGE":                         "Lateral Lunge",
        "STEP_UP":                               "Step-Up",
    },

    # -----------------------------------------------------------------------
    # LEGS — HAMSTRINGS / GLUTES
    # -----------------------------------------------------------------------
    "HIP_RAISE": {
        "BARBELL_HIP_THRUST":                    "Barbell Hip Thrust",
        "DUMBBELL_HIP_THRUST":                   "Dumbbell Hip Thrust",
        "GLUTE_BRIDGE":                          "Glute Bridge",
        "SINGLE_LEG_GLUTE_BRIDGE":               "Single-Leg Glute Bridge",
    },
    "LEG_CURL": {
        "LYING_LEG_CURL":                        "Lying Leg Curl",
        "SEATED_LEG_CURL":                       "Seated Leg Curl",
        "NORDIC_HAMSTRING_CURL":                 "Nordic Hamstring Curl",
        "GOOD_MORNING":                          "Good Morning",
    },

    # -----------------------------------------------------------------------
    # LEGS — CALVES
    # -----------------------------------------------------------------------
    "CALF_RAISE": {
        "BARBELL_CALF_RAISE":                    "Barbell Calf Raise",
        "DUMBBELL_CALF_RAISE":                   "Dumbbell Calf Raise",
        "STANDING_CALF_RAISE":                   "Standing Calf Raise",
        "SEATED_CALF_RAISE":                     "Seated Calf Raise",
        "SINGLE_LEG_CALF_RAISE":                 "Single-Leg Calf Raise",
    },

    # -----------------------------------------------------------------------
    # CORE
    # -----------------------------------------------------------------------
    "PLANK": {
        "PLANK":                                 "Plank",
        "SIDE_PLANK":                            "Side Plank",
        "FOREARM_PLANK":                         "Forearm Plank",
        "PUSH_UP_POSITION_PLANK":                "Push-Up Position Plank",
    },
    "CRUNCH": {
        "CRUNCH":                                "Crunch",
        "BICYCLE_CRUNCH":                        "Bicycle Crunch",
        "REVERSE_CRUNCH":                        "Reverse Crunch",
        "DECLINE_CRUNCH":                        "Decline Crunch",
        "CABLE_CRUNCH":                          "Cable Crunch",
    },
    "LEG_RAISE": {
        "LYING_LEG_RAISE":                       "Lying Leg Raise",
        "HANGING_LEG_RAISE":                     "Hanging Leg Raise",
        "KNEE_RAISE":                            "Knee Raise",
        "CAPTAIN_CHAIR_LEG_RAISE":               "Captain's Chair Leg Raise",
    },
    "CORE": {
        "DEAD_BUG":                              "Dead Bug",
        "PALLOF_PRESS":                          "Pallof Press",
        "AB_WHEEL_ROLLOUT":                      "Ab Wheel Rollout",
        "RUSSIAN_TWIST":                         "Russian Twist",
        "WINDMILL":                              "Windmill",
        "TURKISH_GET_UP":                        "Turkish Get-Up",
    },

    # -----------------------------------------------------------------------
    # OLYMPIC / EXPLOSIVE
    # -----------------------------------------------------------------------
    "OLYMPIC_LIFT": {
        "CLEAN":                                 "Clean",
        "POWER_CLEAN":                           "Power Clean",
        "HANG_CLEAN":                            "Hang Clean",
        "SNATCH":                                "Snatch",
        "POWER_SNATCH":                          "Power Snatch",
        "CLEAN_AND_JERK":                        "Clean and Jerk",
        "PUSH_JERK":                             "Push Jerk",
        "SPLIT_JERK":                            "Split Jerk",
    },

    # -----------------------------------------------------------------------
    # TOTAL BODY / CARDIO
    # -----------------------------------------------------------------------
    "TOTAL_BODY": {
        "BURPEE":                                "Burpee",
        "THRUSTER":                              "Thruster",
        "KETTLEBELL_SWING":                      "Kettlebell Swing",
        "FARMERS_WALK":                          "Farmer's Walk",
        "SLED_PUSH":                             "Sled Push",
        "SLED_DRAG":                             "Sled Drag",
        "BATTLE_ROPE":                           "Battle Rope",
        "MEDICINE_BALL_SLAM":                    "Medicine Ball Slam",
        "BOX_JUMP":                              "Box Jump",
        "BROAD_JUMP":                            "Broad Jump",
    },
}


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


def all_exercises() -> Iterator[Exercise]:
    """Yield every ``Exercise`` in the catalog."""
    for category, names in EXERCISES.items():
        for name, label in names.items():
            yield Exercise(category=category, name=name, label=label)


def resolve(query: str) -> Exercise:
    """Return the best-matching ``Exercise`` for a natural-language *query*.

    Matching strategy (case-insensitive):
    1. Exact label match  — ``"Barbell Bench Press"``
    2. Exact NAME match   — ``"BARBELL_BENCH_PRESS"``
    3. All query tokens present in label (partial / fuzzy)

    Raises
    ------
    KeyError
        If no match is found.
    """
    q = query.strip().lower()

    for ex in all_exercises():
        if ex.label.lower() == q:
            return ex
        if ex.name.lower().replace("_", " ") == q.replace("_", " "):
            return ex

    # Fuzzy: all words in query must appear in label.
    tokens = q.replace("_", " ").split()
    candidates = [
        ex for ex in all_exercises()
        if all(tok in ex.label.lower() for tok in tokens)
    ]
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        # Prefer shorter labels (more specific match).
        return min(candidates, key=lambda e: len(e.label))

    raise KeyError(
        f"No exercise matching {query!r}.  "
        "See garminforge.workouts.exercises.EXERCISES for the full catalog."
    )


def validate(category: str, name: str) -> bool:
    """Return ``True`` if *category* / *name* exists in the local catalog.

    Note: Garmin's server-side catalog is larger than this local copy;
    a ``False`` return does not guarantee upload failure.
    """
    cat = EXERCISES.get(category.upper())
    if cat is None:
        return False
    return name.upper() in cat
