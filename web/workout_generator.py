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

# Equipment options shown in the UI.
# `tag`        — internal key used to match exercises in the pool
# `garmin_key` — Garmin's official equipmentTypeKey (from exercise_equipments.properties)
# `label`      — display name shown to the user
EQUIPMENT_OPTIONS: list[dict[str, str]] = [
    {"tag": "barbell",       "garmin_key": "BARBELL",       "label": "Barbell",           "icon": "🏋️"},
    {"tag": "dumbbell",      "garmin_key": "DUMBBELL",      "label": "Dumbbells",          "icon": "🤸"},
    {"tag": "kettlebell",    "garmin_key": "KETTLEBELL",    "label": "Kettlebell",         "icon": "🫙"},
    {"tag": "cable",         "garmin_key": "CABLE_MACHINE", "label": "Cable Machine",      "icon": "🔗"},
    {"tag": "machine",       "garmin_key": "MACHINE",       "label": "Weight Machines",    "icon": "⚙️"},
    {"tag": "bodyweight",    "garmin_key": None,            "label": "Bodyweight Only",    "icon": "🧘"},
    {"tag": "band",          "garmin_key": "BAND",          "label": "Resistance Bands",   "icon": "🪢"},
    {"tag": "pullup_bar",    "garmin_key": "PULLUP_BAR",    "label": "Pull-up Bar",        "icon": "🔝"},
    {"tag": "bench",         "garmin_key": "BENCH",         "label": "Bench",              "icon": "🪑"},
    {"tag": "medicine_ball", "garmin_key": "MEDICINE_BALL", "label": "Medicine Ball",      "icon": "⚽"},
    {"tag": "ez_bar",        "garmin_key": "EZ_BAR",        "label": "EZ Bar",             "icon": "〰️"},
    {"tag": "plate",         "garmin_key": "PLATE",         "label": "Weight Plate",       "icon": "🔵"},
    {"tag": "box",           "garmin_key": "BOX",           "label": "Box / Step",         "icon": "📦"},
    {"tag": "swiss_ball",    "garmin_key": "SWISS_BALL",    "label": "Swiss Ball",         "icon": "🟢"},
    {"tag": "trx",           "garmin_key": "TRX",           "label": "TRX / Suspension",   "icon": "🪢"},
    {"tag": "sandbag",       "garmin_key": "SANDBAG",       "label": "Sandbag",            "icon": "🪨"},
    {"tag": "battle_rope",   "garmin_key": "BATTLE_ROPE",   "label": "Battle Rope",        "icon": "🌊"},
    {"tag": "sled",          "garmin_key": "SLED",          "label": "Sled",               "icon": "🛷"},
    {"tag": "rings",         "garmin_key": "RINGS",         "label": "Gymnastic Rings",    "icon": "⭕"},
    {"tag": "smith_machine", "garmin_key": "SMITH_MACHINE", "label": "Smith Machine",      "icon": "🏗️"},
    {"tag": "weight_vest",   "garmin_key": "WEIGHT_VEST",   "label": "Weight Vest",        "icon": "🦺"},
    {"tag": "bosu_ball",     "garmin_key": "BOSU_BALL",     "label": "Bosu Ball",          "icon": "🟤"},
    {"tag": "ankle_weight",  "garmin_key": "ANKLE_WEIGHT",  "label": "Ankle Weights",      "icon": "🦿"},
    {"tag": "sliding_disc",  "garmin_key": "SLIDING_DISC",  "label": "Sliding Discs",      "icon": "💿"},
    {"tag": "ab_wheel",      "garmin_key": None,            "label": "Ab Wheel",            "icon": "⚙️"},
    {"tag": "rope",          "garmin_key": "ROPE",          "label": "Climbing Rope",       "icon": "🪢"},
    {"tag": "jump_rope",     "garmin_key": "JUMP_ROPE",     "label": "Jump Rope",           "icon": "🪃"},
    {"tag": "foam_roller",   "garmin_key": "FOAM_ROLLER",   "label": "Foam Roller",         "icon": "🛞"},
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
    _ExTemplate("PUSH_UP",          "PUSH_UP",                       "Push-Up",                       "push",   ["compound"], ["bodyweight", "weight_vest"]),
    _ExTemplate("PUSH_UP",          "DIAMOND_PUSH_UP",               "Diamond Push-Up",               "push",   ["compound"], ["bodyweight"]),
    _ExTemplate("PUSH_UP",          "INCLINE_PUSH_UP",               "Incline Push-Up",               "push",   ["compound"], ["bench", "bodyweight", "bosu_ball"]),
    _ExTemplate("PUSH_UP",          "DECLINE_PUSH_UP",               "Decline Push-Up",               "push",   ["compound"], ["bench", "bodyweight"]),
    # PUSH — shoulder compound
    _ExTemplate("SHOULDER_PRESS",   "BARBELL_SHOULDER_PRESS",        "Barbell Shoulder Press",        "push",   ["compound"], ["barbell", "smith_machine"]),
    _ExTemplate("SHOULDER_PRESS",   "DUMBBELL_SHOULDER_PRESS",       "Dumbbell Shoulder Press",       "push",   ["compound"], ["dumbbell"]),
    _ExTemplate("SHOULDER_PRESS",   "ARNOLD_PRESS",                  "Arnold Press",                  "push",   ["compound"], ["dumbbell"]),
    # PUSH — isolation
    _ExTemplate("FLYE",             "DUMBBELL_FLYE",                 "Dumbbell Flye",                 "push",   ["isolation"], ["dumbbell"]),
    _ExTemplate("FLYE",             "CABLE_CROSSOVER",               "Cable Crossover",               "push",   ["isolation"], ["cable"]),
    _ExTemplate("LATERAL_RAISE",    "DUMBBELL_LATERAL_RAISE",        "Dumbbell Lateral Raise",        "shoulders", ["isolation"], ["dumbbell", "band"]),
    _ExTemplate("LATERAL_RAISE",    "CABLE_LATERAL_RAISE",           "Cable Lateral Raise",           "shoulders", ["isolation"], ["cable"]),

    # -----------------------------------------------------------------------
    # PULL — compound
    # -----------------------------------------------------------------------
    _ExTemplate("PULL_UP",          "PULL_UP",                       "Pull-Up",                       "pull",   ["compound"], ["pullup_bar", "weight_vest"]),
    _ExTemplate("PULL_UP",          "CHIN_UP",                       "Chin-Up",                       "pull",   ["compound"], ["pullup_bar"]),
    _ExTemplate("PULL_UP",          "WIDE_GRIP_PULL_UP",             "Wide-Grip Pull-Up",             "pull",   ["compound"], ["pullup_bar"]),
    _ExTemplate("PULL_UP",          "NEUTRAL_GRIP_PULL_UP",          "Neutral-Grip Pull-Up",          "pull",   ["compound"], ["pullup_bar"]),
    _ExTemplate("PULL_UP",          "BANDED_PULL_UP",                "Banded Pull-Up",                "pull",   ["compound"], ["pullup_bar", "band"]),
    _ExTemplate("PULL_UP",          "LAT_PULLDOWN",                  "Lat Pulldown",                  "pull",   ["compound"], ["cable", "machine"]),
    _ExTemplate("ROW",              "BARBELL_ROW",                   "Barbell Row",                   "pull",   ["compound"], ["barbell"]),
    _ExTemplate("ROW",              "DUMBBELL_ROW",                  "Dumbbell Row",                  "pull",   ["compound"], ["dumbbell"]),
    _ExTemplate("ROW",              "CABLE_ROW",                     "Cable Row",                     "pull",   ["compound"], ["cable"]),
    _ExTemplate("ROW",              "T_BAR_ROW",                     "T-Bar Row",                     "pull",   ["compound"], ["barbell"]),
    _ExTemplate("ROW",              "SEATED_CABLE_ROW",              "Seated Cable Row",              "pull",   ["compound"], ["cable"]),
    _ExTemplate("ROW",              "FACE_PULL",                     "Face Pull",                     "pull",   ["isolation"], ["cable"]),
    _ExTemplate("ROW",              "INVERTED_ROW",                  "Inverted Row",                  "pull",   ["compound"], ["pullup_bar", "barbell", "smith_machine", "trx", "rings"]),
    _ExTemplate("HYPEREXTENSION",   "BACK_EXTENSION",                "Back Extension",                "pull",   ["isolation"], ["bench", "machine"]),
    # PULL — isolation
    _ExTemplate("CURL",             "BARBELL_CURL",                  "Barbell Curl",                  "arms_bi",["isolation"], ["barbell"]),
    _ExTemplate("CURL",             "DUMBBELL_CURL",                 "Dumbbell Curl",                 "arms_bi",["isolation"], ["dumbbell"]),
    _ExTemplate("CURL",             "HAMMER_CURL",                   "Hammer Curl",                   "arms_bi",["isolation"], ["dumbbell"]),
    _ExTemplate("CURL",             "PREACHER_CURL",                 "Preacher Curl",                 "arms_bi",["isolation"], ["barbell", "dumbbell", "ez_bar"]),
    _ExTemplate("CURL",             "INCLINE_DUMBBELL_CURL",         "Incline Dumbbell Curl",         "arms_bi",["isolation"], ["dumbbell"]),
    _ExTemplate("CURL",             "EZ_BAR_CURL",                   "EZ-Bar Curl",                   "arms_bi",["isolation"], ["barbell", "ez_bar"]),

    # -----------------------------------------------------------------------
    # SQUAT — compound
    # -----------------------------------------------------------------------
    _ExTemplate("SQUAT",            "BARBELL_BACK_SQUAT",            "Barbell Back Squat",            "squat",  ["compound"], ["barbell", "smith_machine"]),
    _ExTemplate("SQUAT",            "BARBELL_FRONT_SQUAT",           "Barbell Front Squat",           "squat",  ["compound"], ["barbell"]),
    _ExTemplate("SQUAT",            "GOBLET_SQUAT",                  "Goblet Squat",                  "squat",  ["compound"], ["dumbbell", "kettlebell", "plate"]),
    _ExTemplate("SQUAT",            "BOX_SQUAT",                     "Box Squat",                     "squat",  ["compound"], ["box", "barbell"]),
    _ExTemplate("SQUAT",            "HACK_SQUAT",                    "Hack Squat",                    "squat",  ["compound"], ["machine", "smith_machine"]),
    _ExTemplate("SQUAT",            "LEG_PRESS",                     "Leg Press",                     "squat",  ["compound"], ["machine"]),

    # LUNGE / SPLIT
    _ExTemplate("LUNGE",            "DUMBBELL_LUNGE",                "Dumbbell Lunge",                "lunge",  ["compound"], ["dumbbell"]),
    _ExTemplate("LUNGE",            "WALKING_LUNGE",                 "Walking Lunge",                 "lunge",  ["compound"], ["dumbbell", "barbell", "bodyweight", "weight_vest"]),
    _ExTemplate("LUNGE",            "REVERSE_LUNGE",                 "Reverse Lunge",                 "lunge",  ["compound"], ["dumbbell", "barbell", "bodyweight"]),
    _ExTemplate("LUNGE",            "BULGARIAN_SPLIT_SQUAT",         "Bulgarian Split Squat",         "lunge",  ["compound"], ["dumbbell", "barbell", "bodyweight"]),
    _ExTemplate("LUNGE",            "STEP_UP",                       "Step-Up",                       "lunge",  ["compound"], ["bench", "box"]),

    # -----------------------------------------------------------------------
    # HINGE — compound
    # -----------------------------------------------------------------------
    _ExTemplate("DEADLIFT",         "BARBELL_DEADLIFT",              "Barbell Deadlift",              "hinge",  ["compound"], ["barbell"]),
    _ExTemplate("DEADLIFT",         "ROMANIAN_DEADLIFT",             "Romanian Deadlift",             "hinge",  ["compound"], ["barbell"]),
    _ExTemplate("DEADLIFT",         "DUMBBELL_ROMANIAN_DEADLIFT",    "Dumbbell Romanian Deadlift",    "hinge",  ["compound"], ["dumbbell"]),
    _ExTemplate("DEADLIFT",         "SUMO_DEADLIFT",                 "Sumo Deadlift",                 "hinge",  ["compound"], ["barbell"]),
    _ExTemplate("DEADLIFT",         "TRAP_BAR_DEADLIFT",             "Trap Bar Deadlift",             "hinge",  ["compound"], ["barbell"]),
    _ExTemplate("HIP_RAISE",        "BARBELL_HIP_THRUST",            "Barbell Hip Thrust",            "hinge",  ["compound"], ["barbell"]),
    _ExTemplate("HIP_RAISE",        "DUMBBELL_HIP_THRUST",           "Dumbbell Hip Thrust",           "hinge",  ["compound"], ["dumbbell"]),
    _ExTemplate("HIP_RAISE",        "GLUTE_BRIDGE",                  "Glute Bridge",                  "hinge",  ["compound"], ["bodyweight", "band", "ankle_weight"]),
    _ExTemplate("LEG_CURL",         "LYING_LEG_CURL",                "Lying Leg Curl",                "hinge",  ["isolation"], ["machine"]),
    _ExTemplate("LEG_CURL",         "SEATED_LEG_CURL",               "Seated Leg Curl",               "hinge",  ["isolation"], ["machine"]),
    _ExTemplate("LEG_CURL",         "GOOD_MORNING",                  "Good Morning",                  "hinge",  ["compound"], ["barbell"]),

    # -----------------------------------------------------------------------
    # TRICEPS isolation
    # -----------------------------------------------------------------------
    _ExTemplate("TRICEPS_EXTENSION","TRICEPS_PUSHDOWN",              "Triceps Pushdown",              "arms_tri",["isolation"], ["cable"]),
    _ExTemplate("TRICEPS_EXTENSION","SKULL_CRUSHER",                 "Skull Crusher",                 "arms_tri",["isolation"], ["barbell", "dumbbell", "ez_bar"]),
    _ExTemplate("TRICEPS_EXTENSION","OVERHEAD_DUMBBELL_TRICEPS_EXTENSION","Overhead DB Triceps Ext.","arms_tri",["isolation"], ["dumbbell"]),
    _ExTemplate("TRICEPS_EXTENSION","TRICEPS_DIP",                   "Triceps Dip",                   "arms_tri",["isolation"], ["bench"]),

    # -----------------------------------------------------------------------
    # CORE
    # -----------------------------------------------------------------------
    _ExTemplate("PLANK",            "PLANK",                         "Plank",                         "core",   ["core"], ["bodyweight"]),
    _ExTemplate("PLANK",            "SIDE_PLANK",                    "Side Plank",                    "core",   ["core"], ["bodyweight"]),
    _ExTemplate("CRUNCH",           "CRUNCH",                        "Crunch",                        "core",   ["core"], ["bodyweight"]),
    _ExTemplate("CRUNCH",           "BICYCLE_CRUNCH",                "Bicycle Crunch",                "core",   ["core"], ["bodyweight"]),
    _ExTemplate("CRUNCH",           "REVERSE_CRUNCH",                "Reverse Crunch",                "core",   ["core"], ["bodyweight"]),
    _ExTemplate("LEG_RAISE",        "LYING_LEG_RAISE",               "Lying Leg Raise",               "core",   ["core"], ["bodyweight", "ankle_weight"]),
    _ExTemplate("LEG_RAISE",        "HANGING_LEG_RAISE",             "Hanging Leg Raise",             "core",   ["core"], ["pullup_bar", "ankle_weight"]),
    _ExTemplate("LEG_RAISE",        "KNEE_RAISE",                    "Knee Raise",                    "core",   ["core"], ["pullup_bar"]),
    _ExTemplate("CORE",             "DEAD_BUG",                      "Dead Bug",                      "core",   ["core"], ["bodyweight"]),
    _ExTemplate("CORE",             "RUSSIAN_TWIST",                 "Russian Twist",                 "core",   ["core"], ["bodyweight", "dumbbell", "medicine_ball", "plate"]),
    _ExTemplate("CORE",             "KNEELING_AB_WHEEL",             "Kneeling Ab Wheel",             "core",   ["core"], ["ab_wheel"]),
    _ExTemplate("CORE",             "BARBELL_ROLLOUT",               "Barbell Roll-out",              "core",   ["core"], ["ab_wheel", "barbell"]),

    # -----------------------------------------------------------------------
    # TOTAL BODY
    # -----------------------------------------------------------------------
    _ExTemplate("TOTAL_BODY",       "BURPEE",                        "Burpee",                        "total_body",["total_body","compound"],["bodyweight"]),
    _ExTemplate("TOTAL_BODY",       "KETTLEBELL_SWING",              "Kettlebell Swing",              "total_body",["total_body","compound"],["kettlebell"]),
    # -----------------------------------------------------------------------
    # CARRY (correct Garmin category for farmer's walk / carries)
    # -----------------------------------------------------------------------
    _ExTemplate("CARRY",            "FARMERS_WALK",                  "Farmer's Walk",                 "total_body",["total_body","compound"],["dumbbell","kettlebell","plate","sandbag"]),
    _ExTemplate("CARRY",            "OVERHEAD_CARRY",                "Overhead Carry",                "shoulders", ["compound"],           ["dumbbell","kettlebell"]),
    # -----------------------------------------------------------------------
    # PLYO (correct Garmin category for jumps and med ball slams)
    # -----------------------------------------------------------------------
    _ExTemplate("PLYO",             "BOX_JUMP",                      "Box Jump",                      "total_body",["total_body","compound"],["box"]),
    _ExTemplate("PLYO",             "JUMP_SQUAT",                    "Jump Squat",                    "squat",     ["compound"],           ["bodyweight"]),
    _ExTemplate("PLYO",             "ALTERNATING_JUMP_LUNGE",        "Alternating Jump Lunge",        "lunge",     ["compound"],           ["bodyweight"]),
    _ExTemplate("PLYO",             "MEDICINE_BALL_SLAM",            "Medicine Ball Slam",            "total_body",["total_body","compound"],["medicine_ball"]),
    _ExTemplate("PLYO",             "MEDICINE_BALL_SIDE_THROW",      "Medicine Ball Side Throw",      "core",      ["core","compound"],     ["medicine_ball"]),
    # -----------------------------------------------------------------------
    # BATTLE ROPE (correct Garmin category)
    # -----------------------------------------------------------------------
    _ExTemplate("BATTLE_ROPE",      "ALTERNATING_WAVE",              "Battle Rope Alternating Wave",  "total_body",["total_body"],         ["battle_rope"]),
    _ExTemplate("BATTLE_ROPE",      "ALTERNATING_SQUAT_WAVE",        "Battle Rope Squat Wave",        "total_body",["total_body","compound"],["battle_rope"]),
    # -----------------------------------------------------------------------
    # SLED (correct Garmin category + correct exercise names)
    # -----------------------------------------------------------------------
    _ExTemplate("SLED",             "PUSH",                          "Sled Push",                     "total_body",["total_body","compound"],["sled"]),
    _ExTemplate("SLED",             "FORWARD_DRAG",                  "Sled Forward Drag",             "total_body",["total_body","compound"],["sled"]),
    # -----------------------------------------------------------------------
    # SANDBAG (correct Garmin category)
    # -----------------------------------------------------------------------
    _ExTemplate("SANDBAG",          "BACK_SQUAT",                    "Sandbag Back Squat",            "squat",     ["compound"],           ["sandbag"]),
    _ExTemplate("SANDBAG",          "LUNGE",                         "Sandbag Lunge",                 "lunge",     ["compound"],           ["sandbag"]),
    _ExTemplate("SANDBAG",          "CLEAN_AND_PRESS",               "Sandbag Clean and Press",       "total_body",["total_body","compound"],["sandbag"]),
    _ExTemplate("SANDBAG",          "ROW",                           "Sandbag Row",                   "pull",      ["compound"],           ["sandbag"]),
    _ExTemplate("SANDBAG",          "SHOULDERING",                   "Sandbag Shouldering",           "total_body",["total_body","compound"],["sandbag"]),
    # -----------------------------------------------------------------------
    # SUSPENSION (correct Garmin category for TRX and gymnastic rings)
    # -----------------------------------------------------------------------
    _ExTemplate("SUSPENSION",       "ROW",                           "Suspension Row",                "pull",      ["compound"],           ["trx","rings"]),
    _ExTemplate("SUSPENSION",       "PUSH_UP",                       "Suspension Push-up",            "push",      ["compound"],           ["trx","rings"]),
    _ExTemplate("SUSPENSION",       "CURL",                          "Suspension Curl",               "arms_bi",   ["isolation"],          ["trx","rings"]),
    _ExTemplate("SUSPENSION",       "DIP",                           "Suspension Dip",                "arms_tri",  ["isolation"],          ["trx","rings"]),
    _ExTemplate("SUSPENSION",       "LUNGE",                         "Suspension Lunge",              "lunge",     ["compound"],           ["trx","rings"]),
    _ExTemplate("SUSPENSION",       "SQUAT",                         "Suspension Squat",              "squat",     ["compound"],           ["trx","rings"]),
    _ExTemplate("SUSPENSION",       "PIKE",                          "Suspension Pike",               "core",      ["core"],               ["trx","rings"]),
    _ExTemplate("SUSPENSION",       "HAMSTRING_CURL",                "Suspension Hamstring Curl",     "hinge",     ["isolation"],          ["trx"]),
    _ExTemplate("SUSPENSION",       "PULL_UP",                       "Suspension Pull-up",            "pull",      ["compound"],           ["rings"]),
    _ExTemplate("SUSPENSION",       "Y_FLY",                         "Suspension Y Fly",              "shoulders", ["isolation"],          ["trx","rings"]),
    # -----------------------------------------------------------------------
    # KETTLEBELL — additional
    # -----------------------------------------------------------------------
    _ExTemplate("CORE",             "TURKISH_GET_UP",                "Turkish Get-Up",                "total_body",["compound"],           ["kettlebell"]),
    _ExTemplate("CORE",             "WINDMILL",                      "Windmill",                      "core",      ["core"],               ["kettlebell","dumbbell"]),
    # -----------------------------------------------------------------------
    # SWISS BALL
    # -----------------------------------------------------------------------
    _ExTemplate("CRUNCH",           "SWISS_BALL_CRUNCH",             "Swiss Ball Crunch",             "core",      ["core"],               ["swiss_ball"]),
    _ExTemplate("PLANK",            "SWISS_BALL_PLANK",              "Swiss Ball Plank",              "core",      ["core"],               ["swiss_ball"]),
    _ExTemplate("LEG_CURL",         "SWISS_BALL_HIP_RAISE_AND_LEG_CURL", "Swiss Ball Hip Raise & Leg Curl", "hinge", ["isolation"],       ["swiss_ball"]),
    _ExTemplate("CORE",             "SWISS_BALL_PIKE",               "Swiss Ball Pike",               "core",      ["core"],               ["swiss_ball"]),
    _ExTemplate("PUSH_UP",          "SWISS_BALL_PUSH_UP",            "Swiss Ball Push-up",            "push",      ["compound"],           ["swiss_ball"]),
    # -----------------------------------------------------------------------
    # BOSU BALL
    # -----------------------------------------------------------------------
    _ExTemplate("SQUAT",            "SPLIT_SQUAT",                   "Split Squat",                   "squat",     ["compound"],           ["bosu_ball", "bodyweight"]),
    _ExTemplate("PLANK",            "PUSH_UP_POSITION_PLANK",        "Push-Up Position Plank",        "core",      ["core"],               ["bosu_ball", "bodyweight"]),
    # -----------------------------------------------------------------------
    # ANKLE WEIGHT
    # -----------------------------------------------------------------------
    _ExTemplate("HIP_RAISE",        "SINGLE_LEG_GLUTE_BRIDGE",       "Single-Leg Glute Bridge",       "hinge",     ["compound"],           ["ankle_weight", "bodyweight"]),
    # -----------------------------------------------------------------------
    # ROPE (climbing rope — LATERAL_RAISE category per Garmin's FIT SDK)
    # -----------------------------------------------------------------------
    _ExTemplate("LATERAL_RAISE",    "ROPE_CLIMB",                    "Rope Climb",                    "pull",      ["compound"],           ["rope"]),
    # -----------------------------------------------------------------------
    # JUMP ROPE (CARDIO category)
    # -----------------------------------------------------------------------
    _ExTemplate("CARDIO",           "JUMP_ROPE",                     "Jump Rope",                     "total_body",["total_body"],         ["jump_rope"]),
    _ExTemplate("CARDIO",           "JUMP_ROPE_JOG",                 "Jump Rope Jog",                 "total_body",["total_body"],         ["jump_rope"]),
    # -----------------------------------------------------------------------
    # FOAM ROLLER
    # -----------------------------------------------------------------------
    _ExTemplate("HIP_RAISE",        "SINGLE_LEG_HIP_RAISE_WITH_FOOT_ON_FOAM_ROLLER", "Hip Raise on Foam Roller", "hinge", ["core"], ["foam_roller"]),
    _ExTemplate("CRUNCH",           "THORACIC_CRUNCHES_ON_FOAM_ROLLER", "Thoracic Crunches on Foam Roller", "core", ["core"],          ["foam_roller"]),
    # SLIDING_DISC exercises removed pending verification of correct Garmin
    # category/name via Exercises.json (category "SLIDING_DISC" is rejected
    # by the Garmin API with "Invalid category").
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
    # Human-readable labels of equipment needed to perform this exercise.
    # Empty list means the exercise can be done with no apparatus (pure bodyweight).
    # When non-empty, the user needs at least one of the listed items.
    required_equipment_labels: list[str] = field(default_factory=list)


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
    available   = _available(equipment) if equipment else _available(["bodyweight"])
    num         = _num_exercises(duration_minutes, goal)
    templates   = _select_exercises(available, num, goal)

    # For timed exercises (plank, etc.), convert reps to duration
    TIMED_EXERCISES = {
        # planks (hold time)
        "PLANK", "SIDE_PLANK", "FOREARM_PLANK", "SWISS_BALL_PLANK", "PUSH_UP_POSITION_PLANK",
        "SUSPENSION_PLANK",
        # carries / drags (timed effort)
        "DEAD_BUG", "FARMERS_WALK", "OVERHEAD_CARRY",
        # battle rope (always timed)
        "ALTERNATING_WAVE", "ALTERNATING_SQUAT_WAVE",
        # jump rope (timed effort)
        "JUMP_ROPE", "JUMP_ROPE_JOG",
        # sled (timed effort) — Garmin names are PUSH, FORWARD_DRAG
        "PUSH", "FORWARD_DRAG",
        # suspension
        "MOUNTAIN_CLIMBER", "PIKE",
    }

    # --- build ExerciseInfo list --------------------------------------------
    _eq_label: dict[str, str] = {eq["tag"]: f"{eq['icon']} {eq['label']}" for eq in EQUIPMENT_OPTIONS}

    exercises: list[ExerciseInfo] = []
    for tmpl in templates:
        is_timed = tmpl.name in TIMED_EXERCISES
        link = get_exercise_link(tmpl.name, tmpl.label)

        if is_timed:
            # Convert reps to hold time: 1 "rep" = 3 seconds, capped at 60s
            hold = min(60.0, reps * 3.0)
            actual_reps = None
        else:
            hold = None
            actual_reps = reps

        # If "bodyweight" is among the equipment tags the exercise can be
        # performed with no apparatus at all; the other tags are optional
        # enhancements. Otherwise the user needs at least one listed item.
        if "bodyweight" in tmpl.equipment:
            req_labels: list[str] = []
        else:
            req_labels = [_eq_label[t] for t in tmpl.equipment if t in _eq_label]

        ex = ExerciseInfo(
            category=tmpl.category,
            name=tmpl.name,
            label=tmpl.label,
            muscle_group=tmpl.muscle_group,
            sets=sets,
            reps=actual_reps,
            duration_sec=hold,
            rest_seconds=rest,
            link=link,
            description="",  # filled below from actual values
            required_equipment_labels=req_labels,
        )
        # Build description from the same values that go into the Garmin step
        if ex.duration_sec is not None:
            ex.description = f"{ex.label} — {int(ex.duration_sec)}s hold | How to: {link}"
        else:
            ex.description = f"{ex.label} — {ex.sets}×{ex.reps} | How to: {link}"
        exercises.append(ex)

    # --- build StrengthWorkout payload --------------------------------------
    date_str = datetime.now().strftime("%b %d")
    workout_name = f"{goal_cfg['label']} — {duration_minutes}min ({date_str})"
    workout_desc = (
        f"{goal_cfg['description']} "
        f"Equipment: {', '.join(equipment) if equipment else 'bodyweight'}."
    )

    blocks = [
        ExerciseBlock(
            category=ex.category,
            name=ex.name,
            sets=ex.sets,
            reps=ex.reps,
            duration_seconds=ex.duration_sec,
            rest_seconds=ex.rest_seconds,
            description=ex.description,
        )
        for ex in exercises
    ]

    builder = (
        StrengthWorkout(workout_name, description=workout_desc)
        .add_warmup(description="5 min general warm-up")
        .add_circuit(blocks, rounds=sets)
        .add_cooldown(description="Cool-down + stretch")
    )
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
