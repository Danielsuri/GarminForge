# Onboarding Questionnaire & Dashboard Redesign

**Date:** 2026-04-11  
**Status:** Approved

---

## Context

Currently, unauthenticated users land on a login/dashboard page. The questionnaire exists at `/my/questionnaire` but is only accessible post-login. The goal of this redesign is to:

1. Make the questionnaire the **first thing every user sees**, before creating an account
2. Gate app access behind questionnaire completion — every user must have a program
3. Replace the generic dashboard with a **session-focused home screen** showing the upcoming workout with muscle map, exercise thumbnails, and a nutrition placeholder

This mirrors high-conversion fitness app patterns (e.g. BetterMe) where personalization happens before commitment.

---

## Routing & Flow

### Unauthenticated users
- `GET /` → `RedirectResponse("/onboarding")`
- `GET /onboarding` → render questionnaire (no auth guard)
- `POST /onboarding` (guest) → save answers to `session["pending_q"]`, redirect to `/register`
- `POST /register` (new route) → create user, consume `session["pending_q"]`, save to User, auto-generate program, `login_session()`, redirect to `/`

### Authenticated users
- `GET /` logic (in priority order):
  1. `questionnaire_completed=False` → `RedirectResponse("/onboarding")`
  2. Has active program → `RedirectResponse(f"/my/programs/{program.id}/sessions/{session.id}")`
  3. No program → auto-generate program → redirect to today's session
  - **Case "authenticated, no active program" (the old dashboard fallback) is eliminated**
- `POST /onboarding` (logged-in) → save answers to User, set `questionnaire_completed=True`, redirect to `/`
- `GET /my/questionnaire` → `RedirectResponse("/onboarding", 301)` (backward compat)

### Skip button
- **Removed entirely.** Questionnaire is mandatory.

---

## Questionnaire Steps (9 total)

Shared template `questionnaire.html`. Guest sees all 9 steps; logged-in user sees steps 1–8 (no sign-up card).

| # | Step | UI Component | Notes |
|---|------|-------------|-------|
| 1 | **Goal** | 6 image cards (PNG per goal) | "Already registered? [Login]" link beneath cards |
| 2 | **Age range** | 4 selectable cards: 18–29 / 30–39 / 40–49 / 50+ | Replaces age slider; stored as `age_range` string |
| 3 | **Fitness level** | Radio cards: Beginner / Intermediate / Advanced | Existing `.wopt` styling |
| 4 | **Preferred training days** | 7 day-toggle buttons (Mon–Sun), multi-select | Replaces `weekly_workout_days` int slider |
| 5 | **Equipment** | Existing tag cloud | No change |
| 6 | **Height & Weight** | Two inputs in one card, metric/imperial toggle | New step; used for future BMI calc |
| 7 | **Diet** | Existing 2-col grid | No change |
| 8 | **Health conditions** | Existing 2-col grid | No change |
| 9 | **Sign-up (guest only)** | Final card styled as questionnaire step | See Sign-Up Card section below |

### Goal image cards (step 1)
Each card uses the corresponding PNG from `web/static/img/`:
- `burn-fat.png` → "Burn Fat"
- `lose-weight.png` → "Lose Weight"  
- `build-mucsle.png` → "Build Muscle" (note: filename has typo — do not rename, just map correctly)
- `build-strength.png` → "Build Strength"
- `general-fitness.png` → "General Fitness"
- `muscular-endurance.png` → "Muscular Endurance"

Cards are displayed in a 2×3 grid (desktop) / 2×3 grid (mobile). Each card: image cropped to a fixed aspect ratio (4:3), goal label overlaid at bottom, selected state with purple border + checkmark.

### Age range cards (step 2)
Four cards in a 2×2 grid. No photos available — use styled cards with large age text and a subtle fitness silhouette illustration (CSS/SVG, no external assets). Selected state: purple border + background tint.

### Preferred training days (step 4)
7 pill buttons in a single row (desktop) / wrapping row (mobile): Mon Tue Wed Thu Fri Sat Sun. Multi-select. Minimum 1 day required to advance. Derived count passed to program generator as `weekly_workout_days = len(preferred_days)`.

### Height & Weight (step 6)
Single card with two input pairs side by side:
- Height: number input + unit label (cm / ft+in)
- Weight: number input + unit label (kg / lbs)
- Metric/Imperial toggle (two pill buttons at top of card)
- JS converts ft+in → cm and lbs → kg before storing; always stored in metric
- Both fields optional (user can skip with "Skip" link on this card only — no global skip)

---

## Data Model Changes

**`web/models.py` — `User` additions:**

```python
# New fields
age_range: str | None          # "18-29" | "30-39" | "40-49" | "50+"
preferred_days_json: str       # JSON list e.g. '["Mon","Wed","Fri"]'  default "[]"
height_cm: float | None        # stored in cm regardless of input unit
weight_kg: float | None        # stored in kg regardless of input unit

# Existing field kept for legacy compat (computed from preferred_days_json length)
weekly_workout_days: int | None  # keep nullable, populated on save
```

**`web/migrations/`** — new Alembic migration to add the four columns.

---

## Sign-Up Card (Step 9, guests only)

Styled identically to other `.wcard` steps. Progress bar shows 100%.

