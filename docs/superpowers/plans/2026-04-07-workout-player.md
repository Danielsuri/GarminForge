# Workout Player Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fullscreen in-browser workout player with countdown timers, TTS announcements, wake lock, vibration, and video integration (local MP4s + YouTube thumbnails).

**Architecture:** `video_url` is added to `ExerciseInfo` and flows through the already-existing `exercises_json` template variable. The player is a pure vanilla JS state machine inside a Bootstrap fullscreen modal — no new dependencies. Local MP4s are served by the existing `/static` mount after being copied into `web/static/videos/`. All DOM updates use `textContent` / `createElement` / `setAttribute` — no `innerHTML`.

**Tech Stack:** Python/FastAPI (backend), Jinja2 (templates), Bootstrap 5 modals, vanilla JS (Web Speech API, Wake Lock API, Vibration API)

---

## File Map

| File | Change |
|------|--------|
| `web/static/videos/bulgarian-split-squat.mp4` | New — copy from `videos/` |
| `web/static/videos/jump-squat.mp4` | New — copy from `videos/` |
| `web/workout_generator.py` | Add `video_url` field to `ExerciseInfo`; add `_LOCAL_VIDEO_MAP`; populate in `generate()` |
| `tests/test_workout_editor.py` | Add test for `video_url` population |
| `web/templates/workout_preview.html` | Play button in card header; video tutorial modal; player modal; player JS |

---

## Task 1: Copy videos into static directory

**Files:**
- Create: `web/static/videos/bulgarian-split-squat.mp4`
- Create: `web/static/videos/jump-squat.mp4`

- [ ] **Step 1: Create the directory and copy files**

```bash
mkdir -p web/static/videos
cp videos/bulgarian-split-squat.mp4 web/static/videos/
cp videos/jump-squat.mp4 web/static/videos/
```

- [ ] **Step 2: Verify files are served by the dev server**

Start the server with `python run.py` and open:
- `http://localhost:8000/static/videos/bulgarian-split-squat.mp4`
- `http://localhost:8000/static/videos/jump-squat.mp4`

