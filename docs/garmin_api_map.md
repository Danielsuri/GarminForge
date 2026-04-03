# Garmin workout-service API map

Verified empirically from live `/workout-service/workout` and `/workout-service/workouts`
responses on a real account. These values differ from the FIT SDK, the `garminconnect`
library's `SportType` enum, and most unofficial documentation.

---

## Sport types (`sportType` object)

Used in the top-level workout payload **and** in each `workoutSegments[]` entry.

| sportTypeId | sportTypeKey      | displayOrder | Notes                               |
|-------------|-------------------|--------------|-------------------------------------|
| 1           | running           | 1            | confirmed                           |
| 4           | swimming          | 3            | **pool swim — NOT strength_training** |
| 5           | strength_training | 5            | confirmed from live workout GET     |

> **Trap**: old docs and some libraries list `sportTypeId: 4` as strength training.
> Garmin's server silently remaps it to pool swimming. Always use `id=5` for strength.

Example payload fragment:
```json
"sportType": {"sportTypeId": 5, "sportTypeKey": "strength_training", "displayOrder": 5}
```

---

## Step schema

All steps require a `"type"` discriminator field. Values confirmed from live workout GET:

| `type`             | `stepTypeId` | `stepTypeKey` | `displayOrder` | Use                        |
|--------------------|--------------|---------------|----------------|----------------------------|
| `ExecutableStepDTO`| 1            | warmup        | 1              | Warmup step                |
| `ExecutableStepDTO`| 2            | cooldown      | 2              | Cooldown step              |
| `ExecutableStepDTO`| 3            | interval      | 3              | Exercise / active interval |
| `ExecutableStepDTO`| 4            | recovery      | 4              | Recovery (used by Garmin UI for between-exercise rest) |
| `ExecutableStepDTO`| 5            | rest          | 5              | Rest between sets          |
| `RepeatGroupDTO`   | 6            | repeat        | 6              | Repeat / sets group        |

### End conditions (`endCondition` + `endConditionValue`)

The `endCondition` object holds **only type metadata** — no value.
The actual value goes in `endConditionValue` at the **step level** (not inside `endCondition`).

| conditionTypeId | conditionTypeKey | displayOrder | displayable | endConditionValue unit |
|-----------------|------------------|--------------|-------------|------------------------|
| 1               | lap.button       | 1            | true        | null                   |
| 2               | time             | 2            | true        | seconds (float)        |
| 3               | distance         | 3            | true        | meters (float)         |
| 7               | reps             | 7            | true        | rep count (float)      |
| 7               | iterations       | 7            | false       | set count (float) — used in RepeatGroupDTO |

> **Note**: both `reps` and `iterations` use `conditionTypeId: 7`. `displayable: false`
> on the iterations condition hides it from the Garmin UI.

### Exercise step field names

| Field          | Correct key      | Wrong key (do not use) |
|----------------|------------------|------------------------|
| Exercise category | `"category"`  | ~~`"exerciseCategory"`~~ |
| Exercise name  | `"exerciseName"` | —                      |

Values must be ALL_CAPS_SNAKE_CASE matching Garmin's FIT SDK catalog,
e.g. `"category": "SQUAT"`, `"exerciseName": "GOBLET_SQUAT"`.

### RepeatGroupDTO required fields

```json
{
  "type": "RepeatGroupDTO",
  "stepOrder": 2,
  "stepType": {"stepTypeId": 6, "stepTypeKey": "repeat", "displayOrder": 6},
  "numberOfIterations": 3,
  "endCondition": {"conditionTypeId": 7, "conditionTypeKey": "iterations", "displayOrder": 7, "displayable": false},
  "endConditionValue": 3.0,
  "workoutSteps": [...]
}
```

### Target type (`targetType`)

| workoutTargetTypeId | workoutTargetTypeKey | displayOrder |
|---------------------|----------------------|--------------|
| 1                   | no.target            | 1            |
| 4                   | heart.rate.zone      | 4            |
| 6                   | pace.zone            | 6            |

---

## SSO login flow (new portal, verified from browser capture)

The new Garmin SSO portal (live as of 2026) uses a different API than the old `/mobile/api/login` (blocked) and the embed page we use with Playwright.

**Step 1 — load portal page (sets session cookies):**
```
GET https://sso.garmin.com/portal/sso/en-US/sign-in
    ?clientId=GarminConnect&service=https://connect.garmin.com/app
```

**Step 2 — submit credentials:**
```
POST https://sso.garmin.com/portal/api/login
     ?clientId=GarminConnect&locale=en-US&service=https://connect.garmin.com/app
Content-Type: application/json

{"username": "...", "password": "...", "rememberMe": true, "captchaToken": ""}
```
- `captchaToken` is empty string when no CAPTCHA is shown (typical for trusted IPs)
- Response redirects to `https://connect.garmin.com/app?ticket=ST-...`

**Step 3 — extract ticket from redirect URL and exchange for OAuth tokens** (same as current Playwright flow).

> **CAPTCHA wall (confirmed 2026-04-03)**: Garmin always returns `CAPTCHA_REQUIRED` for new
> headless sessions even with a correct Chrome TLS fingerprint (curl_cffi). The response body is:
> `{"responseStatus": {"type": "CAPTCHA_REQUIRED"}, "captchaAlreadyPassed": false, ...}`
>
> Headless login works in a real browser because it has prior session cookies/history.
> **Playwright browser login remains the only reliable login method for new sessions.**
> The portal API is still useful if Garmin ever relaxes CAPTCHA for trusted IPs.
>
> **⚠ WARNING**: Never commit files containing credentials. `examples/` is in `.gitignore`.

---

## API call notes

- **All** API calls must use `_garth(client).connectapi(path, method=..., json=...)` directly.
  `garminconnect.connectapi` hardcodes `"GET"` and checks its own auth state separately —
  it will fail when tokens are loaded via `garth.loads()`.
- Schedule workout: `POST /workout-service/schedule/{workout_id}` with `{"date": "YYYY-MM-DD"}`
- Upload workout: `POST /workout-service/workout`
- Get workout: `GET /workout-service/workout/{workout_id}`
- List workouts: `GET /workout-service/workouts?start=0&limit=20`

---

## Top-level workout payload shape

```json
{
  "workoutName": "My Workout",
  "sportType": {"sportTypeId": 5, "sportTypeKey": "strength_training", "displayOrder": 5},
  "estimatedDurationInSecs": 1380,
  "description": "optional",
  "workoutSegments": [
    {
      "segmentOrder": 1,
      "sportType": {"sportTypeId": 5, "sportTypeKey": "strength_training", "displayOrder": 5},
      "workoutSteps": [...]
    }
  ]
}
```
