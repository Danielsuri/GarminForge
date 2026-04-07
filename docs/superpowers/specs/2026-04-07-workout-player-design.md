# Workout Player — Design Spec

**Date:** 2026-04-07
**Status:** Approved

---

## Context

GarminForge currently generates workouts and uploads them to Garmin Connect, but provides no in-browser way to actually *do* a workout. Users on a phone or without a Garmin device have no guided experience. This feature adds a fullscreen workout player that walks through exercises with countdowns, rest timers, TTS announcements, wake lock, and vibration — and integrates locally-hosted MP4 tutorial videos alongside existing YouTube tutorial links.

---

## Scope

Two integrated features:

1. **Workout Player** — fullscreen Bootstrap modal that executes the workout with timers, TTS, wake lock, vibration, and video
2. **Video integration** — local MP4s served from `/static/videos/`; shown in the player and as inline tutorial modals in the exercise table

---

## Data Flow

`exercises_json` is already computed and passed to `workout_preview.html` from `app.py`'s `/workout/generate` route. No route changes are needed. The new `video_url` field is added to `ExerciseInfo` and flows through the existing JSON automatically.

```
workout_generator.py
  ExerciseInfo.video_url  ←  _LOCAL_VIDEO_MAP lookup
        ↓
  exercises_json (already in template context)
        ↓
workout_preview.html
  Player JS reads exercises_json → builds queue → runs state machine
```

---

## Files to Modify

| File | Change |
|------|--------|
| `web/workout_generator.py` | Add `video_url: str \| None` to `ExerciseInfo`; add `_LOCAL_VIDEO_MAP` |
| `web/templates/workout_preview.html` | Play button, player modal, video tutorial modal, player JS |
| `web/static/videos/` | New directory — copy MP4s here |

`web/app.py` — no changes needed.

---

## 1. Static Video Serving

Copy MP4s from the project root `videos/` into `web/static/videos/`. The existing `/static` mount in `app.py` (line 128) already serves `web/static/`, so no mount changes are required.

Initial catalog:
```
web/static/videos/
  bulgarian-split-squat.mp4   →  BULGARIAN_SPLIT_SQUAT
  jump-squat.mp4               →  JUMP_SQUAT
```

Naming convention: `EXERCISE_NAME` key → lowercase-hyphenated filename.

---

## 2. `ExerciseInfo` Changes (`web/workout_generator.py`)

### New field

```python
@dataclass
class ExerciseInfo:
    # ... existing fields ...
    video_url: str | None = None   # e.g. "/static/videos/bulgarian-split-squat.mp4"
```

### Local video map

```python
_LOCAL_VIDEO_MAP: dict[str, str] = {
    "BULGARIAN_SPLIT_SQUAT": "/static/videos/bulgarian-split-squat.mp4",
    "JUMP_SQUAT":            "/static/videos/jump-squat.mp4",
}
```

### Population

When building each `ExerciseInfo` in `_select_exercises()`, set:
```python
video_url=_LOCAL_VIDEO_MAP.get(ex_name)
```

---

## 3. Template Changes (`web/templates/workout_preview.html`)

### 3a. Play button

Add alongside the existing Upload/Save buttons in the preview card header:

```html
<button class="btn btn-success" id="playBtn">
  <i class="bi bi-play-fill"></i> Play Workout
</button>
```

### 3b. Video tutorial modal

For exercises with `video_url`, the Tutorial button opens an inline Bootstrap modal instead of a new tab:

```html
<!-- trigger -->
<button onclick="openVideoModal('/static/videos/bulgarian-split-squat.mp4', 'Bulgarian Split Squat')">
  Tutorial
</button>

<!-- modal (one shared instance, src swapped on open) -->
<div class="modal fade" id="videoModal">
  <video id="videoModalPlayer" controls style="width:100%"></video>
</div>
```

For exercises without `video_url`, the Tutorial button retains existing behavior (opens `ex.link` in new tab).