Expected: browser plays each video (or shows the browser's native video player).

- [ ] **Step 3: Commit**

```bash
git add web/static/videos/
git commit -m "feat: add local exercise tutorial videos to static assets"
```

---

## Task 2: Write failing test for video_url field

**Files:**
- Modify: `tests/test_workout_editor.py`

- [ ] **Step 1: Add the test class**

Add this class to `tests/test_workout_editor.py` (after the existing test classes):

```python
class TestExerciseInfoVideoUrl:
    def test_local_video_map_contains_expected_keys(self):
        """_LOCAL_VIDEO_MAP must include both videos we ship."""
        from web.workout_generator import _LOCAL_VIDEO_MAP
        assert _LOCAL_VIDEO_MAP["BULGARIAN_SPLIT_SQUAT"] == "/static/videos/bulgarian-split-squat.mp4"
        assert _LOCAL_VIDEO_MAP["JUMP_SQUAT"] == "/static/videos/jump-squat.mp4"

    def test_exercise_info_has_video_url_field(self):
        """ExerciseInfo dataclass must have a video_url field defaulting to None."""
        import dataclasses
        from web.workout_generator import ExerciseInfo
        field_names = {f.name for f in dataclasses.fields(ExerciseInfo)}
        assert "video_url" in field_names
        # default is None
        plan = generate(["bodyweight"], "build_muscle", 45, seed=42)
        # at least one exercise should have video_url as None (most won't have local video)
        assert any(e.video_url is None for e in plan.exercises)

    def test_video_url_populated_when_exercise_matches_map(self):
        """ExerciseInfo.video_url is set when the exercise name is in _LOCAL_VIDEO_MAP."""
        import dataclasses
        from web.workout_generator import ExerciseInfo, _LOCAL_VIDEO_MAP
        # Build a minimal ExerciseInfo for BULGARIAN_SPLIT_SQUAT
        ex = ExerciseInfo(
            category="STRENGTH_TRAINING",
            name="BULGARIAN_SPLIT_SQUAT",
            label="Bulgarian Split Squat",
            muscle_group="legs",
            sets=3, reps=10, duration_sec=None, rest_seconds=60,
            link="https://www.youtube.com/watch?v=2C-uNgKwPLE",
            description="",
            video_url=_LOCAL_VIDEO_MAP.get("BULGARIAN_SPLIT_SQUAT"),
        )
        assert ex.video_url == "/static/videos/bulgarian-split-squat.mp4"
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
pytest tests/test_workout_editor.py::TestExerciseInfoVideoUrl -v
```

Expected: `ImportError` — `_LOCAL_VIDEO_MAP` not defined, `video_url` field missing.

---

## Task 3: Add video_url to ExerciseInfo and _LOCAL_VIDEO_MAP

**Files:**
- Modify: `web/workout_generator.py:480-588`

- [ ] **Step 1: Add `video_url` field to `ExerciseInfo`**

In `web/workout_generator.py`, after line 482 (`secondary_muscles` field), add:

```python
    required_equipment_labels: list[str] = field(default_factory=list)
    primary_muscles:   list[str] = field(default_factory=list)
    secondary_muscles: list[str] = field(default_factory=list)
    video_url: str | None = None
```

- [ ] **Step 2: Add `_LOCAL_VIDEO_MAP` just before `def generate(`**

Insert this dict around line 497, before `def generate(`:

```python
# Maps Garmin exercise name keys to local static video paths.
# Add entries here as new AI-generated videos are created.
_LOCAL_VIDEO_MAP: dict[str, str] = {
    "BULGARIAN_SPLIT_SQUAT": "/static/videos/bulgarian-split-squat.mp4",
    "JUMP_SQUAT":            "/static/videos/jump-squat.mp4",
}

```

- [ ] **Step 3: Pass `video_url` in the `ExerciseInfo` constructor**

In `generate()`, the `ExerciseInfo` constructor is around line 574. Add `video_url`:

```python
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
            primary_muscles=tmpl.primary_muscles,
            secondary_muscles=tmpl.secondary_muscles,
            video_url=_LOCAL_VIDEO_MAP.get(tmpl.name),
        )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_workout_editor.py::TestExerciseInfoVideoUrl -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add web/workout_generator.py tests/test_workout_editor.py
git commit -m "feat: add video_url field to ExerciseInfo with local video map"
```

---

## Task 4: Add video tutorial modal and update Tutorial buttons

**Files:**
- Modify: `web/templates/workout_preview.html:184-187` (Jinja2 tutorial button)
- Modify: `web/templates/workout_preview.html:437-442` (JS `exerciseRowHTML` tutorial button)
- Modify: `web/templates/workout_preview.html` (add modal HTML before `{% endblock %}`)

- [ ] **Step 1: Add the video tutorial modal HTML**

After the closing `</div>` of `addModal` (before `{% endblock %}` around line 341), insert:

```html
<!-- =====================================================================
     Video Tutorial Modal
     ===================================================================== -->
<div class="modal fade" id="videoTutorialModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered modal-lg">
    <div class="modal-content border-secondary" style="background:#0d0d0d;">
      <div class="modal-header border-secondary py-2">
        <h6 class="modal-title" id="videoTutorialModalLabel">Tutorial</h6>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body p-0">
        <video id="videoTutorialPlayer" controls playsinline
               style="width:100%;display:block;background:#000;max-height:70vh;">
        </video>
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Update the Jinja2 tutorial button (server-side rendered row)**

Replace lines 184-187 in the Jinja2 `{% for ex in plan.exercises %}` loop:

Old:
```html
                      <a href="{{ ex.link }}" target="_blank" rel="noopener noreferrer"
                         class="btn btn-outline-secondary btn-sm py-0 px-2" title="{{ t('preview_tutorial') }}">
                        <i class="bi bi-play-circle me-1"></i>{{ t("preview_tutorial") }}
                      </a>
```

New:
```html
                      {% if ex.video_url %}
                      <button type="button"
                              class="btn btn-outline-secondary btn-sm py-0 px-2"
                              data-video-url="{{ ex.video_url | e }}"
                              data-video-label="{{ ex.label | e }}"
                              onclick="openVideoTutorial(this.dataset.videoUrl, this.dataset.videoLabel)"
                              title="{{ t('preview_tutorial') }}">
                        <i class="bi bi-play-circle me-1"></i>{{ t("preview_tutorial") }}
                      </button>
                      {% else %}
                      <a href="{{ ex.link }}" target="_blank" rel="noopener noreferrer"
                         class="btn btn-outline-secondary btn-sm py-0 px-2" title="{{ t('preview_tutorial') }}">
                        <i class="bi bi-play-circle me-1"></i>{{ t("preview_tutorial") }}
                      </a>
                      {% endif %}
```

- [ ] **Step 3: Update the JS `tutorialBtn` in `exerciseRowHTML()` (line ~437)**

Replace the `const tutorialBtn = ...` block:

Old:
```js
  const tutorialBtn = ex.link
    ? `<a href="${esc(ex.link)}" target="_blank" rel="noopener noreferrer"
          class="btn btn-outline-secondary btn-sm py-0 px-2" title="${MSG_TUTORIAL}">
         <i class="bi bi-play-circle me-1"></i>${MSG_TUTORIAL}
       </a>`
    : '';
```

New:
```js
  const tutorialBtn = ex.video_url
    ? `<button type="button"
               class="btn btn-outline-secondary btn-sm py-0 px-2"
               data-video-url="${esc(ex.video_url)}"
               data-video-label="${esc(ex.label)}"
               onclick="openVideoTutorial(this.dataset.videoUrl, this.dataset.videoLabel)"
               title="${MSG_TUTORIAL}">
         <i class="bi bi-play-circle me-1"></i>${MSG_TUTORIAL}
       </button>`
    : ex.link
      ? `<a href="${esc(ex.link)}" target="_blank" rel="noopener noreferrer"
            class="btn btn-outline-secondary btn-sm py-0 px-2" title="${MSG_TUTORIAL}">
           <i class="bi bi-play-circle me-1"></i>${MSG_TUTORIAL}
         </a>`
      : '';
```

- [ ] **Step 4: Add `openVideoTutorial` to the JS IIFE**

Add this function just before the `window.*` exports block (near line 874):

```js
/* -----------------------------------------------------------------------
   Video Tutorial Modal
   --------------------------------------------------------------------- */
function openVideoTutorial(url, label) {
  const player = document.getElementById('videoTutorialPlayer');
  const title  = document.getElementById('videoTutorialModalLabel');
  player.setAttribute('src', url);
  title.textContent = label;
  bootstrap.Modal.getOrCreateInstance(
    document.getElementById('videoTutorialModal')
  ).show();
}

document.getElementById('videoTutorialModal').addEventListener('hide.bs.modal', () => {
  const player = document.getElementById('videoTutorialPlayer');
  player.pause();
  player.removeAttribute('src');
  player.load();
});
```

- [ ] **Step 5: Export `openVideoTutorial` on window**

In the `window.*` exports block, add:

```js
window.openVideoTutorial = openVideoTutorial;
```

- [ ] **Step 6: Manual verification**

Run `python run.py`, generate a workout with dumbbells (to get Bulgarian Split Squat), and verify:
- Bulgarian Split Squat "Tutorial" button is a `<button>` (not an `<a>` tag)
- Clicking it opens the video modal and plays the MP4
- Closing the modal pauses and clears the video
- A non-video exercise still shows a YouTube `<a>` link

- [ ] **Step 7: Commit**

```bash
git add web/templates/workout_preview.html
git commit -m "feat: inline video tutorial modal for exercises with local MP4"
```

---

## Task 5: Add Play Workout button and player modal HTML

**Files:**
- Modify: `web/templates/workout_preview.html:96-104` (card header)
- Modify: `web/templates/workout_preview.html` (add player modal before `{% endblock %}`)

- [ ] **Step 1: Update the card header to include a Play button**

Replace lines 96-104:

Old:
```html
      <div class="card-header border-secondary d-flex align-items-center justify-content-between">
        <div>
          <span class="fs-3 me-2">{{ plan.goal_icon }}</span>
          <span class="fw-bold fs-5">{{ plan.name }}</span>
        </div>
        <span class="badge bg-garmin">
          <i class="bi bi-clock me-1"></i>{{ plan.duration_minutes }} {{ t("form_min") }}
        </span>
      </div>
```

New:
```html
      <div class="card-header border-secondary d-flex align-items-center justify-content-between">
        <div>
          <span class="fs-3 me-2">{{ plan.goal_icon }}</span>
          <span class="fw-bold fs-5">{{ plan.name }}</span>
        </div>
        <div class="d-flex align-items-center gap-2">
          <button type="button" class="btn btn-success btn-sm fw-semibold" id="playBtn">
            <i class="bi bi-play-fill me-1"></i>Play
          </button>
          <span class="badge bg-garmin">
            <i class="bi bi-clock me-1"></i>{{ plan.duration_minutes }} {{ t("form_min") }}
          </span>
        </div>
      </div>
```

- [ ] **Step 2: Add the workout player modal HTML**

Add this block after the video tutorial modal (before `{% endblock %}`):

```html
<!-- =====================================================================
     Workout Player Modal
     ===================================================================== -->
<div class="modal fade" id="workoutPlayerModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-fullscreen">
    <div class="modal-content border-0" style="background:#0a0a0a;color:#fff;">

      <!-- Header -->
      <div class="modal-header border-0 px-4 pt-3 pb-0">
        <span class="text-muted small" id="playerRoundLabel">Round 1 of 3</span>
        <button type="button" class="btn-close btn-close-white ms-auto"
                data-bs-dismiss="modal" id="playerCloseBtn"></button>
      </div>

      <!-- Body -->
      <div class="modal-body d-flex flex-column align-items-center justify-content-center px-4 py-2"
           style="gap:16px;flex:1;">

        <!-- Video / thumbnail / fallback area -->
        <div id="playerMediaArea"
             style="width:100%;max-width:560px;aspect-ratio:16/9;border-radius:12px;overflow:hidden;background:#111;display:flex;align-items:center;justify-content:center;">
        </div>

        <!-- Exercise name -->
        <h1 id="playerExerciseName" class="text-center fw-bold mb-0"
            style="font-size:clamp(1.4rem,5vw,2.2rem);letter-spacing:-.01em;">
          Get Ready
        </h1>

        <!-- Timer / rep count -->
        <div id="playerTimer"
             style="font-size:clamp(3rem,15vw,6rem);font-weight:800;line-height:1;color:#4ade80;font-variant-numeric:tabular-nums;">
          5
        </div>

        <!-- Step indicator -->
        <div id="playerStepLabel" class="text-muted" style="font-size:.9rem;">
          Step 1 of 18
        </div>

        <!-- Progress bar -->
        <div style="width:100%;max-width:560px;background:#222;border-radius:4px;height:6px;">
          <div id="playerProgress"
               style="background:#4ade80;height:6px;border-radius:4px;width:0%;transition:width .4s ease;">
          </div>
        </div>

        <!-- Controls -->
        <div class="d-flex gap-3 mt-2">
          <button type="button" class="btn btn-outline-light px-4 py-2 fw-semibold"
                  id="playerPauseBtn">
            <i class="bi bi-pause-fill" id="playerPauseIcon"></i>
            <span id="playerPauseLabel" class="ms-1">Pause</span>
          </button>
          <button type="button" class="btn btn-outline-secondary px-4 py-2" id="playerSkipBtn">
            <i class="bi bi-skip-forward-fill me-1"></i>Skip
          </button>
        </div>

      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Manual check (no JS yet)**

Run `python run.py`, generate a workout, verify "Play" button appears in the card header. Clicking it does nothing yet — that's expected.

- [ ] **Step 4: Commit**

```bash
git add web/templates/workout_preview.html
git commit -m "feat: add Play button and workout player modal scaffold"
```

---

## Task 6: Add workout player JavaScript state machine

**Files:**
- Modify: `web/templates/workout_preview.html` — append inside the IIFE just before the final `})();`

- [ ] **Step 1: Add the player state machine**

Locate the closing `})();` of the IIFE (last line of the `<script>` block, around line 944). Insert the following block immediately before it:

```js
/* =======================================================================
   Workout Player
   ======================================================================= */

// ── State ──────────────────────────────────────────────────────────────
let playerQueue    = [];
let playerIndex    = 0;
let playerTimeLeft = 0;
let playerInterval = null;
let playerPaused   = false;
let playerWakeLock = null;

// ── TTS ────────────────────────────────────────────────────────────────
function playerSpeak(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
}

// ── Wake Lock ──────────────────────────────────────────────────────────
async function playerAcquireWakeLock() {
  if (!('wakeLock' in navigator)) return;
  try { playerWakeLock = await navigator.wakeLock.request('screen'); } catch (_) {}
}
function playerReleaseWakeLock() {
  if (playerWakeLock) { playerWakeLock.release(); playerWakeLock = null; }
}

// ── Queue builder ──────────────────────────────────────────────────────
function buildPlayerQueue(exs) {
  const queue = [{ type: 'warmup', duration: 5 }];
  const rounds = exs.length ? exs[0].sets : 1;
  for (let r = 0; r < rounds; r++) {
    for (let i = 0; i < exs.length; i++) {
      const ex     = exs[i];
      const nextEx = exs[(i + 1) % exs.length];
      queue.push({ type: 'exercise', ex, round: r + 1, rounds });
      if (ex.rest_seconds > 0) {
        queue.push({ type: 'rest', ex, round: r + 1, rounds, nextEx });
      }
    }
  }
  queue.push({ type: 'complete' });
  return queue;
}

// ── YouTube video-ID helper ────────────────────────────────────────────
function youtubeId(url) {
  if (!url) return null;
  const m = String(url).match(/[?&]v=([^&]+)/);
  return m ? m[1] : null;
}

// ── Media area renderer (uses createElement — no innerHTML) ────────────
function renderMediaArea(step) {
  const area = document.getElementById('playerMediaArea');
  area.replaceChildren();                     // clear safely

  if (step.type !== 'exercise') {
    area.style.display = 'none';
    return;
  }
  area.style.display = 'flex';

  const ex = step.ex;
  if (ex.video_url) {
    const video = document.createElement('video');
    video.setAttribute('src', ex.video_url);
    video.autoplay = true;
    video.loop     = true;
    video.muted    = true;
    video.setAttribute('playsinline', '');
    video.style.cssText = 'width:100%;height:100%;object-fit:cover;';
    area.appendChild(video);
  } else {
    const vid = youtubeId(ex.link);
    if (vid) {
      const img = document.createElement('img');
      img.setAttribute('src', 'https://img.youtube.com/vi/' + vid + '/hqdefault.jpg');
      img.alt = ex.label;
      img.style.cssText = 'width:100%;height:100%;object-fit:cover;';
      area.appendChild(img);
    } else {
      // Fallback: name + muscle group card
      const wrap   = document.createElement('div');
      wrap.style.cssText = 'text-align:center;padding:16px;';
      const icon   = document.createElement('div');
      icon.style.fontSize = '3rem';
      icon.textContent = '\uD83C\uDFCB\uFE0F';   // 🏋️
      const lbl    = document.createElement('div');
      lbl.style.cssText = 'font-size:1rem;font-weight:600;color:#ccc;margin-top:8px;';
      lbl.textContent = ex.label;
      const muscle = document.createElement('div');
      muscle.style.cssText = 'font-size:.8rem;color:#666;margin-top:4px;';
      muscle.textContent = ex.muscle_group.replace(/_/g, ' ');
      wrap.append(icon, lbl, muscle);
      area.appendChild(wrap);
    }
  }
}

// ── UI updater ────────────────────────────────────────────────────────
function renderPlayerStep() {
  const step  = playerQueue[playerIndex];
  const total = playerQueue.length - 1;      // last item is 'complete'
  const pct   = Math.round((playerIndex / Math.max(total, 1)) * 100);

  document.getElementById('playerProgress').style.width = pct + '%';
  document.getElementById('playerStepLabel').textContent =
    'Step ' + (playerIndex + 1) + ' of ' + total;

  renderMediaArea(step);

  const nameEl  = document.getElementById('playerExerciseName');
  const timerEl = document.getElementById('playerTimer');
  const roundEl = document.getElementById('playerRoundLabel');

  if (step.type === 'warmup') {
    roundEl.textContent  = 'Get Ready';
    nameEl.textContent   = 'Get Ready';
    timerEl.textContent  = String(playerTimeLeft);
    timerEl.style.color  = '#facc15';

  } else if (step.type === 'exercise') {
    roundEl.textContent = 'Round ' + step.round + ' of ' + step.rounds;
    nameEl.textContent  = step.ex.label;
    timerEl.style.color = '#4ade80';
    timerEl.textContent = step.ex.duration_sec
      ? String(playerTimeLeft)
      : '\u00D7\u00A0' + step.ex.reps;

  } else if (step.type === 'rest') {
    roundEl.textContent = 'Round ' + step.round + ' of ' + step.rounds;
    nameEl.textContent  = 'Rest \u00B7 Next: ' + step.nextEx.label;
    timerEl.textContent = String(playerTimeLeft);
    timerEl.style.color = '#60a5fa';

  } else if (step.type === 'complete') {
    roundEl.textContent  = '';
    nameEl.textContent   = 'Workout Complete!';
    timerEl.textContent  = '\uD83C\uDF89';   // 🎉
    timerEl.style.color  = '#4ade80';
    document.getElementById('playerStepLabel').textContent = 'Great work!';
    document.getElementById('playerProgress').style.width  = '100%';
    document.getElementById('playerSkipBtn').disabled      = true;
    playerReleaseWakeLock();
    if (window.speechSynthesis) window.speechSynthesis.cancel();
  }
}

// ── Advance to next step ──────────────────────────────────────────────
function playerAdvance() {
  clearInterval(playerInterval);
  playerInterval = null;
  if (playerIndex < playerQueue.length - 1) playerIndex++;
  playerStartStep();
}

// ── Start a step ─────────────────────────────────────────────────────
function playerStartStep() {
  const step = playerQueue[playerIndex];

  if (step.type === 'warmup') {
    playerTimeLeft = step.duration;
    playerSpeak('Get ready');
    renderPlayerStep();
    playerInterval = setInterval(() => {
      playerTimeLeft--;
      if (playerTimeLeft <= 0) { playerAdvance(); return; }
      renderPlayerStep();
    }, 1000);

  } else if (step.type === 'exercise') {
    if (step.ex.duration_sec) {
      playerTimeLeft = Math.round(step.ex.duration_sec);
      playerSpeak('Exercise: ' + step.ex.label + ', ' + playerTimeLeft + ' seconds');
      renderPlayerStep();
      playerInterval = setInterval(() => {
        playerTimeLeft--;
        if (playerTimeLeft <= 0) { playerAdvance(); return; }
        renderPlayerStep();
      }, 1000);
    } else {
      playerTimeLeft = 0;
      playerSpeak('Exercise: ' + step.ex.label + ', ' + step.ex.reps + ' reps');
      renderPlayerStep();
      // Rep-based: user taps Skip when done — no auto-advance
    }

  } else if (step.type === 'rest') {
    playerTimeLeft = Math.round(step.ex.rest_seconds);
    playerSpeak('Rest, ' + playerTimeLeft + ' seconds');
    renderPlayerStep();
    playerInterval = setInterval(() => {
      playerTimeLeft--;
      if (playerTimeLeft <= 0) {
        if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
        playerAdvance();
        return;
      }
      renderPlayerStep();
    }, 1000);

  } else if (step.type === 'complete') {
    renderPlayerStep();
    playerSpeak('Workout complete. Great work!');
  }
}

// ── Pause / Resume ────────────────────────────────────────────────────
document.getElementById('playerPauseBtn').addEventListener('click', () => {
  const iconEl  = document.getElementById('playerPauseIcon');
  const labelEl = document.getElementById('playerPauseLabel');
  if (playerPaused) {
    playerPaused = false;
    iconEl.className  = 'bi bi-pause-fill';
    labelEl.textContent = 'Pause';
    const step = playerQueue[playerIndex];
    const isTimed = step.type === 'warmup' || step.type === 'rest' ||
                    (step.type === 'exercise' && step.ex.duration_sec);
    if (isTimed && playerTimeLeft > 0) {
      playerInterval = setInterval(() => {
        playerTimeLeft--;
        if (playerTimeLeft <= 0) { playerAdvance(); return; }
        renderPlayerStep();
      }, 1000);
    }
  } else {
    playerPaused = true;
    clearInterval(playerInterval);
    playerInterval = null;
    iconEl.className  = 'bi bi-play-fill';
    labelEl.textContent = 'Resume';
  }
});

// ── Skip ──────────────────────────────────────────────────────────────
document.getElementById('playerSkipBtn').addEventListener('click', () => {
  playerAdvance();
});

// ── Close ─────────────────────────────────────────────────────────────
document.getElementById('playerCloseBtn').addEventListener('click', () => {
  clearInterval(playerInterval);
  playerInterval = null;
  playerReleaseWakeLock();
  if (window.speechSynthesis) window.speechSynthesis.cancel();
});

// ── Launch ────────────────────────────────────────────────────────────
document.getElementById('playBtn').addEventListener('click', () => {
  clearInterval(playerInterval);
  playerInterval   = null;
  playerPaused     = false;
  playerIndex      = 0;
  playerQueue      = buildPlayerQueue(exercises);

  document.getElementById('playerPauseIcon').className   = 'bi bi-pause-fill';
  document.getElementById('playerPauseLabel').textContent = 'Pause';
  document.getElementById('playerSkipBtn').disabled       = false;

  playerAcquireWakeLock();
  bootstrap.Modal.getOrCreateInstance(
    document.getElementById('workoutPlayerModal')
  ).show();
  playerStartStep();
});
```

- [ ] **Step 2: Manual end-to-end verification**

Run `python run.py`, generate a workout, click **Play**, and verify:

1. **Warmup:** 5-second countdown (yellow), TTS says "Get ready"
2. **Timed exercise (e.g. Plank):** Countdown in green, TTS says "Exercise: Plank, 30 seconds"
3. **Rep exercise (e.g. Goblet Squat):** Shows "× 12", no auto-advance, TTS says reps count
4. **Rest:** Blue countdown, TTS says "Rest, 60 seconds", vibration on mobile at rest-end
5. **Round label:** "Round 1 of 3" increments each round
6. **Progress bar:** Fills as steps complete
7. **Bulgarian Split Squat:** Video plays in media area
8. **Other exercises:** YouTube thumbnail or fallback card shows
9. **Pause:** Timer freezes, button shows "Resume"
10. **Resume:** Timer continues from where it stopped
11. **Complete:** Shows "Workout Complete! 🎉", Skip disabled
12. **Close (×):** Timer stops, wake lock released, TTS cancelled

- [ ] **Step 3: Commit**

```bash
git add web/templates/workout_preview.html
git commit -m "feat: workout player state machine with TTS, wake lock, video, and vibration"
```

---

## Verification Summary

| Check | Command / Action |
|-------|-----------------|
| Videos served | `curl -I http://localhost:8000/static/videos/bulgarian-split-squat.mp4` → 200 |
| `video_url` tests | `pytest tests/test_workout_editor.py::TestExerciseInfoVideoUrl -v` → 3 PASS |
| Full test suite | `pytest -v` → all PASS |
| Tutorial modal | Generate workout with dumbbells → Tutorial on Bulgarian Split Squat → MP4 plays inline |
| Player full flow | Generate → Play → walk through all 6 state types |
| Mobile | Open on phone → screen stays on, vibration fires at rest-end |
| No-video fallback | Non-video exercise → YouTube thumbnail shows in player |
