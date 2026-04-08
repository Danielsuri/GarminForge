# Pre-fill Dashboard Goal and Equipment from Questionnaire Data

**Date:** 2026-04-08  
**Scope:** Quick Wins #1 and #2 — dashboard form pre-selection for returning users  
**Files touched:** `web/app.py`, `web/templates/dashboard.html`

---

## Goal

When a logged-in user visits the dashboard, the goal radio and equipment multiselect are pre-populated from their questionnaire profile data. No re-selecting required on repeat visits.

## Data Sources

- `User.fitness_goals_json` — JSON list e.g. `["build_muscle", "lose_weight"]`. First element is used as the pre-selected goal.
- `User.preferred_equipment_json` — JSON list e.g. `["barbell", "dumbbell"]`. Full list is used to pre-select equipment.
- `forge_user` is already injected into every template by `render_template` — no extra DB query needed.

## Changes

### `web/app.py` — `GET /` route

Call `get_current_user(request, db)` (already used elsewhere in the codebase) to resolve the logged-in user, parse the two JSON fields, and pass the results to `_render()`:

```python
from web.auth_utils import get_current_user
import json

# inside index():
forge_user = get_current_user(request, db)
selected_goal = None
user_equipment: list[str] = []
if forge_user is not None:
    if forge_user.fitness_goals_json:
        goals_list = json.loads(forge_user.fitness_goals_json)
        selected_goal = goals_list[0] if goals_list else None
    if forge_user.preferred_equipment_json:
        user_equipment = json.loads(forge_user.preferred_equipment_json)
```

Pass `selected_goal=selected_goal` and `user_equipment=user_equipment` to `_render()`.

### `web/templates/dashboard.html` — Tom Select init

Add `items` to the TomSelect constructor so equipment is pre-selected on load:

```js
new TomSelect('#equipmentSelect', {
  items: {{ user_equipment | tojson }},
  plugins: ['remove_button', 'clear_button'],
  // ... rest unchanged
});
```

The goal radio already handles `selected_goal` — template lines 70–72 check `key == (selected_goal or '')` and set `checked` accordingly. No template changes needed for goal beyond passing the variable.

## Fallback Behavior

- User not logged in: `selected_goal=None`, `user_equipment=[]` → dashboard behaves exactly as today (first goal checked, no equipment pre-selected).
- User logged in but questionnaire not completed: same fallback.

## Out of Scope

- Persisting changes the user makes on the dashboard back to their profile (separate feature).
- Pre-filling duration or other fields.