**Content:**
- Label: "ALMOST THERE" (`.wcard-label` style)
- Title: "Your plan is ready."
- Subtitle: "Create a free account to unlock it."
- Email input
- Password input (min 8 chars, show/hide toggle)
- Primary CTA: "Create account & start training" (`.wnav-save` style)
- Divider: "or"
- "Continue with Google" button (existing OAuth — `GET /auth/google?next=/`)
- Fine print: "Already have an account? [Log in]"

**Route:** `POST /register` (new, in `routes_auth.py`)
- Validates email/password
- Creates `User` row
- Reads `session["pending_q"]`, maps to model fields, saves
- Sets `questionnaire_completed=True`
- Calls `auto_generate_program(user, db)` (see below)
- Calls `login_session(request, user)`
- Redirects to `/`

The existing `GET/POST /auth/register` route is **kept** as a fallback (direct link, deep link) but is no longer the primary path. It should also consume `session["pending_q"]` if present.

---

## Auto-Generate Program on Registration

New function `auto_generate_program(user: User, db: Session) -> Program` in `web/program_generator.py` (or a new `web/onboarding.py`).

**Logic:**
- Goal → map `fitness_goals_json[0]` to periodization strategy:
  - `burn_fat` / `lose_weight` → `"linear"`, moderate intensity
  - `build_muscle` / `build_strength` → `"block"`
  - `general_fitness` / `endurance` → `"undulating"`
- Duration: 8 weeks default
- Sessions per week: `len(preferred_days)` or fallback to 3
- Equipment: from `preferred_equipment_json`
- Fitness level: from `fitness_level`
- Schedule sessions starting from next Monday
- Creates `Program` + all `ProgramSession` rows
- Sets `program.status = "active"`

This same function is called when:
1. New user registers via questionnaire
2. Authenticated user with `questionnaire_completed=True` but no active program hits `/`
3. User resets their program from profile (future)

---

## Dashboard / Session Home Screen Changes

The **session preview page** (`web/templates/my_session_preview.html`) becomes the effective home. Two sections added:

### Upcoming Workout Card
Added above the existing session detail. Contains:
- Session name + scheduled date (e.g. "Week 1 · Day 1 — Build Strength")
- Muscle map SVG (already rendered on this page — reuse `muscle_map_svg`)
- Mini exercise list (first 5 exercises):
  ```html
  <div class="exercise-row">
    <div class="exercise-thumb-placeholder"></div>  <!-- 40×40px grey square -->
    <div class="exercise-row-info">
      <span class="exercise-row-name">Barbell Bench Press</span>
      <div class="exercise-row-meta">  <!-- colored dot pills: 4 sets · 8 reps -->
        <span class="set-pip"></span>...
      </div>
    </div>
    <button class="exercise-row-more">···</button>
  </div>
  ```
- "Start workout" CTA (existing play button)

### Today's Nutrition Placeholder
Below the workout card:
```html
<div class="koda-card koda-card--coming-soon">
  <div class="coming-soon-badge">Coming Soon</div>
  <h3>Today's Nutrition</h3>
  <p>Personalized meal plan based on your goals.</p>
  <!-- greyed-out placeholder rows -->
</div>
```

---

## Files to Create / Modify

| File | Action | Notes |
|------|--------|-------|
| `web/app.py` | Modify | Update `GET /` routing logic; remove dashboard fallback for auth users |
| `web/routes_auth.py` | Modify | Add `GET/POST /register` (new sign-up card route); update existing `/auth/register` to consume `session["pending_q"]` |
| `web/routes_my.py` | Modify | `GET/POST /my/questionnaire` → redirect to `/onboarding`; remove skip route |
| `web/models.py` | Modify | Add `age_range`, `preferred_days_json`, `height_cm`, `weight_kg` columns |
| `web/migrations/versions/` | Create | New Alembic migration for 4 new columns |
| `web/program_generator.py` | Modify | Add `auto_generate_program()` function |
| `web/templates/questionnaire.html` | Modify | Reorder steps; replace age slider with range cards; replace days slider with day-picker; add height/weight card; add sign-up card (guest only); add goal image cards |
| `web/templates/my_session_preview.html` | Modify | Add exercise thumbnail rows + nutrition coming-soon card |
| `web/static/css/` (or inline) | Modify | Styles for goal image cards, age range cards, day-picker pills, exercise thumb rows, coming-soon card |

---

## Verification

1. **Guest flow:** Open app in incognito → should land on `/onboarding` → complete all 8 steps → sign-up card appears → register → land on today's session with muscle map + exercise list
2. **Logged-in retake:** Log in → go to `/my/questionnaire` → redirected to `/onboarding` → complete → no sign-up card → land on dashboard
3. **Skip removed:** No skip button visible at any step
4. **Auto-program:** After registration, DB has 1 active `Program` + scheduled `ProgramSession` rows for next 8 weeks
5. **Preferred days:** Select Mon/Wed/Fri → program sessions only scheduled on those days
6. **Height/weight optional:** Advance past step 6 without filling → no validation error, fields NULL in DB
7. **Dashboard:** Session page shows muscle map + 5 exercise rows with grey thumbnails + nutrition coming-soon card
8. **`/` with no program:** Authenticated user with no active program → program auto-generated → redirected to session (not the old generator dashboard)
