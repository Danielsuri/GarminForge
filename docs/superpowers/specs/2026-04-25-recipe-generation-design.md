---
title: Recipe Generation for Nutrition Plan
date: 2026-04-25
status: approved
---

## Problem

The nutrition plan feature shows weekly meal schedules but gives users no guidance on how to actually cook each meal. Users know *what* to eat but not *how* to prepare it.

## Goal

Add on-demand, AI-generated, bilingual recipe cards per meal — cached permanently by `meal_id` so over time every pool meal has a built-in recipe and AI calls become unnecessary.

---

## Architecture

### Data model

New `RecipeCache` table in `web/models.py`:

```python
class RecipeCache(Base):
    __tablename__ = "recipe_cache"
    id: Mapped[str]            # UUID primary key
    meal_id: Mapped[str]       # unique index
    recipe_en: Mapped[str]     # JSON blob
    recipe_he: Mapped[str]     # JSON blob
    generated_at: Mapped[datetime]
```

Recipe blob schema (same shape for both `recipe_en` and `recipe_he`):

```json
{
  "servings": 2,
  "prep_time_min": 10,
  "cook_time_min": 20,
  "steps": ["Step 1...", "Step 2..."],
  "tips": ["Tip 1..."]
}
```

`meal_id` has a unique constraint. DB table is created via the same `Base.metadata.create_all` call used elsewhere in the project (no separate migration tool).

---

### Backend route

`GET /nutrition/meals/{meal_id}/recipe` added to `web/routes_nutrition.py`.

Flow:

1. Query `RecipeCache` by `meal_id` → return `{recipe_en, recipe_he}` if found (cache hit).
2. On miss: resolve meal object from `meal_selector.load_pool()`. For user-suggested meals, also check `MealSuggestion` rows.
3. Build prompt and call `get_ai_provider().complete(prompt)`.
4. Parse response with existing `_extract_json()` from `web/ai_provider.py`.
5. Insert `RecipeCache` row; return `{recipe_en, recipe_he}`.
6. On AI failure or unparseable JSON: return HTTP 502 `{"error": "recipe_unavailable"}`.

AI prompt template:

```
Given this meal:
  Name: {name_en} ({name_he})
  Ingredients: {comma-separated item_en list}

Return JSON with exactly these top-level keys:
  recipe_en: { servings (int), prep_time_min (int), cook_time_min (int), steps (string[]), tips (string[]) }
  recipe_he: { servings (int), prep_time_min (int), cook_time_min (int), steps (string[]), tips (string[]) }

steps and tips must be written in the respective language.
Return only the JSON object, no markdown.
```

---

### UI (`web/templates/nutrition.html`)

- Each meal card in the Plan tab gets a **"Recipe"** button.
- On click: button shows a spinner, fires `fetch('/nutrition/meals/{meal_id}/recipe')`.
- On success: populate and open a recipe modal (reuse the existing suggestion modal pattern).
- Modal sections: meal name, prep time, cook time, servings, numbered steps, tips.
- Language: driven by the existing `currentLang` JS variable so the modal follows the page lang toggle.
- In-page JS cache: a `Map` keyed by `meal_id` stores fetched recipes; repeat taps skip the fetch.
- On 502: modal shows an error message with a retry button.

---

### Graduate script

`scripts/graduate_recipes.py` — reads all `RecipeCache` rows, matches by `meal_id` to entries in `web/data/meal_pool.json`, writes `recipe_en` and `recipe_he` fields onto matching entries, saves the file in-place. Run manually once most meals are covered to bake recipes into the static pool.

---

## Files changed

| File | Change |
|------|--------|
| `web/models.py` | Add `RecipeCache` model |
| `web/routes_nutrition.py` | Add `GET /nutrition/meals/{meal_id}/recipe` |
| `web/templates/nutrition.html` | Recipe button on meal cards + recipe modal |
| `scripts/graduate_recipes.py` | New graduation script (new file) |

Reused without change: `web/ai_provider.py` (`get_ai_provider`, `_extract_json`), `web/meal_selector.py` (`load_pool`).

---

## Verification

- Recipe button appears on every meal card in the Plan tab.
- First tap: spinner shows, AI is called, modal opens with all fields (steps, tips, times, servings).
- Second tap (same session): no network request — in-page JS cache serves the recipe.
- Page reload + tap: `RecipeCache` row is returned, no AI call.
- Language toggle: modal re-renders in the new language.
- AI failure (invalid key): 502 returned, modal shows retry message without crashing the page.
- `pytest` passes with no regressions.
