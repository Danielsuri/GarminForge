# GarminForge Enhancement Plan

## Overview

Three enhancements to make GarminForge useful beyond Garmin uploads:

1. **In-browser Workout Player** — run the workout on your phone/browser with timers, TTS announcements, rest countdowns, no Garmin needed
2. **PDF/Print Export** — one-click printable workout sheet from the preview page
3. **Raspberry Pi + Cloudflare Tunnel** — permanent public HTTPS URL for alpha users

---

## Enhancement 1: In-browser Workout Player

### Goal

"Play" button on the preview page opens a fullscreen player. It walks through exercises and rest periods using a countdown timer, announces each exercise by name via Web Speech API, keeps the screen on (Wake Lock), and vibrates at rest-end.

### Data available (no new backend needed)

`plan.exercises` (list of `ExerciseInfo`) has everything:
- `label` — spoken name
- `sets` — rounds (all exercises share the same sets count in circuit mode)
- `reps` / `duration_sec` — determines timer vs rep display
- `rest_seconds` — rest after each exercise

Serialize `plan.exercises` to JSON in `workout_preview.html` (same pattern as `payload_json`):
```html
<script id="workout-data" type="application/json">{{ exercises_json | safe }}</script>
```

Pass `exercises_json` from `app.py`'s `/workout/generate` route alongside `payload_json`.

### Files to modify

| File | Change |
|------|--------|
| `web/app.py` | Add `exercises_json = json.dumps([asdict(e) for e in plan.exercises])` and pass to template |
| `web/templates/workout_preview.html` | Add Play button, embed `exercises_json`, add fullscreen modal HTML |
| `web/templates/workout_preview.html` | Add `{% block scripts %}` with player JS state machine |

### Player architecture (pure vanilla JS, no new deps)

**State machine:**
```
IDLE → WARMUP (5s countdown) → EXERCISE → REST → [next exercise or next round] → COOLDOWN → COMPLETE
```

**Exercise queue:**
```js
// rounds = exercises[0].sets
// queue = for r in range(rounds): for ex in exercises: [EXERCISE(ex), REST(ex.rest_seconds)]
```

**Player UI (Bootstrap fullscreen modal):**
- Large exercise name (centered, h1)
- Large countdown timer or static rep count (e.g., "× 12")
- Progress bar (step N of total)
- Round indicator ("Round 2 of 3")
- Pause / Skip buttons
- Auto-advances; on COMPLETE shows summary

**Web Speech API (best-effort):**
```js
const synth = window.speechSynthesis;
function announce(text) { synth.speak(new SpeechSynthesisUtterance(text)); }
// "Exercise: Goblet Squat, 10 reps"
// "Rest, 60 seconds"
// "Round 2 complete"
```

**Wake Lock API:**
```js
let wakeLock = null;
async function requestWakeLock() {
  if ('wakeLock' in navigator) wakeLock = await navigator.wakeLock.request('screen');
}
// Release on complete/close
```

**Timed exercises** (`duration_sec != null`): show countdown. Otherwise show static rep count.

**Vibration** (mobile): `navigator.vibrate([200, 100, 200])` when rest ends.

### Implementation steps

1. `app.py`: import `dataclasses.asdict`, compute `exercises_json`, pass to template
2. Add Play button to preview card header (alongside Upload button)
3. Add fullscreen Bootstrap modal HTML to `workout_preview.html`
4. Add `<script id="workout-data" type="application/json">` tag
5. Write JS state machine in `{% block scripts %}`:
   - Parse workout data from script tag
   - Build exercise queue (rounds × exercises)
   - `setInterval`-based countdown for timed phases
   - Update DOM on each tick
   - Speech + Wake Lock + Vibration hooks

---

## Enhancement 2: PDF / Print Export

### Goal

"Print / Save as PDF" button on the preview page renders a clean one-page workout sheet.

### Implementation (pure CSS + one button, no new deps)

**Files to modify:**
- `web/templates/workout_preview.html` — add print styles + Print button

**CSS:**
```css
@media print {
  nav, .btn-toolbar, .player-modal { display: none !important; }
  .workout-card { box-shadow: none; border: none; }
  body { font-size: 11pt; }
}
```

**Button:**
```html
<button class="btn btn-outline-secondary" onclick="window.print()">
  <i class="bi bi-printer"></i> Print / PDF
</button>
```

No backend changes required — the exercise table already contains all needed information.

---

## Enhancement 3: Raspberry Pi + Cloudflare Tunnel

### Goal

Permanent public HTTPS URL so alpha users can access the app from outside the local network.

### Steps (one-time setup on Pi)

**1. Install cloudflared:**
```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb
```

**2. Bind app to 0.0.0.0** (change `run.py`):
```python
# Before: host="127.0.0.1"
uvicorn.run("web.app:app", host="0.0.0.0", port=8000, reload=args.reload)
```

**3. Named tunnel (permanent URL):**
```bash
cloudflared tunnel login
cloudflared tunnel create garminforge
cloudflared tunnel route dns garminforge garminforge.yourdomain.com
```

Config file at `~/.cloudflared/config.yml`:
```yaml
tunnel: <tunnel-id>
credentials-file: /home/pi/.cloudflared/<tunnel-id>.json
ingress:
  - hostname: garminforge.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

**4. Run as systemd service:**
```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

**5. Multi-user token isolation check:**
Token string is already stored per-session in the Starlette session cookie.
Verify `GarminForgeClient` is constructed per-request in `app.py` (not a shared global).

### Files to modify
- `run.py` — change host to `0.0.0.0`

---

## Suggested implementation order

1. `run.py` host fix — 5 min, unblocks Pi + phone testing
2. PDF print button + CSS — 15 min, immediate value
3. Workout Player — primary feature, ~2–3 hours:
   - `app.py`: exercises_json
   - Modal HTML + Play button
   - JS state machine
   - Speech + Wake Lock + Vibration
4. Cloudflare Tunnel setup (follow steps above, no code changes beyond `run.py`)

---

## Verification

**Player:**
- Generate a workout → click Play → verify exercise names announced, timer counts down, rest phase shows, round indicator increments
- Mobile: Wake Lock keeps screen on, vibration fires at rest-end
- Timed exercise (CORE goal includes PLANK): verify countdown shown, not rep count

**PDF:**
- Generate workout → click Print / PDF → nav and buttons hidden, exercise table clean

**Pi + Tunnel:**
- `curl https://garminforge.yourdomain.com/` from external network → 200 OK
- Open incognito tab and verify separate session (no token leak between users)
