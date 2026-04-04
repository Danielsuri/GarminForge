"""
Translation strings for GarminForge UI.

``t(key, lang, **kwargs)`` is the public helper used by rendering.py to inject
a bound ``t`` function into every Jinja2 template context.

Lookup order: TRANSLATIONS[lang][key]  →  TRANSLATIONS["en"][key]  →  key itself.
"""
from __future__ import annotations

from collections.abc import Callable

SUPPORTED_LANGS: frozenset[str] = frozenset({"en", "he"})

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # --- Navbar ---
        "nav_my_plans":            "My Plans",
        "nav_progress":            "Progress",
        "nav_logout":              "Log out",
        "nav_sign_in":             "Sign In",
        "nav_register":            "Register",
        "nav_garmin_connected":    "Garmin Connected",
        "nav_garmin_not_connected": "Garmin not connected",

        # --- Generator form ---
        "form_build_workout":      "Build Your Workout",
        "form_workout_goal":       "Workout Goal",
        "form_available_equipment": "Available Equipment",
        "form_session_duration":   "Session Duration",
        "form_generate_btn":       "Generate Workout",
        "form_regenerate_btn":     "Regenerate",
        "form_equipment_hint":     "Select all you have. Leave empty for bodyweight-only exercises.",
        "form_placeholder_title":  "Your workout will appear here",
        "form_placeholder_body":   "Fill in the options on the left and click Generate Workout.",
        "form_generating":         "Generating\u2026",
        "form_generate_failed":    "Generation failed. Please try again.",
        "form_min":                "min",

        # --- Workout preview ---
        "preview_exercises":       "Exercises",
        "preview_sets_each":       "Sets each",
        "preview_reps_per_set":    "Reps / set",
        "preview_warmup_label":    "5 min general warm-up",
        "preview_cooldown_label":  "Cool-down + stretch",
        "preview_tutorial":        "Tutorial",
        "preview_reps":            "reps",
        "preview_hold":            "s hold",
        "preview_rest":            "s rest",
        "preview_needs":           "Needs:",
        "preview_circuit_desc_pre":  "do all ",
        "preview_circuit_desc_post": " exercises, then repeat",
        "preview_round_footer_pre":  "Rest 90s, then repeat from exercise 1 \u2014 ",
        "preview_round_footer_post": " rounds total",
        "preview_rounds_badge":    "\u00d7 {n} rounds",
        "preview_save_plans":      "Save to My Plans",
        "preview_saved":           "Saved!",
        "preview_saving":          "Saving\u2026",
        "preview_save_failed":     "Save failed. Please try again.",
        "preview_upload_garmin":   "Upload to Garmin Connect",
        "preview_uploading":       "Uploading\u2026",
        "preview_schedule_label":  "Schedule on Garmin (optional)",
        "preview_schedule_hint":   "Leave blank to save as an unscheduled workout.",
        "preview_connect_prompt":  "Connect your Garmin account to upload this workout.",
        "preview_connect_btn":     "Connect Garmin Account",
        "preview_selected_suffix": " selected",
        "preview_no_equipment":    "No equipment",

        # --- Badges ---
        "badge_warmup":   "WARM-UP",
        "badge_cooldown": "COOL-DOWN",
        "badge_circuit":  "CIRCUIT",

        # --- Goal labels ---
        "goal_label_burn_fat":       "Burn Fat",
        "goal_label_lose_weight":    "Lose Weight",
        "goal_label_build_muscle":   "Build Muscle",
        "goal_label_build_strength": "Build Strength",
        "goal_label_general_fitness": "General Fitness",
        "goal_label_endurance":      "Muscular Endurance",

        # --- Goal descriptions ---
        "goal_desc_burn_fat":       "High reps, short rest, maximum calorie burn.",
        "goal_desc_lose_weight":    "Moderate reps, moderate rest, balanced intensity.",
        "goal_desc_build_muscle":   "Hypertrophy rep range, full rest between sets.",
        "goal_desc_build_strength": "Heavy compound lifts, maximal strength adaptation.",
        "goal_desc_general_fitness": "Well-rounded training for overall health.",
        "goal_desc_endurance":      "High reps, minimal rest, endurance adaptation.",

        # --- Equipment labels ---
        "eq_bodyweight":    "No Equipment",
        "eq_barbell":       "Barbell",
        "eq_dumbbell":      "Dumbbells",
        "eq_kettlebell":    "Kettlebell",
        "eq_cable":         "Cable Machine",
        "eq_machine":       "Weight Machines",
        "eq_band":          "Resistance Bands",
        "eq_pullup_bar":    "Pull-up Bar",
        "eq_bench":         "Bench",
        "eq_medicine_ball": "Medicine Ball",
        "eq_ez_bar":        "EZ Bar",
        "eq_plate":         "Weight Plate",
        "eq_box":           "Box / Step",
        "eq_swiss_ball":    "Swiss Ball",
        "eq_trx":           "TRX / Suspension",
        "eq_sandbag":       "Sandbag",
        "eq_battle_rope":   "Battle Rope",
        "eq_sled":          "Sled",
        "eq_rings":         "Gymnastic Rings",
        "eq_smith_machine": "Smith Machine",
        "eq_weight_vest":   "Weight Vest",
        "eq_bosu_ball":     "Bosu Ball",
        "eq_ankle_weight":  "Ankle Weights",
        "eq_sliding_disc":  "Sliding Discs",
        "eq_ab_wheel":      "Ab Wheel",
        "eq_rope":          "Climbing Rope",
        "eq_jump_rope":     "Jump Rope",
        "eq_foam_roller":   "Foam Roller",

        # --- Muscle group labels ---
        "muscle_push":       "push",
        "muscle_pull":       "pull",
        "muscle_squat":      "squat",
        "muscle_hinge":      "hinge",
        "muscle_lunge":      "lunge",
        "muscle_core":       "core",
        "muscle_arms_bi":    "arms bi",
        "muscle_arms_tri":   "arms tri",
        "muscle_shoulders":  "shoulders",
        "muscle_total_body": "total body",
        "muscle_calves":     "calves",

        # --- My Plans ---
        "plans_title":        "My Plans",
        "plans_generate_new": "Generate New",
        "plans_saved":        "Saved",
        "plans_preview":      "Preview",
        "plans_no_plans":     "No saved plans yet",
        "plans_no_plans_desc": "Generate a workout and click Save to My Plans to save it here.",
        "plans_generate_btn": "Generate a Workout",
        "plans_delete_confirm": "Delete this plan?",
        "plans_delete_error":   "Could not delete plan. Please try again.",

        # --- My Progress ---
        "progress_title":       "My Progress",
        "progress_sessions":    "Sessions",
        "progress_completed":   "Completed",
        "progress_finish_rate": "Finish Rate",
        "progress_total_min":   "Total Min",
        "progress_workout":     "Workout",
        "progress_date":        "Date",
        "progress_duration":    "Duration",
        "progress_progress":    "Progress",
        "progress_status":      "Status",
        "progress_done":        "Done",
        "progress_in_progress": "In progress",
        "progress_no_sessions": "No sessions logged yet",
        "progress_no_sessions_desc": "Complete a workout in the player and your history will appear here.",
        "progress_generate_btn": "Generate a Workout",

        # --- Auth ---
        "auth_tagline":         "Generate personalised strength workouts and send them directly to Garmin Connect.",
        "auth_sign_in_heading": "Sign In",
        "auth_register_heading": "Create Account",
        "auth_register_sub":    "Save workouts and track your progress.",
        "auth_or_email":        "or sign in with email",
        "auth_or_signup_email": "or sign up with email",
        "auth_email":           "Email",
        "auth_password":        "Password",
        "auth_name":            "Name",
        "auth_optional":        "(optional)",
        "auth_min_chars":       "(min 8 chars)",
        "auth_sign_in_btn":     "Sign In",
        "auth_create_btn":      "Create Account",
        "auth_signing_in":      "Signing in\u2026",
        "auth_creating":        "Creating\u2026",
        "auth_new_here":        "New here?",
        "auth_create_free":     "Create a free account",
        "auth_have_account":    "Already have an account?",
        "auth_sign_in_link":    "Sign in",

        # --- Workout editor ---
        "edit_drag_to_reorder":   "Drag to reorder",
        "edit_replace":           "Replace",
        "edit_remove":            "Remove",
        "edit_add_exercise":      "Add Exercise",
        "edit_replace_title":     "Replace Exercise",
        "edit_add_title":         "Add Exercise",
        "edit_all_muscles":       "All",
        "edit_no_alternatives":   "No alternatives available for current equipment.",
        "edit_rebuilding":        "Saving changes\u2026",
        "edit_rebuild_failed":    "Failed to update workout. Please try again.",
        "edit_toast_removed":     "Exercise removed",
        "edit_toast_replaced":    "Exercise replaced",
        "edit_toast_added":       "Exercise added",
        "edit_toast_reordered":   "Order updated",

        # --- Footer ---
        "footer_text": "unofficial Garmin Connect workout tool",
    },

    "he": {
        # --- Navbar ---
        "nav_my_plans":            "\u05d4\u05ea\u05d5\u05db\u05e0\u05d9\u05d5\u05ea \u05e9\u05dc\u05d9",
        "nav_progress":            "\u05d4\u05ea\u05e7\u05d3\u05de\u05d5\u05ea",
        "nav_logout":              "\u05d4\u05ea\u05e0\u05ea\u05e7\u05d5\u05ea",
        "nav_sign_in":             "\u05db\u05e0\u05d9\u05e1\u05d4",
        "nav_register":            "\u05d4\u05e8\u05e9\u05de\u05d4",
        "nav_garmin_connected":    "Garmin \u05de\u05d7\u05d5\u05d1\u05e8",
        "nav_garmin_not_connected": "Garmin \u05dc\u05d0 \u05de\u05d7\u05d5\u05d1\u05e8",

        # --- Generator form ---
        "form_build_workout":      "\u05d1\u05e0\u05d4 \u05d0\u05d9\u05de\u05d5\u05df",
        "form_workout_goal":       "\u05de\u05d8\u05e8\u05ea \u05d4\u05d0\u05d9\u05de\u05d5\u05df",
        "form_available_equipment": "\u05e6\u05d9\u05d5\u05d3 \u05d6\u05de\u05d9\u05df",
        "form_session_duration":   "\u05de\u05e9\u05da \u05d4\u05d0\u05d9\u05de\u05d5\u05df",
        "form_generate_btn":       "\u05e6\u05d5\u05e8 \u05d0\u05d9\u05de\u05d5\u05df",
        "form_regenerate_btn":     "\u05e6\u05d5\u05e8 \u05de\u05d7\u05d3\u05e9",
        "form_equipment_hint":     "\u05d1\u05d7\u05e8 \u05d0\u05ea \u05db\u05dc \u05d4\u05e6\u05d9\u05d5\u05d3 \u05e9\u05d9\u05e9 \u05dc\u05da. \u05d4\u05e9\u05d0\u05e8 \u05e8\u05d9\u05e7 \u05dc\u05ea\u05e8\u05d2\u05d9\u05dc\u05d9 \u05de\u05e9\u05e7\u05dc \u05d2\u05d5\u05e3 \u05d1\u05dc\u05d1\u05d3.",
        "form_placeholder_title":  "\u05d4\u05d0\u05d9\u05de\u05d5\u05df \u05e9\u05dc\u05da \u05d9\u05d5\u05e4\u05d9\u05e2 \u05db\u05d0\u05df",
        "form_placeholder_body":   "\u05de\u05dc\u05d0 \u05d0\u05ea \u05d4\u05d0\u05e4\u05e9\u05e8\u05d5\u05d9\u05d5\u05ea \u05d5\u05dc\u05d7\u05e5 \u05e2\u05dc \u05e6\u05d5\u05e8 \u05d0\u05d9\u05de\u05d5\u05df.",
        "form_generating":         "\u05de\u05d9\u05d9\u05e6\u05e8\u2026",
        "form_generate_failed":    "\u05d4\u05d9\u05d9\u05e6\u05d5\u05e8 \u05e0\u05db\u05e9\u05dc. \u05e0\u05e1\u05d4 \u05e9\u05d5\u05d1.",
        "form_min":                "\u05d3\u05e7\u05d5\u05ea",

        # --- Workout preview ---
        "preview_exercises":       "\u05ea\u05e8\u05d2\u05d9\u05dc\u05d9\u05dd",
        "preview_sets_each":       "\u05e1\u05d8\u05d9\u05dd \u05dc\u05ea\u05e8\u05d2\u05d9\u05dc",
        "preview_reps_per_set":    "\u05d7\u05d6\u05e8\u05d5\u05ea \u05dc\u05e1\u05d8",
        "preview_warmup_label":    "5 \u05d3\u05e7\u05d5\u05ea \u05d7\u05d9\u05de\u05d5\u05dd \u05db\u05dc\u05dc\u05d9",
        "preview_cooldown_label":  "\u05e6\u05d9\u05e0\u05d5\u05df + \u05de\u05ea\u05d9\u05d7\u05d5\u05ea",
        "preview_tutorial":        "\u05d4\u05d3\u05e8\u05db\u05d4",
        "preview_reps":            "\u05d7\u05d6\u05e8\u05d5\u05ea",
        "preview_hold":            "\u05e9\u05e0\u05d9\u05d5\u05ea",
        "preview_rest":            "\u05e9\u05e0\u05d9\u05d5\u05ea \u05de\u05e0\u05d5\u05d7\u05d4",
        "preview_needs":           "\u05d3\u05e8\u05d5\u05e9:",
        "preview_circuit_desc_pre":  "\u05d1\u05e6\u05e2 \u05d0\u05ea \u05db\u05dc ",
        "preview_circuit_desc_post": " \u05d4\u05ea\u05e8\u05d2\u05d9\u05dc\u05d9\u05dd, \u05d5\u05d0\u05d6 \u05d7\u05d6\u05d5\u05e8",
        "preview_round_footer_pre":  "\u05de\u05e0\u05d5\u05d7\u05d4 90 \u05e9\u05e0\u05d9\u05d5\u05ea, \u05d5\u05d0\u05d6 \u05d7\u05d6\u05d5\u05e8 \u05dc\u05ea\u05e8\u05d2\u05d9\u05dc 1 \u2014 ",
        "preview_round_footer_post": " \u05e1\u05d9\u05d1\u05d5\u05d1\u05d9\u05dd \u05e1\u05da \u05d4\u05db\u05dc",
        "preview_rounds_badge":    "\u00d7 {n} \u05e1\u05d9\u05d1\u05d5\u05d1\u05d9\u05dd",
        "preview_save_plans":      "\u05e9\u05de\u05d5\u05e8 \u05dc\u05ea\u05d5\u05db\u05e0\u05d9\u05d5\u05ea \u05e9\u05dc\u05d9",
        "preview_saved":           "\u05e0\u05e9\u05de\u05e8!",
        "preview_saving":          "\u05e9\u05d5\u05de\u05e8\u2026",
        "preview_save_failed":     "\u05d4\u05e9\u05de\u05d9\u05e8\u05d4 \u05e0\u05db\u05e9\u05dc\u05d4. \u05e0\u05e1\u05d4 \u05e9\u05d5\u05d1.",
        "preview_upload_garmin":   "\u05d4\u05e2\u05dc\u05d4 \u05dc-Garmin Connect",
        "preview_uploading":       "\u05de\u05e2\u05dc\u05d4\u2026",
        "preview_schedule_label":  "\u05ea\u05d6\u05de\u05df \u05d1-Garmin (\u05d0\u05d5\u05e4\u05e6\u05d9\u05d5\u05e0\u05dc\u05d9)",
        "preview_schedule_hint":   "\u05d4\u05e9\u05d0\u05e8 \u05e8\u05d9\u05e7 \u05dc\u05e9\u05de\u05d9\u05e8\u05d4 \u05db\u05d0\u05d9\u05de\u05d5\u05df \u05dc\u05dc\u05d0 \u05ea\u05d6\u05de\u05d5\u05df.",
        "preview_connect_prompt":  "\u05d7\u05d1\u05e8 \u05d0\u05ea \u05d7\u05e9\u05d1\u05d5\u05df Garmin \u05e9\u05dc\u05da \u05dc\u05d4\u05e2\u05dc\u05d0\u05ea \u05d4\u05d0\u05d9\u05de\u05d5\u05df.",
        "preview_connect_btn":     "\u05d7\u05d1\u05e8 \u05d7\u05e9\u05d1\u05d5\u05df Garmin",
        "preview_selected_suffix": " \u05e0\u05d1\u05d7\u05e8\u05d5",
        "preview_no_equipment":    "\u05dc\u05dc\u05d0 \u05e6\u05d9\u05d5\u05d3",

        # --- Badges ---
        "badge_warmup":   "\u05d7\u05d9\u05de\u05d5\u05dd",
        "badge_cooldown": "\u05e6\u05d9\u05e0\u05d5\u05df",
        "badge_circuit":  "\u05de\u05e2\u05d2\u05dc",

        # --- Goal labels ---
        "goal_label_burn_fat":       "\u05e9\u05e8\u05d9\u05e4\u05ea \u05e9\u05d5\u05de\u05df",
        "goal_label_lose_weight":    "\u05d9\u05e8\u05d9\u05d3\u05d4 \u05d1\u05de\u05e9\u05e7\u05dc",
        "goal_label_build_muscle":   "\u05d1\u05e0\u05d9\u05d9\u05ea \u05e9\u05e8\u05d9\u05e8",
        "goal_label_build_strength": "\u05d1\u05e0\u05d9\u05d9\u05ea \u05db\u05d5\u05d7",
        "goal_label_general_fitness": "\u05db\u05d5\u05e9\u05e8 \u05db\u05dc\u05dc\u05d9",
        "goal_label_endurance":      "\u05e1\u05d9\u05d1\u05d5\u05dc\u05ea \u05e9\u05e8\u05d9\u05e8\u05d9\u05dd",

        # --- Goal descriptions ---
        "goal_desc_burn_fat":       "\u05d7\u05d6\u05e8\u05d5\u05ea \u05e8\u05d1\u05d5\u05ea, \u05de\u05e0\u05d5\u05d7\u05d4 \u05e7\u05e6\u05e8\u05d4, \u05e9\u05e8\u05d9\u05e4\u05ea \u05e7\u05dc\u05d5\u05e8\u05d9\u05d5\u05ea \u05de\u05e7\u05e1\u05d9\u05de\u05dc\u05d9\u05ea.",
        "goal_desc_lose_weight":    "\u05d7\u05d6\u05e8\u05d5\u05ea \u05d1\u05d9\u05e0\u05d5\u05e0\u05d9\u05d5\u05ea, \u05de\u05e0\u05d5\u05d7\u05d4 \u05d1\u05d9\u05e0\u05d5\u05e0\u05d9\u05ea, \u05e2\u05e6\u05d9\u05de\u05d5\u05ea \u05de\u05d0\u05d5\u05d6\u05e0\u05ea.",
        "goal_desc_build_muscle":   "\u05d8\u05d5\u05d5\u05d7 \u05d7\u05d6\u05e8\u05d5\u05ea \u05dc\u05d4\u05d9\u05e4\u05e8\u05d8\u05e8\u05d5\u05e4\u05d9\u05d4, \u05de\u05e0\u05d5\u05d7\u05d4 \u05de\u05dc\u05d0\u05d4 \u05d1\u05d9\u05df \u05e1\u05d8\u05d9\u05dd.",
        "goal_desc_build_strength": "\u05d4\u05e8\u05de\u05d5\u05ea \u05de\u05d5\u05e8\u05db\u05d1\u05d5\u05ea \u05db\u05d1\u05d3\u05d5\u05ea, \u05d4\u05e1\u05ea\u05d2\u05dc\u05d5\u05ea \u05dc\u05db\u05d5\u05d7 \u05de\u05e7\u05e1\u05d9\u05de\u05dc\u05d9.",
        "goal_desc_general_fitness": "\u05d0\u05d9\u05de\u05d5\u05df \u05de\u05d2\u05d5\u05d5\u05df \u05dc\u05d1\u05e8\u05d9\u05d0\u05d5\u05ea \u05db\u05dc\u05dc\u05d9\u05ea.",
        "goal_desc_endurance":      "\u05d7\u05d6\u05e8\u05d5\u05ea \u05e8\u05d1\u05d5\u05ea, \u05de\u05e0\u05d5\u05d7\u05d4 \u05de\u05d9\u05e0\u05d9\u05de\u05dc\u05d9\u05ea, \u05e1\u05d9\u05d1\u05d5\u05dc\u05ea \u05e9\u05e8\u05d9\u05e8\u05d9\u05dd.",

        # --- Equipment labels ---
        "eq_bodyweight":    "\u05dc\u05dc\u05d0 \u05e6\u05d9\u05d5\u05d3",
        "eq_barbell":       "\u05de\u05d5\u05d8 \u05d9\u05e9\u05e8",
        "eq_dumbbell":      "\u05de\u05e9\u05e7\u05d5\u05dc\u05d5\u05ea \u05d9\u05d3",
        "eq_kettlebell":    "\u05e7\u05d8\u05dc\u05d1\u05dc",
        "eq_cable":         "\u05de\u05db\u05d5\u05e0\u05ea \u05db\u05d1\u05dc",
        "eq_machine":       "\u05de\u05db\u05d5\u05e0\u05d5\u05ea \u05de\u05e9\u05e7\u05dc",
        "eq_band":          "\u05d2\u05d5\u05de\u05d9\u05d5\u05ea \u05d4\u05ea\u05e0\u05d2\u05d3\u05d5\u05ea",
        "eq_pullup_bar":    "\u05de\u05ea\u05d7",
        "eq_bench":         "\u05e1\u05e4\u05e1\u05dc",
        "eq_medicine_ball": "\u05db\u05d3\u05d5\u05e8 \u05db\u05d5\u05d7",
        "eq_ez_bar":        "\u05de\u05d5\u05d8 EZ",
        "eq_plate":         "\u05d3\u05d9\u05e1\u05e7",
        "eq_box":           "\u05e7\u05d5\u05e4\u05e1\u05d0 / \u05de\u05d3\u05e8\u05d2\u05d4",
        "eq_swiss_ball":    "\u05db\u05d3\u05d5\u05e8 \u05e9\u05d5\u05d5\u05d9\u05e6\u05e8\u05d9",
        "eq_trx":           "TRX / \u05ea\u05dc\u05d9\u05d9\u05d4",
        "eq_sandbag":       "\u05e9\u05e7 \u05d7\u05d5\u05dc",
        "eq_battle_rope":   "\u05d7\u05d1\u05dc \u05e7\u05e8\u05d1",
        "eq_sled":          "\u05de\u05d6\u05d7\u05dc\u05ea\u05d4",
        "eq_rings":         "\u05d8\u05d1\u05e2\u05d5\u05ea \u05d4\u05ea\u05e2\u05de\u05dc\u05d5\u05ea",
        "eq_smith_machine": "\u05de\u05db\u05d5\u05e0\u05ea \u05e1\u05de\u05d9\u05ea'",
        "eq_weight_vest":   "\u05d0\u05e4\u05d5\u05d3 \u05de\u05e9\u05e7\u05dc",
        "eq_bosu_ball":     "\u05db\u05d3\u05d5\u05e8 \u05d1\u05d5\u05e1\u05d5",
        "eq_ankle_weight":  "\u05de\u05e9\u05e7\u05d5\u05dc\u05d5\u05ea \u05e7\u05e8\u05e1\u05d5\u05dc",
        "eq_sliding_disc":  "\u05d3\u05d9\u05e1\u05e7\u05d9\u05d5\u05ea \u05d4\u05d7\u05dc\u05e7\u05d4",
        "eq_ab_wheel":      "\u05d2\u05dc\u05d2\u05dc \u05d1\u05d8\u05df",
        "eq_rope":          "\u05d7\u05d1\u05dc \u05d8\u05d9\u05e4\u05d5\u05e1",
        "eq_jump_rope":     "\u05d7\u05d1\u05dc \u05e7\u05e4\u05d9\u05e6\u05d4",
        "eq_foam_roller":   "\u05d2\u05dc\u05d9\u05dc \u05e4\u05d5\u05dd",

        # --- Muscle group labels ---
        "muscle_push":       "\u05d3\u05d7\u05d9\u05e4\u05d4",
        "muscle_pull":       "\u05de\u05e9\u05d9\u05db\u05d4",
        "muscle_squat":      "\u05e1\u05e7\u05d5\u05d5\u05d0\u05d8",
        "muscle_hinge":      "\u05e6\u05d9\u05e8",
        "muscle_lunge":      "\u05dc\u05d0\u05e0\u05d2'",
        "muscle_core":       "\u05dc\u05d9\u05d1\u05d4",
        "muscle_arms_bi":    "\u05d1\u05d9\u05e6\u05e4\u05e1",
        "muscle_arms_tri":   "\u05d8\u05e8\u05d9\u05e6\u05e4\u05e1",
        "muscle_shoulders":  "\u05db\u05ea\u05e4\u05d9\u05d9\u05dd",
        "muscle_total_body": "\u05db\u05dc \u05d4\u05d2\u05d5\u05e3",
        "muscle_calves":     "\u05e9\u05d5\u05e7\u05d9\u05d9\u05dd",

        # --- My Plans ---
        "plans_title":        "\u05d4\u05ea\u05d5\u05db\u05e0\u05d9\u05d5\u05ea \u05e9\u05dc\u05d9",
        "plans_generate_new": "\u05e6\u05d5\u05e8 \u05d7\u05d3\u05e9",
        "plans_saved":        "\u05e0\u05e9\u05de\u05e8",
        "plans_preview":      "\u05ea\u05e6\u05d5\u05d2\u05d4 \u05de\u05e7\u05d3\u05d9\u05de\u05d4",
        "plans_no_plans":     "\u05d0\u05d9\u05df \u05ea\u05d5\u05db\u05e0\u05d9\u05d5\u05ea \u05e9\u05de\u05d5\u05e8\u05d5\u05ea \u05e2\u05d3\u05d9\u05d9\u05df",
        "plans_no_plans_desc": "\u05e6\u05d5\u05e8 \u05d0\u05d9\u05de\u05d5\u05df \u05d5\u05dc\u05d7\u05e5 \u05e2\u05dc \u05e9\u05de\u05d5\u05e8 \u05dc\u05ea\u05d5\u05db\u05e0\u05d9\u05d5\u05ea \u05e9\u05dc\u05d9 \u05db\u05d3\u05d9 \u05dc\u05e9\u05de\u05d5\u05e8 \u05d0\u05d5\u05ea\u05d5 \u05db\u05d0\u05df.",
        "plans_generate_btn": "\u05e6\u05d5\u05e8 \u05d0\u05d9\u05de\u05d5\u05df",
        "plans_delete_confirm": "\u05dc\u05de\u05d7\u05d5\u05e7 \u05ea\u05d5\u05db\u05e0\u05d9\u05ea \u05d6\u05d5?",
        "plans_delete_error":   "\u05dc\u05d0 \u05e0\u05d9\u05ea\u05df \u05dc\u05de\u05d7\u05d5\u05e7 \u05ea\u05d5\u05db\u05e0\u05d9\u05ea. \u05e0\u05e1\u05d4 \u05e9\u05d5\u05d1.",

        # --- My Progress ---
        "progress_title":       "\u05d4\u05d4\u05ea\u05e7\u05d3\u05de\u05d5\u05ea \u05e9\u05dc\u05d9",
        "progress_sessions":    "\u05d0\u05d9\u05de\u05d5\u05e0\u05d9\u05dd",
        "progress_completed":   "\u05d4\u05d5\u05e9\u05dc\u05de\u05d5",
        "progress_finish_rate": "\u05d0\u05d7\u05d5\u05d6 \u05d4\u05e9\u05dc\u05de\u05d4",
        "progress_total_min":   "\u05e1\u05d4\"\u05db \u05d3\u05e7\u05d5\u05ea",
        "progress_workout":     "\u05d0\u05d9\u05de\u05d5\u05df",
        "progress_date":        "\u05ea\u05d0\u05e8\u05d9\u05da",
        "progress_duration":    "\u05de\u05e9\u05da",
        "progress_progress":    "\u05d4\u05ea\u05e7\u05d3\u05de\u05d5\u05ea",
        "progress_status":      "\u05e1\u05d8\u05d0\u05d8\u05d5\u05e1",
        "progress_done":        "\u05d4\u05d5\u05e9\u05dc\u05dd",
        "progress_in_progress": "\u05d1\u05ea\u05d4\u05dc\u05d9\u05da",
        "progress_no_sessions": "\u05d0\u05d9\u05df \u05d0\u05d9\u05de\u05d5\u05e0\u05d9\u05dd \u05de\u05ea\u05d5\u05e2\u05d3\u05d9\u05dd \u05e2\u05d3\u05d9\u05d9\u05df",
        "progress_no_sessions_desc": "\u05d4\u05e9\u05dc\u05dd \u05d0\u05d9\u05de\u05d5\u05df \u05d5\u05d4\u05d4\u05d9\u05e1\u05d8\u05d5\u05e8\u05d9\u05d4 \u05e9\u05dc\u05da \u05ea\u05d5\u05e4\u05d9\u05e2 \u05db\u05d0\u05df.",
        "progress_generate_btn": "\u05e6\u05d5\u05e8 \u05d0\u05d9\u05de\u05d5\u05df",

        # --- Auth ---
        "auth_tagline":         "\u05e6\u05d5\u05e8 \u05d0\u05d9\u05de\u05d5\u05e0\u05d9 \u05db\u05d5\u05d7 \u05de\u05d5\u05ea\u05d0\u05de\u05d9\u05dd \u05d0\u05d9\u05e9\u05d9\u05ea \u05d5\u05e9\u05dc\u05d7 \u05d0\u05d5\u05ea\u05dd \u05d9\u05e9\u05d9\u05e8\u05d5\u05ea \u05dc-Garmin Connect.",
        "auth_sign_in_heading": "\u05db\u05e0\u05d9\u05e1\u05d4",
        "auth_register_heading": "\u05d9\u05e6\u05d9\u05e8\u05ea \u05d7\u05e9\u05d1\u05d5\u05df",
        "auth_register_sub":    "\u05e9\u05de\u05d5\u05e8 \u05d0\u05d9\u05de\u05d5\u05e0\u05d9\u05dd \u05d5\u05e2\u05e7\u05d5\u05d1 \u05d0\u05d7\u05e8 \u05d4\u05ea\u05e7\u05d3\u05de\u05d5\u05ea\u05da.",
        "auth_or_email":        "\u05d0\u05d5 \u05db\u05e0\u05d9\u05e1\u05d4 \u05e2\u05dd \u05d0\u05d9\u05de\u05d9\u05d9\u05dc",
        "auth_or_signup_email": "\u05d0\u05d5 \u05d4\u05e8\u05e9\u05de\u05d4 \u05e2\u05dd \u05d0\u05d9\u05de\u05d9\u05d9\u05dc",
        "auth_email":           "\u05d0\u05d9\u05de\u05d9\u05d9\u05dc",
        "auth_password":        "\u05e1\u05d9\u05e1\u05de\u05d4",
        "auth_name":            "\u05e9\u05dd",
        "auth_optional":        "(\u05d0\u05d5\u05e4\u05e6\u05d9\u05d5\u05e0\u05dc\u05d9)",
        "auth_min_chars":       "(\u05de\u05d9\u05e0' 8 \u05ea\u05d5\u05d5\u05d9\u05dd)",
        "auth_sign_in_btn":     "\u05db\u05e0\u05d9\u05e1\u05d4",
        "auth_create_btn":      "\u05d9\u05e6\u05d9\u05e8\u05ea \u05d7\u05e9\u05d1\u05d5\u05df",
        "auth_signing_in":      "\u05de\u05ea\u05d7\u05d1\u05e8\u2026",
        "auth_creating":        "\u05d9\u05d5\u05e6\u05e8\u2026",
        "auth_new_here":        "\u05d7\u05d3\u05e9 \u05db\u05d0\u05df?",
        "auth_create_free":     "\u05e6\u05d5\u05e8 \u05d7\u05e9\u05d1\u05d5\u05df \u05d7\u05d9\u05e0\u05dd",
        "auth_have_account":    "\u05db\u05d1\u05e8 \u05d9\u05e9 \u05dc\u05da \u05d7\u05e9\u05d1\u05d5\u05df?",
        "auth_sign_in_link":    "\u05db\u05e0\u05d9\u05e1\u05d4",

        # --- Workout editor ---
        "edit_drag_to_reorder":   "\u05d2\u05e8\u05d5\u05e8 \u05dc\u05e1\u05d9\u05d3\u05d5\u05e8 \u05de\u05d7\u05d3\u05e9",
        "edit_replace":           "\u05d4\u05d7\u05dc\u05e4\u05d4",
        "edit_remove":            "\u05d4\u05e1\u05e8\u05d4",
        "edit_add_exercise":      "\u05d4\u05d5\u05e1\u05e3 \u05ea\u05e8\u05d2\u05d9\u05dc",
        "edit_replace_title":     "\u05d4\u05d7\u05dc\u05e4\u05ea \u05ea\u05e8\u05d2\u05d9\u05dc",
        "edit_add_title":         "\u05d4\u05d5\u05e1\u05e3 \u05ea\u05e8\u05d2\u05d9\u05dc",
        "edit_all_muscles":       "\u05d4\u05db\u05dc",
        "edit_no_alternatives":   "\u05d0\u05d9\u05df \u05d7\u05dc\u05d5\u05e4\u05d5\u05ea \u05d6\u05de\u05d9\u05e0\u05d5\u05ea \u05dc\u05e6\u05d9\u05d5\u05d3 \u05d4\u05e7\u05d9\u05d9\u05dd.",
        "edit_rebuilding":        "\u05e9\u05d5\u05de\u05e8 \u05e9\u05d9\u05e0\u05d5\u05d9\u05d9\u05dd\u2026",
        "edit_rebuild_failed":    "\u05e2\u05d3\u05db\u05d5\u05df \u05d4\u05d0\u05d9\u05de\u05d5\u05df \u05e0\u05db\u05e9\u05dc. \u05e0\u05e1\u05d4 \u05e9\u05d5\u05d1.",
        "edit_toast_removed":     "\u05ea\u05e8\u05d2\u05d9\u05dc \u05d4\u05d5\u05e1\u05e8",
        "edit_toast_replaced":    "\u05ea\u05e8\u05d2\u05d9\u05dc \u05d4\u05d5\u05d7\u05dc\u05e3",
        "edit_toast_added":       "\u05ea\u05e8\u05d2\u05d9\u05dc \u05e0\u05d5\u05e1\u05e3",
        "edit_toast_reordered":   "\u05d4\u05e1\u05d3\u05e8 \u05e2\u05d5\u05d3\u05db\u05df",

        # --- Footer ---
        "footer_text": "\u05db\u05dc\u05d9 \u05d0\u05d9\u05de\u05d5\u05df \u05dc\u05d0 \u05e8\u05e9\u05de\u05d9 \u05e9\u05dc Garmin Connect",
    },
}


def t(key: str, lang: str = "en", **kwargs: str) -> str:
    """Return the translated string for *key* in *lang*, falling back to English."""
    text = TRANSLATIONS.get(lang, {}).get(key) or TRANSLATIONS["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text


def make_t(lang: str) -> Callable[[str], str]:
    """Return a single-argument translate function bound to *lang*.

    The returned callable is injected into Jinja2 template context as ``t``.
    Templates call ``{{ t('key') }}`` — no ``lang`` argument needed.
    For dynamic substitutions templates use Jinja2 string concatenation directly.
    """
    def _t(key: str) -> str:
        return t(key, lang)
    return _t
