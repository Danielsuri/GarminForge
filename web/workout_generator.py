"""
Workout generation logic.

Takes three user inputs:
- equipment: list of available equipment tags
- goal:      one of the GOALS keys
- duration_minutes: total session length in minutes

Produces:
- A ``StrengthWorkout`` payload dict ready to POST to Garmin Connect.
- A structured ``WorkoutPlan`` with rich exercise metadata for the UI preview.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from garminforge.workouts.strength import StrengthWorkout, ExerciseBlock
from web.exercise_links import get_exercise_link

# ---------------------------------------------------------------------------
# Goal definitions
# ---------------------------------------------------------------------------

GOALS: dict[str, dict[str, Any]] = {
    "burn_fat": {
        "label":       "Burn Fat",
        "icon":        "🔥",
        "description": "High reps, short rest, maximum calorie burn.",
        "sets":        3,
        "reps":        15,
        "rest_seconds": 45,
        "emphasis":    ["compound", "total_body"],
    },
    "lose_weight": {
        "label":       "Lose Weight",
        "icon":        "⚖️",
        "description": "Moderate reps, moderate rest, balanced intensity.",
        "sets":        3,
        "reps":        12,
        "rest_seconds": 60,
        "emphasis":    ["compound", "total_body"],
    },
    "build_muscle": {
        "label":       "Build Muscle",
        "icon":        "💪",
        "description": "Hypertrophy rep range, full rest between sets.",
        "sets":        4,
        "reps":        8,
        "rest_seconds": 90,
        "emphasis":    ["compound", "isolation"],
    },
    "build_strength": {
        "label":       "Build Strength",
        "icon":        "🏋️",
        "description": "Heavy compound lifts, maximal strength adaptation.",
        "sets":        5,
        "reps":        5,
        "rest_seconds": 180,
        "emphasis":    ["compound"],
    },
    "general_fitness": {
        "label":       "General Fitness",
        "icon":        "🏅",
        "description": "Well-rounded training for overall health.",
        "sets":        3,
        "reps":        10,
        "rest_seconds": 75,
        "emphasis":    ["compound", "isolation", "core"],
    },
    "endurance": {
        "label":       "Muscular Endurance",
        "icon":        "🚴",
        "description": "High reps, minimal rest, endurance adaptation.",
        "sets":        3,
        "reps":        20,
        "rest_seconds": 30,
        "emphasis":    ["compound", "total_body"],
    },
}

# ---------------------------------------------------------------------------
# Equipment definitions (display + tag)
# ---------------------------------------------------------------------------

EQUIPMENT_OPTIONS: list[dict[str, str]] = [
    {"tag": "barbell",    "label": "Barbell",          "icon": "🏋️"},
    {"tag": "dumbbell",   "label": "Dumbbells",         "icon": "🤸"},
    {"tag": "cable",      "label": "Cable Machine",     "icon": "🔗"},
    {"tag": "machine",    "label": "Weight Machines",   "icon": "⚙️"},
    {"tag": "kettlebell", "label": "Kettlebell",        "icon": "🫙"},
    {"tag": "bodyweight", "label": "Bodyweight Only",   "icon": "🧘"},
    {"tag": "band",       "label": "Resistance Bands",  "icon": "🪢"},
]


# ---------------------------------------------------------------------------
# Exercise pool
# ---------------------------------------------------------------------------

@dataclass
class _ExTemplate:
    category:     str
    name:         str
    label:        str
    muscle_group: str    # push | pull | squat | hinge | lunge | core | arms_bi | arms_tri | shoulders | calves
    tags:         list[str]  # compound | isolation | total_body | core
    equipment:    list[str]  # barbell | dumbbell | cable | machine | kettlebell | bodyweight | band


_POOL: list[_ExTemplate] = [
    # -----------------------------------------------------------------------
    # PUSH — chest compound
    # -----------------------------------------------------------------------
    _ExTemplate("BENCH_PRESS",      "BARBELL_BENCH_PRESS",           "Barbell Bench Press",           "push",   ["compound"], ["barbell"]),
    _ExTemplate("BENCH_PRESS",      "DUMBBELL_BENCH_PRESS",          "Dumbbell Bench Press",          "push",   ["compound"], ["dumbbell"]),
    _ExTemplate("BENCH_PRESS",      "INCLINE_BARBELL_BENCH_PRESS",   "Incline Barbell Bench Press",   "push",   ["compound"], ["barbell"]),
    _ExTemplate("BENCH_PRESS",      "INCLINE_DUMBBELL_BENCH_PRESS",  "Incline Dumbbell Bench Press",  "push",   ["compound"], ["dumbbell"]),
    _ExTemplate("PUSH_UP",          "PUSH_UP",                       "Push-Up",                       "push",   ["compound"], ["bodyweight"]),
    _ExTemplate("PUSH_UP",          "DIAMOND_PUSH_UP",               "Diamond Push-Up",               "push",   ["compound"], ["bodyweight"]),
    # PUSH — shoulder compound
    _ExTemplate("SHOULDER_PRESS",   "BARBELL_SHOULDER_PRESS",        "Barbell Shoulder Press",        "push",   ["compound"], ["barbell"]),
    _ExTemplate("SHOULDER_PRESS",   "DUMBBELL_SHOULDER_PRESS",       "Dumbbell Shoulder Press",       "push",   ["compound"], ["dumbbell"]),
    _ExTemplate("SHOULDER_PRESS",   "ARNOLD_PRESS",                  "Arnold Press",                  "push",   ["compound"], ["dumbbell"]),
    # PUSH — isolation
    _ExTemplate("FLYE",             "DUMBBELL_FLYE",                 "Dumbbell Flye",                 "push",   ["isolation"], ["dumbbell"]),
    _ExTemplate("FLYE",             "CABLE_CROSSOVER",               "Cable Crossover",               "push",   ["isolation"], ["cable"]),
    _ExTemplate("LATERAL_RAISE",    "DUMBBELL_LATERAL_RAISE",        "Dumbbell Lateral Raise",        "shoulders", ["isolation"], ["dumbbell"]),
    _ExTemplate("LATERAL_RAISE",    "CABLE_LATERAL_RAISE",           "Cable Lateral Raise",           "shoulders", ["isolation"], ["cable"]),

    # -----------------------------------------------------------------------
    # PULL — compound
    # -----------------------------------------------------------------------
    _ExTemplate("PULL_UP",          "PULL_UP",                       "Pull-Up",                       "pull",   ["compound"], ["bodyweight"]),
    _ExTemplate("PULL_UP",          "CHIN_UP",                       "Chin-Up",                       "pull",   ["compound"], ["bodyweight"]),
    _ExTemplate("PULL_UP",          "LAT_PULLDOWN",                  "Lat Pulldown",                  "pull",   ["compound"], ["cable", "machine"]),
    _ExTemplate("ROW",              "BARBELL_ROW",                   "Barbell Row",                   "pull",   ["compound"], ["barbell"]),
    _ExTemplate("ROW",              "DUMBBELL_ROW",                  "Dumbbell Row",                  "pull",   ["compound"], ["dumbbell"]),
    _ExTemplate("ROW",              "CABLE_ROW",                     "Cable Row",                     "pull",   ["compound"], ["cable"]),
    _ExTemplate("ROW",              "T_BAR_ROW",                     "T-Bar Row",                     "pull",   ["compound"], ["barbell"]),
    _ExTemplate("ROW",              "SEATED_CABLE_ROW",              "Seated Cable Row",              "pull",   ["compound"], ["cable"]),
    _ExTemplate("ROW",              "FACE_PULL",                     "Face Pull",                     "pull",   ["isolation"], ["cable"]),
    _ExTemplate("HYPEREXTENSION",   "BACK_EXTENSION",                "Back Extension",                "pull",   ["isolation"], ["bodyweight", "machine"]),
    # PULL — isolation
    _ExTemplate("CURL",             "BARBELL_CURL",                  "Barbell Curl",                  "arms_bi",["isolation"], ["barbell"]),
    _ExTemplate("CURL",             "DUMBBELL_CURL",                 "Dumbbell Curl",                 "arms_bi",["isolation"], ["dumbbell"]),
    _ExTemplate("CURL",             "HAMMER_CURL",                   "Hammer Curl",                   "arms_bi",["isolation"], ["dumbbell"]),
    _ExTemplate("CURL",             "PREACHER_CURL",                 "Preacher Curl",                 "arms_bi",["isolation"], ["barbell", "dumbbell"]),
    _ExTemplate("CURL",             "INCLINE_DUMBBELL_CURL",         "Incline Dumbbell Curl",         "arms_bi",["isolation"], ["dumbbell"]),
    _ExTemplate("CURL",             "EZ_BAR_CURL",                   "EZ-Bar Curl",                   "arms_bi",["isolation"], ["barbell"]),

    # -----------------------------------------------------------------------
    # SQUAT — compound
    # -----------------------------------------------------------------------
    _ExTemplate("SQUAT",            "BARBELL_BACK_SQUAT",            "Barbell Back Squat",            "squat",  ["compound"], ["barbell"]),
    _ExTemplate("SQUAT",            "BARBELL_FRONT_SQUAT",           "Barbell Front Squat",           "squat",  ["compound"], ["barbell"]),
    _ExTemplate("SQUAT",            "GOBLET_SQUAT",                  "Goblet Squat",                  "squat",  ["compound"], ["dumbbell", "kettlebell"]),
    _ExTemplate("SQUAT",            "HACK_SQUAT",                    "Hack Squat",                    "squat",  ["compound"], ["machine"]),
    _ExTemplate("SQUAT",            "LEG_PRESS",                     "Leg Press",                     "squat",  ["compound"], ["machine"]),

    # LUNGE / SPLIT
    _ExTemplate("LUNGE",            "DUMBBELL_LUNGE",                "Dumbbell Lunge",                "lunge",  ["compound"], ["dumbbell"]),
    _ExTemplate("LUNGE",            "WALKING_LUNGE",                 "Walking Lunge",                 "lunge",  ["compound"], ["dumbbell", "barbell", "bodyweight"]),
    _ExTemplate("LUNGE",            "REVERSE_LUNGE",                 "Reverse Lunge",                 "lunge",  ["compound"], ["dumbbell", "barbell", "bodyweight"]),
    _ExTemplate("LUNGE",            "BULGARIAN_SPLIT_SQUAT",         "Bulgarian Split Squat",         "lunge",  ["compound"], ["dumbbell", "barbell", "bodyweight"]),

    # -----------------------------------------------------------------------
    # HINGE — compound
    # -----------------------------------------------------------------------
    _ExTemplate("DEADLIFT",         "BARBELL_DEADLIFT",              "Barbell Deadlift",              "hinge",  ["compound"], ["barbell"]),
    _ExTemplate("DEADLIFT",         "ROMANIAN_DEADLIFT",             "Romanian Deadlift",             "hinge",  ["compound"], ["barbell"]),
    _ExTemplate("DEADLIFT",         "SUMO_DEADLIFT",                 "Sumo Deadlift",                 "hinge",  ["compound"], ["barbell"]),
    _ExTemplate("DEADLIFT",         "TRAP_BAR_DEADLIFT",             "Trap Bar Deadlift",             "hinge",  ["compound"], ["barbell"]),
    _ExTemplate("HIP_RAISE",        "BARBELL_HIP_THRUST",            "Barbell Hip Thrust",            "hinge",  ["compound"], ["barbell"]),
    _ExTemplate("HIP_RAISE",        "DUMBBELL_HIP_THRUST",           "Dumbbell Hip Thrust",           "hinge",  ["compound"], ["dumbbell"]),
    _ExTemplate("HIP_RAISE",        "GLUTE_BRIDGE",                  "Glute Bridge",                  "hinge",  ["compound"], ["bodyweight"]),
    _ExTemplate("LEG_CURL",         "LYING_LEG_CURL",                "Lying Leg Curl",                "hinge",  ["isolation"], ["machine"]),
    _ExTemplate("LEG_CURL",         "SEATED_LEG_CURL",               "Seated Leg Curl",               "hinge",  ["isolation"], ["machine"]),
    _ExTemplate("LEG_CURL",         "GOOD_MORNING",                  "Good Morning",                  "hinge",  ["compound"], ["barbell"]),

    # -----------------------------------------------------------------------
    # TRICEPS isolation
    # -----------------------------------------------------------------------
    _ExTemplate("TRICEPS_EXTENSION","TRICEPS_PUSHDOWN",              "Triceps Pushdown",              "arms_tri",["isolation"], ["cable"]),
    _ExTemplate("TRICEPS_EXTENSION","SKULL_CRUSHER",                 "Skull Crusher",                 "arms_tri",["isolation"], ["barbell", "dumbbell"]),
    _ExTemplate("TRICEPS_EXTENSION","OVERHEAD_DUMBBELL_TRICEPS_EXTENSION","Overhead DB Triceps Ext.","arms_tri",["isolation"], ["dumbbell"]),
    _ExTemplate("TRICEPS_EXTENSION","TRICEPS_DIP",                   "Triceps Dip",                   "arms_tri",["isolation"], ["bodyweight"]),

    # -----------------------------------------------------------------------
    # CORE
    # -----------------------------------------------------------------------
    _ExTemplate("PLANK",            "PLANK",                         "Plank",                         "core",   ["core"], ["bodyweight"]),
    _ExTemplate("PLANK",            "SIDE_PLANK",                    "Side Plank",                    "core",   ["core"], ["bodyweight"]),
    _ExTemplate("CRUNCH",           "CRUNCH",                        "Crunch",                        "core",   ["core"], ["bodyweight"]),
    _ExTemplate("CRUNCH",           "BICYCLE_CRUNCH",                "Bicycle Crunch",                "core",   ["core"], ["bodyweight"]),
    _ExTemplate("CRUNCH",           "REVERSE_CRUNCH",                "Reverse Crunch",                "core",   ["core"], ["bodyweight"]),
    _ExTemplate("LEG_RAISE",        "LYING_LEG_RAISE",               "Lying Leg Raise",               "core",   ["core"], ["bodyweight"]),
    _ExTemplate("LEG_RAISE",        "HANGING_LEG_RAISE",             "Hanging Leg Raise",             "core",   ["core"], ["bodyweight"]),
    _ExTemplate("CORE",             "DEAD_BUG",                      "Dead Bug",                      "core",   ["core"], ["bodyweight"]),
    _ExTemplate("CORE",             "RUSSIAN_TWIST",                 "Russian Twist",                 "core",   ["core"], ["bodyweight", "dumbbell"]),
    _ExTemplate("CORE",             "AB_WHEEL_ROLLOUT",              "Ab Wheel Rollout",              "core",   ["core"], ["bodyweight"]),

    # -----------------------------------------------------------------------
    # TOTAL BODY
    # -----------------------------------------------------------------------
    _ExTemplate("TOTAL_BODY",       "BURPEE",                        "Burpee",                        "total_body",["total_body","compound"],["bodyweight"]),
    _ExTemplate("TOTAL_BODY",       "KETTLEBELL_SWING",              "Kettlebell Swing",              "total_body",["total_body","compound"],["kettlebell"]),
    _ExTemplate("TOTAL_BODY",       "BOX_JUMP",                      "Box Jump",                      "total_body",["total_body","compound"],["bodyweight"]),
    _ExTemplate("TOTAL_BODY",       "FARMERS_WALK",                  "Farmer's Walk",                 "total_body",["total_body","compound"],["dumbbell","kettlebell"]),
]


# ---------------------------------------------------------------------------
# Selection strategy
# ---------------------------------------------------------------------------

# Desired muscle group order for a full-body session
_FULL_BODY_ORDER = ["squat", "push", "hinge", "pull", "lunge", "core", "arms_bi", "arms_tri", "shoulders"]

# Tags that count as "compound" for strength/burn goals
_COMPOUND_TAGS = {"compound", "total_body"}


def _available(equipment: list[str]) -> list[_ExTemplate]:
    """Filter pool to exercises reachable with the given equipment."""
    eq_set = set(equipment)
    return [ex for ex in _POOL if eq_set.intersection(ex.equipment)]


def _num_exercises(duration_minutes: int, goal: str) -> int:
    """How many exercise blocks fit in *duration_minutes* for *goal*."""
    # 10 min overhead for warmup + cooldown
    work_minutes = max(5, duration_minutes - 10)
    # Minutes per exercise block (including sets + rest)
    mins_per_block = {
        "burn_fat":       4,
        "lose_weight":    5,
        "build_muscle":   8,
        "build_strength": 12,
        "general_fitness": 7,
        "endurance":      4,
    }.get(goal, 6)
    return max(2, min(9, work_minutes // mins_per_block))


def _select_exercises(
    available: list[_ExTemplate],
    num: int,
    goal: str,
) -> list[_ExTemplate]:
    """Choose *num* exercises balancing muscle groups and goal emphasis."""
    emphasis = set(GOALS[goal]["emphasis"])
    compound_only = "compound" in emphasis and "isolation" not in emphasis

    # Separate by muscle group, respecting goal
    by_group: dict[str, list[_ExTemplate]] = {}
    for ex in available:
        # For strength goals, skip isolation-only exercises
        if compound_only and not _COMPOUND_TAGS.intersection(ex.tags):
            continue
        by_group.setdefault(ex.muscle_group, []).append(ex)

    # If very few options, fall back to all available
    if sum(len(v) for v in by_group.values()) < num:
        by_group = {}
        for ex in available:
            by_group.setdefault(ex.muscle_group, []).append(ex)

    selected: list[_ExTemplate] = []
    used_groups: set[str] = set()

    # First pass: one exercise per muscle group in preferred order
    for group in _FULL_BODY_ORDER:
        if len(selected) >= num:
            break
        candidates = by_group.get(group, [])
        if not candidates:
            continue
        # Prefer compound for fat/strength; allow isolation for muscle/fitness
        comp = [c for c in candidates if _COMPOUND_TAGS.intersection(c.tags)]
        pick_from = comp if comp and compound_only else candidates
        ex = random.choice(pick_from)
        selected.append(ex)
        used_groups.add(group)

    # Second pass: fill remaining slots from unused groups then any group
    for group in _FULL_BODY_ORDER:
        if len(selected) >= num:
            break
        if group in used_groups:
            continue
        candidates = by_group.get(group, [])
        if not candidates:
            continue
        selected.append(random.choice(candidates))
        used_groups.add(group)

    # If still short, allow repeating groups
    remaining = num - len(selected)
    if remaining > 0:
        all_candidates = [ex for exs in by_group.values() for ex in exs
                          if ex not in selected]
        random.shuffle(all_candidates)
        selected.extend(all_candidates[:remaining])

    return selected[:num]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class ExerciseInfo:
    """Rich exercise metadata for the UI preview."""
    category:     str
    name:         str
    label:        str
    muscle_group: str
    sets:         int
    reps:         int | None
    duration_sec: float | None
    rest_seconds: float
    link:         str
    description:  str   # embedded in Garmin step


@dataclass
class WorkoutPlan:
    """Generated workout ready for preview and upload."""
    name:            str
    goal_label:      str
    goal_icon:       str
    description:     str
    duration_minutes: int
    exercises:       list[ExerciseInfo]
    garmin_payload:  dict[str, Any]


def generate(
    equipment: list[str],
    goal: str,
    duration_minutes: int,
    *,
    seed: int | None = None,
) -> WorkoutPlan:
    """Generate a balanced workout.

    Parameters
    ----------
    equipment:
        List of equipment tags from ``EQUIPMENT_OPTIONS``.
    goal:
        One of the ``GOALS`` keys.
    duration_minutes:
        Total session length including warmup/cooldown.
    seed:
        Optional random seed for reproducible generation.
    """
    if seed is not None:
        random.seed(seed)

    if goal not in GOALS:
        raise ValueError(f"Unknown goal {goal!r}. Choose from: {list(GOALS)}")

    goal_cfg = GOALS[goal]
    sets        = goal_cfg["sets"]
    reps        = goal_cfg["reps"]
    rest        = goal_cfg["rest_seconds"]

    # --- exercise selection -------------------------------------------------
    available   = _available(equipment) if equipment else _POOL
    num         = _num_exercises(duration_minutes, goal)
    templates   = _select_exercises(available, num, goal)

    # For timed exercises (plank, etc.), convert reps to duration
    TIMED_EXERCISES = {
        "PLANK", "SIDE_PLANK", "FOREARM_PLANK",
        "DEAD_BUG", "FARMERS_WALK", "BATTLE_ROPE",
    }

    # --- build ExerciseInfo list --------------------------------------------
    exercises: list[ExerciseInfo] = []
    for tmpl in templates:
        is_timed = tmpl.name in TIMED_EXERCISES
        link = get_exercise_link(tmpl.name, tmpl.label)

        if is_timed:
            # Convert reps to hold time: 1 "rep" = 3 seconds, capped at 60s
            hold = min(60.0, reps * 3.0)
            desc = f"{tmpl.label} — {int(hold)}s hold | How to: {link}"
        else:
            hold = None
            desc = f"{tmpl.label} — {sets}×{reps} | How to: {link}"

        exercises.append(ExerciseInfo(
            category=tmpl.category,
            name=tmpl.name,
            label=tmpl.label,
            muscle_group=tmpl.muscle_group,
            sets=sets,
            reps=None if is_timed else reps,
            duration_sec=hold,
            rest_seconds=rest,
            link=link,
            description=desc,
        ))

    # --- build StrengthWorkout payload --------------------------------------
    date_str = datetime.now().strftime("%b %d")
    workout_name = f"{goal_cfg['label']} — {duration_minutes}min ({date_str})"
    workout_desc = (
        f"{goal_cfg['description']} "
        f"Equipment: {', '.join(equipment) if equipment else 'bodyweight'}."
    )

    builder = (
        StrengthWorkout(workout_name, description=workout_desc)
        .add_warmup(description="5 min general warm-up")
    )

    for ex in exercises:
        block = ExerciseBlock(
            category=ex.category,
            name=ex.name,
            sets=ex.sets,
            reps=ex.reps,
            duration_seconds=ex.duration_sec,
            rest_seconds=ex.rest_seconds,
            description=ex.description,
        )
        builder.add_block(block)

    builder.add_cooldown(description="Cool-down + stretch")
    payload = builder.build(validate=False)

    return WorkoutPlan(
        name=workout_name,
        goal_label=goal_cfg["label"],
        goal_icon=goal_cfg["icon"],
        description=workout_desc,
        duration_minutes=duration_minutes,
        exercises=exercises,
        garmin_payload=payload,
    )
