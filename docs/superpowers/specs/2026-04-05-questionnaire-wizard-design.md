# Questionnaire Wizard — Design Spec
**Date:** 2026-04-05
**Status:** Approved

## Overview

Replace the current static scrollable questionnaire form with an animated step-by-step wizard. One question fills the screen at a time. Answering and pressing Continue fades the card out (scale down + fade) and fades the next one in. A progress bar and dot indicators show where the user is. A summary screen at the end lets them review before saving.

---

## Interaction Design

| Decision | Choice |
|---|---|
| Layout | Single-question wizard (one card visible at a time) |
| Transition | Fade + scale: exit shrinks to 0.94 + fades out; enter scales up from 0.94 + fades in |
| Navigation | Back / Continue buttons on every card; Back reverses with the same animation |
| Progress | Thin progress bar (top) + dot strip (bottom); both update on each step |
| Summary | Final screen shows all answers as badge chips before Save |

---

## Question Sequence (7 steps + summary)

| # | Label | UI Control | Notes |
|---|---|---|---|
| 1 | Age | **Range slider** 13–80, large numeric readout | Live-updating value display |
| 2 | Fitness level | **3-option radio row** | Beginner / Intermediate / Advanced |
| 3 | Days / week | **Range slider** 1–7 | Live "N days / week" label |
| 4 | Fitness goals | **Multi-select list** (5 opts) | Tap to toggle; allows multiple |
| 5 | Equipment | **Tag cloud** (pill buttons) | Same set as workout generator |
| 6 | Diet | **2-col checkbox grid** | 8 options |
| 7 | Health conditions | **2-col checkbox grid** | 6 options |
| — | Summary | Read-only badge chips | "Edit ←" returns to step 7 |

---

## Visual Style

- Inherits GarminForge dark theme (`#111316` background, `#0066cc` accent)
- Card: `#1a1d2e` background, `border-radius: 16px`, subtle border
- Section label: small uppercase blue text above the question title
- Slider value: large bold `#0066cc` number centered above the track
- Options: dark pill/card, `#0066cc` border + tint when selected
- Progress bar: 4px, fills left-to-right as steps complete
- Dot strip: 7 dots below card; active dot pulses slightly larger, completed dots dim blue

---

## Template Changes

**Replace** `web/templates/questionnaire.html` entirely.

The new template is a single-page wizard:
- All 7 question cards + summary card rendered in the HTML, stacked via `position: absolute`
- Only the active card has `opacity: 1; transform: scale(1); pointer-events: all`
- All others: `opacity: 0; transform: scale(0.94); pointer-events: none`
- CSS transition on both `opacity` and `transform` (0.32s ease)
- Vanilla JS (~80 lines) handles step index, progress updates, dot rendering, slider live labels, option toggling, and Back/Continue navigation
- No new JS dependencies — no frameworks, no libraries beyond what's already on the page

**No backend changes required** — the form still POSTs to `POST /my/questionnaire` with the same field names (`age`, `fitness_level`, `diet[]`, etc.).

---

## Verified Unchanged

- Form action: `POST /my/questionnaire`
- Field names match `routes_my.py` handler: `age`, `fitness_level`, `weekly_workout_days`, `fitness_goals`, `equipment`, `diet`, `health_conditions`
- Skip button still POSTs to `/my/questionnaire/skip`
- Pre-population of existing answers on retake (Jinja2 `selected`/`checked` attributes still work since cards are server-rendered)

---

## Out of Scope

- No swipe gesture support (mouse/touch drag) — Continue button only
- No animation direction difference for Back vs Forward (same fade-scale both ways)
- No per-step validation (all fields optional, consistent with current behaviour)
