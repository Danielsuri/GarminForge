# GarminForge Quick Wins

Low-effort, high-value improvements that can be shipped in hours to days.
All items use data and infrastructure that **already exists** in the codebase — nothing requires a
new architectural layer.

---

## ⭐⭐⭐ Do First — High Value / Low Effort

### ~~1. Pre-fill dashboard goal from questionnaire data~~ ✅ DONE (v2.0.0)
**Location:** `web/app.py` GET `/` · `web/templates/dashboard.html`

**What exists:**
- `User.fitness_goals_json` stores e.g. `["build_muscle", "lose_weight"]` after questionnaire
- Dashboard has 6 goal radio buttons keyed to the same GOALS dict
- `User.preferred_equipment_json` stores the user's equipment

**Current state:** Dashboard always resets to default on every visit — the questionnaire data is
never fed back to the form.

**Quick win:** In the GET `/` route, read `forge_user.fitness_goals_json` and
`forge_user.preferred_equipment_json`, map the first stored goal to a pre-selected radio, and pass
the equipment list to the Tom Select initializer.

**Value:** Every returning user immediately sees a form tuned to their profile — no re-selecting
required. Signals that the app "knows you."

**Effort:** ~1–2 hours

---

### ~~2. Equipment pre-selection for returning users~~ ✅ DONE (v2.0.0)
**Location:** `web/app.py` GET `/` · `web/templates/dashboard.html` Tom Select init

**What exists:**
- `User.preferred_equipment_json` (JSON list of equipment tag strings, e.g. `["barbell","dumbbell"]`)
- Tom Select multiselect already handles programmatic pre-selection via `items: [...]` config
- 27 equipment options defined in `EQUIPMENT_OPTIONS`

**Current state:** Tom Select initializes with no pre-selected items on every page load.

**Quick win:** Pass `user_equipment` (parsed from DB JSON) to the template; inject into the
`TomSelect` constructor as `items`.

**Value:** Removes the most tedious repeated input for every returning user. Pairs with item #1 above
for a fully pre-filled form.

**Effort:** ~1 hour

---

### 3. Health-condition exercise filtering
**Location:** `web/workout_generator.py` → `_select_exercises()`

**What exists:**
- `User.health_conditions_json` collects `"heart"`, `"joints"`, `"back"`, `"asthma"`,
  `"hypertension"`, `"diabetes"` from the questionnaire
- `ExerciseInfo` has `category`, `label`, `primary_muscles`
- `_ExTemplate` has `muscle_group` and `required_equipment_labels`

**Current state:** `_select_exercises()` ignores health conditions entirely; high-impact plyometric
exercises can be assigned to users who flagged joint problems.

**Quick win:** Add a `health_conditions: list[str]` parameter to `generate()` and
`_select_exercises()`. Define a small exclusion map:

```python
_HEALTH_EXCLUSIONS = {
    "joints":      {"PLYO", "BOX_JUMP", "JUMP_SQUAT", "BURPEE", "JUMP_LUNGE"},
    "back":        {"DEADLIFT", "GOOD_MORNING", "BACK_EXTENSION", "HYPEREXTENSION"},
    "heart":       {"BATTLE_ROPE", "BURPEE", "JUMP_SQUAT"},  # extreme HIIT
    "asthma":      {"BATTLE_ROPE"},
}
```

Filter `_POOL` before selection. Pass `health_conditions` from the logged-in user's profile.

**Value:** Safety + meaningful personalization. A user with bad knees will never get box jumps.
This is something no generic fitness app does, and it directly uses data you already collected.

**Effort:** ~4–6 hours

---

### 4. Workout naming with Week/Day prefix
**Location:** `web/workout_generator.py` ~line 590 (name generation)

**What exists:**
- Name is generated as: `"Build Muscle — 45min (Apr 07)"`
- `generate()` signature: `generate(equipment, goal, duration_minutes, ...)`

**Current state:** Every workout looks like a one-off session; no sense of progression.

**Quick win:** Add optional `week_num: int | None` and `day_num: int | None` params:
```python
prefix = f"Week {week_num} Day {day_num} · " if week_num and day_num else ""
name = f"{prefix}{goal_label} — {duration_minutes}min ({date_str})"
# → "Week 1 Day 1 · Build Muscle — 45min (Apr 07)"
```

