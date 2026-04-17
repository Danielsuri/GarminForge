"""
Instructional video / article links for exercises.

Priority order:
  1. Curated YouTube tutorial (stable, high-quality channel)
  2. YouTube search URL (always resolves, no dead links)

All links open in a new tab in the UI and are embedded in the Garmin
workout step description so they sync to the device notes.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Curated links  (category/name → URL)
# Using well-known, stable channels: Jeff Nippard, Alan Thrall, AthleanX
# ---------------------------------------------------------------------------

_CURATED: dict[str, str] = {
    # BENCH PRESS
    "BARBELL_BENCH_PRESS": "https://www.youtube.com/watch?v=vcBig73ojpE",
    "DUMBBELL_BENCH_PRESS": "https://www.youtube.com/watch?v=VmB1G1K7v94",
    "INCLINE_BARBELL_BENCH_PRESS": "https://www.youtube.com/watch?v=DbFgADa2PL8",
    "INCLINE_DUMBBELL_BENCH_PRESS": "https://www.youtube.com/watch?v=8iPEnn-ltC8",
    "CLOSE_GRIP_BARBELL_BENCH_PRESS": "https://www.youtube.com/watch?v=nEF0bv2FW94",
    # FLYE
    "DUMBBELL_FLYE": "https://www.youtube.com/watch?v=eozdVDA78K0",
    "INCLINE_DUMBBELL_FLYE": "https://www.youtube.com/watch?v=QENKPHhQVi4",
    "CABLE_CROSSOVER": "https://www.youtube.com/watch?v=taI4XduLpTk",
    # PUSH-UP
    "PUSH_UP": "https://www.youtube.com/watch?v=IODxDxX7oi4",
    "DIAMOND_PUSH_UP": "https://www.youtube.com/watch?v=J0DXe9L6tz0",
    # DEADLIFT
    "BARBELL_DEADLIFT": "https://www.youtube.com/watch?v=op9kVnSso6Q",
    "ROMANIAN_DEADLIFT": "https://www.youtube.com/watch?v=2SHsk9AzdjA",
    "SUMO_DEADLIFT": "https://www.youtube.com/watch?v=TomVMUA9rHc",
    "TRAP_BAR_DEADLIFT": "https://www.youtube.com/watch?v=RT0CiHGUm14",
    # SQUAT
    "BARBELL_BACK_SQUAT": "https://www.youtube.com/watch?v=ultWZbUMPL8",
    "BARBELL_FRONT_SQUAT": "https://www.youtube.com/watch?v=m4ytaCJZpl0",
    "GOBLET_SQUAT": "https://www.youtube.com/watch?v=MeIiIdhvXT4",
    "BULGARIAN_SPLIT_SQUAT": "https://www.youtube.com/watch?v=2C-uNgKwPLE",
    "LEG_PRESS": "https://www.youtube.com/watch?v=IZxyjW7MPJQ",
    # LUNGE
    "DUMBBELL_LUNGE": "https://www.youtube.com/watch?v=D7KaRcUTQeE",
    "WALKING_LUNGE": "https://www.youtube.com/watch?v=L8fvypPrzzs",
    "REVERSE_LUNGE": "https://www.youtube.com/watch?v=xrPteyQLGAo",
    # ROW
    "BARBELL_ROW": "https://www.youtube.com/watch?v=G8l_8chR5BE",
    "DUMBBELL_ROW": "https://www.youtube.com/watch?v=roCP6wCXPqo",
    "CABLE_ROW": "https://www.youtube.com/watch?v=GZbfZ033f74",
    "T_BAR_ROW": "https://www.youtube.com/watch?v=j3Igk5nyZE4",
    "SEATED_CABLE_ROW": "https://www.youtube.com/watch?v=GZbfZ033f74",
    "FACE_PULL": "https://www.youtube.com/watch?v=rep-qVOkqgk",
    # PULL-UP
    "PULL_UP": "https://www.youtube.com/watch?v=eGo4IYlbE5g",
    "CHIN_UP": "https://www.youtube.com/watch?v=Q4IzO-iu9mg",
    "LAT_PULLDOWN": "https://www.youtube.com/watch?v=CAwf7n6Luuc",
    "CLOSE_GRIP_LAT_PULLDOWN": "https://www.youtube.com/watch?v=uyL_WbXpUmI",
    # SHOULDER PRESS
    "BARBELL_SHOULDER_PRESS": "https://www.youtube.com/watch?v=2yjwXTZQDDI",
    "DUMBBELL_SHOULDER_PRESS": "https://www.youtube.com/watch?v=qEwKCR5JCog",
    "SEATED_DUMBBELL_SHOULDER_PRESS": "https://www.youtube.com/watch?v=qEwKCR5JCog",
    "ARNOLD_PRESS": "https://www.youtube.com/watch?v=6Z15_WdXmVw",
    "PUSH_PRESS": "https://www.youtube.com/watch?v=iaBVSJm78ko",
    # LATERAL RAISE
    "DUMBBELL_LATERAL_RAISE": "https://www.youtube.com/watch?v=3VcKaXpzqRo",
    "CABLE_LATERAL_RAISE": "https://www.youtube.com/watch?v=PPGUMknb5tE",
    # CURL
    "BARBELL_CURL": "https://www.youtube.com/watch?v=kwG2ipFRgfo",
    "DUMBBELL_CURL": "https://www.youtube.com/watch?v=ykJmrZ5v0Oo",
    "HAMMER_CURL": "https://www.youtube.com/watch?v=zC3nLlEvin4",
    "PREACHER_CURL": "https://www.youtube.com/watch?v=fIWP-FRFNU0",
    "INCLINE_DUMBBELL_CURL": "https://www.youtube.com/watch?v=soxrZlIl35U",
    "EZ_BAR_CURL": "https://www.youtube.com/watch?v=Kcsg_DjQnFE",
    # TRICEPS
    "TRICEPS_PUSHDOWN": "https://www.youtube.com/watch?v=2-LAMcpzODU",
    "SKULL_CRUSHER": "https://www.youtube.com/watch?v=d_KZxkY_0cM",
    "OVERHEAD_DUMBBELL_TRICEPS_EXTENSION": "https://www.youtube.com/watch?v=YbX7Wd8jQ-Q",
    "TRICEPS_DIP": "https://www.youtube.com/watch?v=6kALZikXxLc",
    # HIP RAISE / GLUTES
    "BARBELL_HIP_THRUST": "https://www.youtube.com/watch?v=SEdqd1n0cvg",
    "DUMBBELL_HIP_THRUST": "https://www.youtube.com/watch?v=dmEajKqGVKk",
    "GLUTE_BRIDGE": "https://www.youtube.com/watch?v=wPM8icPu6H8",
    "SINGLE_LEG_GLUTE_BRIDGE": "https://www.youtube.com/watch?v=gPio-PYMGug",
    # LEG CURL
    "LYING_LEG_CURL": "https://www.youtube.com/watch?v=1Tq3QdYUuHs",
    "SEATED_LEG_CURL": "https://www.youtube.com/watch?v=ELOCsoDSmrg",
    "NORDIC_HAMSTRING_CURL": "https://www.youtube.com/watch?v=F4eRNSSmFb4",
    "GOOD_MORNING": "https://www.youtube.com/watch?v=YA-h3n9L4YU",
    # CALF
    "STANDING_CALF_RAISE": "https://www.youtube.com/watch?v=-M4-G8p1fCI",
    "SEATED_CALF_RAISE": "https://www.youtube.com/watch?v=JbyjNymZOt0",
    # SHRUG
    "BARBELL_SHRUG": "https://www.youtube.com/watch?v=g6qbq4Lf1FI",
    "DUMBBELL_SHRUG": "https://www.youtube.com/watch?v=cJRVVxmytaM",
    # CORE
    "PLANK": "https://www.youtube.com/watch?v=ASdvN_XEl_c",
    "SIDE_PLANK": "https://www.youtube.com/watch?v=K1NnAOTLMWk",
    "CRUNCH": "https://www.youtube.com/watch?v=Xyd_fa5zoEU",
    "BICYCLE_CRUNCH": "https://www.youtube.com/watch?v=9FGilxCbdz8",
    "REVERSE_CRUNCH": "https://www.youtube.com/watch?v=hyv13_8k74Y",
    "LYING_LEG_RAISE": "https://www.youtube.com/watch?v=l4kQd9eWclE",
    "HANGING_LEG_RAISE": "https://www.youtube.com/watch?v=hdng3Nm1x_E",
    "DEAD_BUG": "https://www.youtube.com/watch?v=4XLEnwUr1d8",
    "RUSSIAN_TWIST": "https://www.youtube.com/watch?v=JyUqwkVpsi8",
    "AB_WHEEL_ROLLOUT": "https://www.youtube.com/watch?v=VLxR4_LF19Q",
    # BACK EXTENSION
    "BACK_EXTENSION": "https://www.youtube.com/watch?v=ph3pddpKzzw",
    # OLYMPIC
    "POWER_CLEAN": "https://www.youtube.com/watch?v=RiN4_ZCFsBs",
    "CLEAN": "https://www.youtube.com/watch?v=RiN4_ZCFsBs",
    "KETTLEBELL_SWING": "https://www.youtube.com/watch?v=YSxHifyI6s8",
    # TOTAL BODY
    "BURPEE": "https://www.youtube.com/watch?v=818_qY0cYss",
    "BOX_JUMP": "https://www.youtube.com/watch?v=52r_Ul5k03g",
}


def get_exercise_link(exercise_name: str, label: str = "") -> str:
    """Return the best available instructional URL for an exercise.

    Falls back to a YouTube search URL if no curated link exists.

    Parameters
    ----------
    exercise_name:
        ALL_CAPS_SNAKE_CASE exercise name, e.g. ``"BARBELL_BENCH_PRESS"``.
    label:
        Human-readable label used as the YouTube search query fallback.
    """
    name = exercise_name.upper()
    if name in _CURATED:
        return _CURATED[name]

    # Fallback: YouTube search
    query = (label or name.replace("_", " ").title()).replace(" ", "+")
    return f"https://www.youtube.com/results?search_query=how+to+{query}"


def get_short_link(exercise_name: str, label: str = "") -> str:
    """Return a short URL suitable for embedding in a Garmin step description.

    Garmin step descriptions are freeform text; we keep it brief.
    """
    url = get_exercise_link(exercise_name, label)
    return url