### 3c. Workout player modal

Fullscreen Bootstrap modal (`modal-fullscreen`), dark theme:

```
+------------------------------------------+
|  [ video / thumbnail / name card ]       |
|                                          |
|  Exercise Name                           |
|  0:45  (countdown)  or  × 12  (reps)    |
|                                          |
|  Round 2 of 3  ·  Step 4 of 18          |
|  ████████████░░░░░░░░  progress bar      |
|                                          |
|  [⏸ Pause]  [⏭ Skip]                    |
+------------------------------------------+
```

**Video area fallback chain:**
1. `ex.video_url` exists → `<video autoplay loop muted playsinline>`
2. `ex.link` contains `watch?v=` → `<img src="https://img.youtube.com/vi/{id}/hqdefault.jpg">`
3. Neither → exercise name + muscle group card (icon + label)

**Rest screen** (between exercises):
- No video — large countdown only
- Label: "Rest · Next: {next_exercise_name}"
- Vibrate on rest-end: `navigator.vibrate([200, 100, 200])`

**Warmup screen** (5 s before first exercise):
- Countdown from 5, label "Get Ready"

**Complete screen:**
- Summary: total time, exercises completed
- "Close" button releases wake lock

---

## 4. Player JS State Machine

### States
```
IDLE → WARMUP → EXERCISE → REST → EXERCISE → ... → COMPLETE
```

### Queue construction
```js
// rounds = exercises[0].sets
// queue: [{type:'warmup', duration:5}, {type:'exercise', ex}, {type:'rest', ex}, ...]
for (let r = 0; r < rounds; r++) {
  for (const ex of exercises) {
    queue.push({ type: 'exercise', ex, round: r + 1 });
    if (ex.rest_seconds > 0) queue.push({ type: 'rest', ex, round: r + 1 });
  }
}
```

### Timer loop
`setInterval`-based, 1 s tick. Each tick decrements `timeLeft`; at 0, calls `advance()`.

### Rep-based exercises
`ex.duration_sec == null` → skip timer, show `× {ex.reps}`. Advance on "Skip" tap only — no auto-advance.

### Web Speech API (best-effort)
```js
// On EXERCISE start: "Exercise: Bulgarian Split Squat, 10 reps"
// On REST start:     "Rest, 60 seconds"
// On round complete: "Round 2 complete"
```

### Wake Lock API (best-effort)
```js
if ('wakeLock' in navigator) wakeLock = await navigator.wakeLock.request('screen');
// Release on COMPLETE or modal close
```

### Pause / Skip
- Pause: clears interval, stores remaining time, shows Resume button
- Skip: calls `advance()` immediately

---

## 5. Tutorial Link Logic (exercise table)

In `exerciseRowHTML()` JS function (already exists in the template):

```js
const tutorialBtn = ex.video_url
  ? `<button onclick="openVideoModal('${ex.video_url}', '${ex.label}')">Tutorial</button>`
  : `<a href="${ex.link}" target="_blank">Tutorial</a>`;
```

---

## Verification

1. Generate a workout → click **Play Workout**
   - Warmup countdown appears (5 s)
   - First exercise loads: name announced via TTS, video plays (if available) or thumbnail shows
   - Timer counts down for timed exercises; rep count shown for rep-based
   - Rest phase shows with countdown + next-exercise label
   - Round indicator increments correctly
   - Final exercise → Complete screen appears

2. Mobile checks
   - Screen stays on (Wake Lock active)
   - Vibration fires at rest-end
   - Fullscreen modal fills viewport

3. Tutorial links
   - Bulgarian Split Squat / Jump Squat: clicking Tutorial opens video modal (not YouTube)
   - Any other exercise: Tutorial opens YouTube in new tab

4. Fallbacks
   - Exercise with YouTube direct link but no local video: thumbnail shows in player
   - Exercise with search-fallback link: name+muscle card shows in player