No backend changes required. The UI can expose week/day inputs as optional fields, or
the multi-week program generator (Slow Burn #2) will supply them automatically.

**Value:** Instantly frames the app as a progressive training tool, not a one-shot generator.
Sets the mental model for multi-week programs before that feature is built.

**Effort:** ~30 minutes

---

### 5. Scheduling date suggestions based on weekly_workout_days
**Location:** `web/templates/workout_preview.html` upload section

**What exists:**
- `User.weekly_workout_days` (integer 1–7 from questionnaire)
- `schedule_date` date input already in the upload form
- Upload form already has JS interaction

**Current state:** The date input is blank; users must manually type or pick a date.

**Quick win:** When the upload form opens, compute the next N candidate dates (spread across
the week matching the user's cadence) and render them as clickable date chips above the date input:

```
📅 Suggested:  [ Mon Apr 7 ]  [ Wed Apr 9 ]  [ Fri Apr 11 ]
```

Clicking a chip fills the hidden date input. Fall back to a plain date picker if
`weekly_workout_days` is not set.

**Value:** Removes friction from the most important action (uploading to Garmin). Makes the app
feel adaptive to the user's schedule without requiring any new data.

**Effort:** ~3–4 hours

---

### 6. Surface Garmin workout history in the UI
**Location:** New route `GET /my/garmin-workouts` + card in `web/templates/dashboard.html`

**What exists:**
- `GarminForgeClient.get_workouts(start=0, limit=10)` — fully implemented, never called from UI
- Debug route `/debug/workouts` exists but is hidden (not linked in navbar or dashboard)
- The response includes `workoutName`, `sportType`, `createdDate`, `workoutId`

**Current state:** A user's Garmin workout history is invisible inside GarminForge. The debug route
is accessible by URL only.

**Quick win:**
1. Add `GET /my/garmin-workouts` that calls `forge.get_workouts()` and returns JSON
2. Add a "Recent Garmin Workouts" collapsible card to the dashboard sidebar
3. Each row: workout name + date + "Duplicate" button (pre-fills the generate form with same goal/duration)

**Value:** Closes the loop — users see what they've sent to Garmin and can build on previous
sessions. Also validates the Garmin connection is working.

**Effort:** ~4–6 hours

---

## ⭐⭐ Do Soon — High Value / Medium Effort

### 7. Show rounds_completed in the progress page
**Location:** `web/templates/my_progress.html`

**What exists:**
- `WorkoutSession.rounds_completed` and `WorkoutSession.total_rounds` are stored by the
  Workout Player app via `POST /my/sessions`
- The progress template (`my_progress.html`) renders exercises_completed/total_exercises but
  **never references rounds columns**

**Current state:** Round completion data is silently discarded in the UI.

**Quick win:** Add a "Rounds" column to the sessions table:
```
| Plan Name | Date | Duration | Exercises | Rounds | Status |
| Chest Day | Apr 7 | 45 min | 6/8 ████░░ | 3/4 | done |
```

**Value:** More granular progress visibility; shows users they're completing full circuits.

**Effort:** ~1 hour (template-only change)

---

### 8. Add curated video links for 33 missing exercises
**Location:** `web/exercise_links.py`

**What exists:**
- 117 exercises have direct YouTube links (stable, curated channels: Jeff Nippard, Alan Thrall,
  AthleanX)
- ~33 exercises fall back to `youtube.com/results?search_query=how+to+{name}` — a search page,
  not a tutorial

**Missing categories with no curated links:**
- Suspension training (TRX ROW, TRX PUSH_UP, TRX CURL, TRX DIP, TRX LUNGE, TRX SQUAT)
- Sled exercises (SLED_PUSH, SLED_PULL, FARMER_CARRY)
- Sandbag exercises (SANDBAG_SQUAT, SANDBAG_CARRY, SANDBAG_CLEAN)
- Battle rope variants (BATTLE_ROPE_ALTERNATING_WAVES, BATTLE_ROPE_SLAM)
- Banded pull-up variants (BANDED_PULL_UP, NEUTRAL_GRIP_PULL_UP, WIDE_GRIP_PULL_UP)
- Plyo variants (JUMP_LUNGE, LATERAL_BOUND, BOX_JUMP_STEP_DOWN)

**Quick win:** Research and add direct tutorial URLs for these 33 exercises.

**Value:** Every user who taps a tutorial link goes to a real video, not a search results page.

**Effort:** ~2 hours

---

### 9. Display last_login_at as "last session" indicator
**Location:** `web/models.py` (field exists) · `web/templates/my_profile.html`

**What exists:**
- `User.last_login_at` is stored in the DB (updated on each login) but never displayed

**Current state:** The profile page shows "Member since" but nothing about recent activity.

**Quick win:** Add "Last active: 3 days ago" below the member-since line on the profile page.
Computing relative time is a 2-line Jinja2 expression.

**Value:** Lightweight gamification hook; nudges users who've been inactive.

**Effort:** ~30 minutes

---

### 10. Pull Garmin user profile onto the profile page
**Location:** `web/routes_my.py` GET `/my/profile` · `web/templates/my_profile.html`

**What exists:**
- `GarminForgeClient.get_user_profile()` — implemented in `garminforge/client.py`, never called
  from any web route
- Profile page has a "Garmin Connection" status indicator in the navbar

**Current state:** The profile page shows GarminForge account info but nothing about the linked
Garmin account beyond connection status.

**Quick win:** Call `forge.get_user_profile()` in the profile route and display Garmin display name,
profile picture URL, and member-since date in a "Garmin Account" card.

**Value:** Reinforces the Garmin connection; gives the profile page a richer identity.

**Effort:** ~3–4 hours

---

## ⭐ Nice to Have

### 11. Goal emoji in navbar
**Location:** `web/templates/base.html` navbar

**What exists:** `User.fitness_goals_json` stores primary goals; GOALS dict has `icon` per goal.

**Quick win:** Show the user's primary goal emoji next to their display name in the navbar.
E.g. `Daniel 💪` for a build_muscle user.

**Effort:** ~30 minutes

---

### 12. Re-verify SLIDING_DISC exercises against Garmin API
**Location:** `web/workout_generator.py` line 358

**What exists:**
```python
# SLIDING_DISC exercises removed pending verification of correct Garmin
# category/name via Exercises.json (category "SLIDING_DISC" is rejected by
# the Garmin API with "Invalid category").
```

8 sliding disc exercises were removed because the Garmin API rejected the category name.

**Quick win:** Use `/debug/lookup/workout-service/workout/exercises` to check current valid
category names. If `SLIDING_DISC` (or its correct alias) is now valid, re-add the exercises.

**Effort:** ~1–2 hours (debugging, not UI work)

---

## Priority Matrix

| Rank | Item | Value | Effort | Priority |
|------|------|-------|--------|----------|
| ~~1~~ | ~~Equipment pre-selection~~ | ~~High~~ | ~~1 hr~~ | ✅ v2.0.0 |
| ~~2~~ | ~~Pre-fill goal from questionnaire~~ | ~~High~~ | ~~1–2 hrs~~ | ✅ v2.0.0 |
| 3 | Workout naming with Week/Day prefix | Medium | 30 min | ⭐⭐⭐ |
| 4 | Health-condition exercise filtering | High | 4–6 hrs | ⭐⭐⭐ |
| 5 | Scheduling date suggestions | High | 3–4 hrs | ⭐⭐⭐ |
| 6 | Surface Garmin workout history | High | 4–6 hrs | ⭐⭐⭐ |
| 7 | rounds_completed in progress page | Medium | 1 hr | ⭐⭐ |
| 8 | Add missing exercise video links | Medium | 2 hrs | ⭐⭐ |
| 9 | Last-active indicator on profile | Low | 30 min | ⭐⭐ |
| 10 | Garmin profile on profile page | Medium | 3–4 hrs | ⭐⭐ |
| 11 | Goal emoji in navbar | Low | 30 min | ⭐ |
| 12 | Re-verify SLIDING_DISC category | Low | 1–2 hrs | ⭐ |

### Grouping by time investment

**Do in a single session (< 2 hrs total):**
Items ~~2~~, 3, 7, 9, 11 — can all be shipped in one focused sitting.

**Do next sprint (2–6 hrs each):**
Items 1, 4, 5, 6 — each is self-contained, can be tackled in any order.

**Do when you have a full day:**
Item 4 (health filtering) is the most impactful single change and justifies a careful implementation.
