# Koda UI Redesign — Design Spec
**Date:** 2026-04-08  
**Scope:** Full visual redesign of all web templates + rebrand from GarminForge to Koda  
**Approach:** Complete template rebuild — every page redesigned from scratch in Koda's visual language

---

## 1. Brand Identity

### Name & Logo
- **Brand name:** Koda (replaces GarminForge everywhere — titles, nav, headings, page `<title>`, metadata)
- **Logo mark:** φ (coda symbol) — a circle with a horizontal and vertical crosshair line through its center. Rendered purely in CSS at three sizes:
  - 64px — hero/splash contexts
  - 32px — navbar
  - 24px — inline / favicon fallback
- **Wordmark:** `KODA` in Inter 800, letter-spacing 2.5px, uppercase, always paired with the φ mark

### Brand Meaning (informs copy and UX voice)
- **The Ally** — reliable, silent partner
- **The Resolution (Coda)** — satisfying execution of a structured plan
- **The System (Code)** — precision infrastructure, data-driven

### Voice
- Analytical, grounded, succinct — never hype
- ✅ "Target pace achieved. Maintain cadence."
- ❌ "CRUSH YOUR GOALS! NO EXCUSES!"
- Motivational quotes drawn from the Koda ethos (rotating):
  - "The steady baseline compounds."
  - "Structure is the edge you need."
  - "Turn intention into architecture."
  - "Consistency is the infrastructure."
  - "Precision over hype. Every session."

---

## 2. Design System

### 2.1 Color Palette

**Backgrounds (darkest → lightest)**

| Token | Hex | Usage |
|---|---|---|
| `--color-canvas` | `#090b14` | `<body>` background |
| `--color-surface` | `#0d1117` | page-level surface |
| `--color-card` | `#111827` | standard cards |
| `--color-card-raised` | `#1a2035` | elevated/active cards |
| `--color-hero-bg` | `#0e0b1f` | hero/atmospheric sections |

**Brand (Violet / Indigo)**

| Token | Hex | Usage |
|---|---|---|
| `--color-brand-deep` | `#4c1d95` | deep accents |
| `--color-brand-dark` | `#6d28d9` | gradient start |
| `--color-brand` | `#7c3aed` | primary accent, borders, labels |
| `--color-brand-mid` | `#8b5cf6` | interactive states |
| `--color-brand-light` | `#a78bfa` | highlights, numbers, headlines |
| `--color-brand-pale` | `#ddd6fe` | very subtle tints |

**Primary button gradient:** `linear-gradient(135deg, #7c3aed, #a78bfa)`

**Semantic**

| Token | Hex | Usage |
|---|---|---|
| `--color-success` | `#16a34a` / `#4ade80` | completion, uploaded, Garmin connected badge |
| `--color-warning` | `#d97706` / `#fbbf24` | in-progress, partial |
| `--color-danger` | `#dc2626` / `#f87171` | delete, error |
| `--color-info` | `#0284c7` | informational |

**Text**

| Token | Usage |
|---|---|
| `#ffffff` | Primary headings |
| `rgba(255,255,255,0.75)` | Body text |
| `rgba(255,255,255,0.45)` | Secondary / meta text |
| `rgba(255,255,255,0.25)` | Muted / timestamps |
| `#a78bfa` | Accent text (labels, numbers, active states) |

### 2.2 Typography

**Three-font system — all loaded from Google Fonts:**

| Role | Font | Weight | Usage |
|---|---|---|---|
| Display | **Syne** | 700, 800 | Hero headlines, motivational quotes, page titles |
| UI | **Inter** | 400, 500, 600, 700, 800 | All interface text — nav, labels, body, buttons |
| Data/Mono | **JetBrains Mono** | 500, 700 | Rep counts, timers, pacing, dates, metrics, code-like values |

**Type scale:**

| Element | Font | Size | Weight | Transform | Letter-spacing |
|---|---|---|---|---|---|
| Hero headline | Syne | 44px (desktop) / 26px (mobile) | 800 | — | — |
| Page title | Syne | 30px | 800 | — | — |
| Greeting | Syne | 26px | 800 | — | — |
| Card title | Inter | 16px | 700 | — | — |
| Body | Inter | 14px | 400/500 | — | — |
| Section label | Inter | 10–11px | 600 | uppercase | 3px |
| Metric value | JetBrains Mono | 22–28px | 700 | — | — |
| Meta / date | JetBrains Mono | 11px | 500 | — | — |
| Badge text | Inter | 10px | 600 | — | 0.5px |

### 2.3 Spacing & Radius
- Base unit: 4px
- Card padding: 18–24px
- Page content padding: 28–32px
- Card border-radius: 14px (cards), 10px (inner blocks), 8px (inputs/buttons), 20px (badges/pills)
- Navbar height: 54px

### 2.4 Elevation & Glow
- Standard card: `border: 1px solid rgba(255,255,255,0.07)`
- Active/highlighted card: `border: 1px solid rgba(124,58,237,0.4); box-shadow: 0 0 40px rgba(124,58,237,0.08)`
- Focus ring: `box-shadow: 0 0 0 3px rgba(124,58,237,0.15)`
- Hero glow: `radial-gradient(circle, rgba(124,58,237,0.12–0.18) 0%, transparent 70%)` — absolute positioned, bottom-left of hero sections
- Grid texture on hero backgrounds: `repeating-linear-gradient` at 0° and 90°, `rgba(124,58,237,0.03–0.05)`, 50–60px cells

### 2.5 Component Library

**Buttons**
- Primary: gradient background, white text, `border-radius: 8px`, `padding: 10–14px 18–22px`, `font-weight: 700`
- Secondary: `background: rgba(124,58,237,0.12)`, `border: 1px solid rgba(124,58,237,0.35)`, `color: #a78bfa`
- Ghost: transparent, `border: 1px solid rgba(255,255,255,0.12)`, `color: rgba(255,255,255,0.6)`
- Danger: `background: rgba(239,68,68,0.12)`, `border: 1px solid rgba(239,68,68,0.3)`, `color: #f87171`
- Play (workout): green gradient `linear-gradient(135deg, #22c55e, #16a34a)`, circular, pulsing ring animation

**Badges**
- Violet, Green, Amber, Red, Slate variants (see color tokens above)
- `border-radius: 20px`, `padding: 3px 10px`, `font-size: 10px`, `font-weight: 600`

**Inputs**
- Default: `background: rgba(255,255,255,0.05)`, `border: 1px solid rgba(255,255,255,0.1)`, `border-radius: 8px`, `padding: 11px 14px`
- Focused: `background: rgba(124,58,237,0.07)`, `border-color: rgba(124,58,237,0.6)`, focus ring

**Progress bars**
- Track: `height: 4–5px`, `background: rgba(255,255,255,0.07)`, `border-radius: 3px`
- Fill: `background: linear-gradient(90deg, #7c3aed, #a78bfa)`

**Stat cards**
- `background: rgba(124,58,237,0.08)`, `border: 1px solid rgba(124,58,237,0.18)`, `border-radius: 12px`
- Value: JetBrains Mono 22–28px, `color: #a78bfa`
- Label: 9px uppercase, letter-spacing 2px, `color: rgba(255,255,255,0.3)`

**Motivational quote block**
- `border-left: 3px solid #7c3aed`, `border-radius: 0 12px 12px 0`, `padding: 16px 20px`
- Background: `linear-gradient(135deg, rgba(124,58,237,0.1), rgba(167,139,250,0.05))`
- Text: Syne 16px 700

---

## 3. Navigation Bar

- Height: 54px, `background: rgba(13,17,23,0.97)`, `backdrop-filter: blur(12px)`
- `border-bottom: 1px solid rgba(124,58,237,0.15)`
- Left: φ mark (32px) + `KODA` wordmark
- Center: nav links — Generate · My Plans · Programs · Progress
  - Active: `color: #a78bfa`, `background: rgba(124,58,237,0.12)`, `border-radius: 6px`
  - Inactive: `color: rgba(255,255,255,0.45)`
- Right: Garmin Connected badge (green dot + "Connected") + avatar circle (initials, gradient bg)
- Mobile: hamburger menu, links collapse into a full-width slide-down drawer

---

## 4. Pages

### 4.1 Login / Landing (`/`, `/login`)

**Desktop layout:** Two-column split, `min-height: 100vh`

**Left panel — cinematic hero:**
- Background: `linear-gradient(160deg, #0e0b1f, #130d2a, #0a0f1e)`
- Grid texture overlay (see §2.4)
- Violet radial glow, bottom-left and top-right
- Top-left: φ mark + KODA wordmark
- Center: eyebrow label ("Precision Training System") + Syne 44px headline ("Structure is the edge you need.") + body copy tagline
- Bottom-left: rotating motivational quote block (cycles every 8s with a fade transition)

**Right panel — form:**
- Background: `#0d1117`, `border-left: 1px solid rgba(124,58,237,0.15)`
- Padding: 48px 40px
- Eyebrow: "Welcome Back" · Title: "Sign in to Koda" · Subtitle: "Continue your structured training."
- Fields: Email, Password (with show/hide toggle)
- Primary button: "Sign In to Koda"
- Divider: "or continue with"
- SSO button: Google (with Google SVG icon)
- Footer link: "Don't have an account? Create one free →"

**Mobile layout:**
- Hero fills 100vh; grid texture + glow as desktop
- φ + KODA nav at top-left
- Syne headline centered-left, body copy below
- Frosted glass form card pinned to the bottom: `background: rgba(13,17,23,0.88)`, `backdrop-filter: blur(16px)`, `border: 1px solid rgba(124,58,237,0.3)`, `border-radius: 18px 18px 0 0`
- Scrolling down reveals full form with hero compressed into a thin brand bar at top (φ + KODA + gradient bg, ~80px)

### 4.2 Register (`/register`)
- Same two-column layout as login
- Right panel: Name, Email, Password fields + "Create Koda Account" primary button
- Hero left panel identical (same rotating quote, same atmosphere)

### 4.3 Dashboard — Generate & Preview (`/dashboard`, `/preview`)

**Navbar** (shared, see §3)

**Hero greeting bar** (below navbar):
- `background: linear-gradient(135deg, #0e0b1f, #130d2a, #0a0d1a)`
- Grid texture + glow (right side)
- Left: eyebrow (day + date) + Syne 26px greeting ("Good morning, Daniel. / Build today's plan.")
- Right: three stat pills — Plans · Completion Rate · Programs (JetBrains Mono values)

**Main content — two-panel grid** (`340px | 1fr`):

*Left — Generator panel:*
- Section label "Goal" → 2×3 grid of goal cards (icon + name); selected state: violet border + bg tint
- Section label "Equipment" → Tom Select multi-select styled in Koda tokens (violet selected tags, dark dropdown)
- Section label "Duration" → JetBrains Mono 28px value display + custom-styled range slider (violet thumb + fill gradient) + min/max labels
- Primary "⚡ Generate Workout" button (full width)
- Below button: muscle map SVG with Koda-colored regions (primary = `#a78bfa`, secondary = `rgba(167,139,250,0.4)`) + legend

*Right — Workout preview panel:*
- "Workout Preview" section label
- Workout card with violet border glow:
  - Header: goal emoji + title + description · play button (green gradient, circular) · duration badge (JetBrains Mono, violet)
  - Stats row: 3-column grid — Exercises · Sets · Rep Range (JetBrains Mono values)
  - Exercise list: warm-up tag → circuit block (violet border, `rgba(124,58,237,0.1)` header) → exercise items (number circle, name, meta, video/delete icon buttons) → sortable via drag handle
- Below card: "Push to Garmin Connect ↑" button (green accent)

**Mobile:**
- Generator and Preview are separate scroll contexts stacked vertically (no routing change — same page)
- Hero greeting bar compressed to ~80px
- A sticky toggle row (two buttons: "Generate" / "Preview") scrolls with the page; tapping one smooth-scrolls to that section. This is a CSS scroll-snap + `scrollIntoView` pattern, not a router change.

### 4.4 My Plans (`/plans`)
- Page hero: eyebrow "Training Library" · title "My Plans" · right: plan count + "+ New Plan" button
- 3-column card grid (responsive → 2-col tablet → 1-col mobile)
- Each plan card: goal icon · title · subtitle (muscle groups) · badge row (goal, duration, status) · card footer (date + preview/delete icon buttons)
- Active/recently-uploaded cards get violet border glow
- Empty state: φ mark centered + Syne headline "Your training library is empty." + body copy + "Generate First Plan" primary button

### 4.5 My Programs (`/programs`)
- Page hero: eyebrow "Training Architecture" · title "My Programs"
- Same 3-column card grid as Plans
- Each card: goal icon · program name · badge row (duration weeks, status: Active/Completed/Paused, periodization type) · footer (date + view/delete)
- Empty state: same pattern with "No programs yet." message

### 4.6 Program Detail (`/programs/<id>`)
- Page hero: program name + status badge
- Sessions table: Week · Day · Focus · Scheduled date · Status badge
- Table rows: hover background `rgba(255,255,255,0.02)`, status badges (green/amber/slate)
- Back breadcrumb link at top (← Programs)

### 4.7 Progress (`/progress`)
- Page hero: eyebrow "Performance Tracking" · title "Your Progress" · right: rotating Koda quote in Syne italic
- Summary row: 4 stat cards — Total Sessions · Completed · Finish Rate · Total Minutes (JetBrains Mono values, violet)
- "Session History" section heading
- Data table: Workout · Date · Duration · Completion (inline progress bar + fraction) · Status badge
- Empty state: "No sessions recorded yet." + body copy

### 4.8 Profile (`/profile`)
- Page hero: eyebrow "Account" · title "[Name]'s Profile" · right: "Edit Profile" ghost button
- Two-column layout: left avatar card · right fitness info sections
- Avatar card: gradient circle with initials · name · email (JetBrains Mono) · member stats · divider · "Reconnect Garmin" primary button
- Fitness profile section: Info rows (Age, Fitness Level, Weekly Days) + tag badge rows (Goals, Equipment, Diet, Health conditions)
- Empty state (no questionnaire): card with φ mark + "Complete your fitness profile" CTA

### 4.9 Questionnaire Wizard (`/questionnaire`)
- Full-screen dark canvas (`#090b14`)
- Narrow centered card (max-width: 440px) with Koda card styling
- Progress bar at top: 4px, violet fill, `transition: width 0.4s ease`
- Step cards: absolute-positioned, animated in/out (`opacity` + `transform: scale + translateY`, 0.3s ease)
- Option cards (`.wopt`): dark bg, violet border when selected, tinted bg when selected
- Tag cloud (`.wtag`): pill-shaped, same selected states
- Slider display: JetBrains Mono 42px value, `color: #a78bfa`
- Navigation dots: 7px circles, `#a78bfa` when active with scale 1.3
- Buttons: Back (ghost) · Next (violet primary) · Save (green primary)

### 4.10 MFA (`/mfa`)
- Centered card on dark canvas
- φ mark at top (large, 48px)
- Syne headline "Two-Factor Authentication"
- 6-digit code input: JetBrains Mono, large, centered, violet focus ring
- Auto-submit on 6 digits

### 4.11 SSO / Auth Waiting (`/sso`, `/waiting`)
- Centered card, φ mark + animated violet spinner
- Status messages in Koda voice: "Connecting to Garmin Connect…"
- SSO: iframe card with Koda card styling

---

## 5. Animations & Micro-interactions

| Element | Animation |
|---|---|
| Page load | `fadeIn` 0.3s ease on `<main>` |
| Hero glow | Subtle `pulse` (scale 1.0 → 1.05 → 1.0, 4s infinite) on radial glow elements |
| Motivational quote rotation | `opacity` fade 0.4s ease, every 8 seconds |
| Questionnaire step transition | `opacity` + `scale(0.94) translateY(±12px)`, 0.3s ease |
| Play button rings | `play-ring-pulse` keyframe, 2.4s ease-out infinite (existing — keep) |
| Card hover | `border-color` transition 0.15s to violet |
| Button hover | Gradient brightens via `filter: brightness(1.08)`, 0.15s |
| Active button | `transform: scale(0.98)`, 70ms |
| Progress bar fill | `width` transition 0.4s ease |
| Exercise removal | `opacity 0 + translateX(20px)`, 0.2s ease |
| Input focus | `box-shadow` focus ring, 0.15s |
| Navbar | `backdrop-filter` already set; on scroll past hero, add `box-shadow: 0 1px 0 rgba(124,58,237,0.2)` |
| Goal card select | Border color + background tint, 0.15s |

---

## 6. Responsive Breakpoints

| Breakpoint | Layout changes |
|---|---|
| < 768px (mobile) | Single column everywhere; dashboard generator + preview stacked; hero compressed to ~80px bar on inner pages; login = full-screen hero with float card; navbar collapses to hamburger |
| 768–1024px (tablet) | Plan/program grid → 2 columns; dashboard still 2-panel but generator narrower |
| ≥ 1024px (desktop) | Full layouts as specified above |

---

## 7. Implementation Notes

### Files to change
- **`web/static/css/`** — Replace current CSS with new Koda stylesheet. Use CSS custom properties for all tokens.
- **`web/templates/base.html`** — New navbar, Google Fonts `<link>`, updated brand name, φ logo mark.
- **`web/templates/login_forge.html`** — Full cinematic hero rebuild.
- **`web/templates/register.html`** — Same two-column layout as login.
- **`web/templates/dashboard.html`** — Hero greeting bar + two-panel generator/preview.
- **`web/templates/workout_preview.html`** — Inline with dashboard preview panel styles.
- **`web/templates/my_plans.html`** — Page hero + card grid.
- **`web/templates/my_programs.html`** — Page hero + card grid.
- **`web/templates/my_program_detail.html`** — Page hero + sessions table.
- **`web/templates/my_progress.html`** — Page hero + summary stats + data table.
- **`web/templates/my_profile.html`** — Page hero + split profile layout.
- **`web/templates/questionnaire.html`** — Koda-styled wizard (existing JS logic preserved).
- **`web/templates/mfa.html`** — Centered card with φ mark.
- **`web/templates/sso.html`** — Centered card + iframe.
- **`web/templates/waiting.html`** — Centered card + violet spinner.
- **`web/app.py` / routes** — No logic changes; only template string updates for brand name where hardcoded.

### Key constraints
- Bootstrap 5 stays as the grid foundation (`container-xl`, responsive grid classes). Override all Bootstrap color variables with Koda tokens.
- Existing JS (SortableJS drag-and-drop, Tom Select, play button logic, questionnaire transitions) must remain functional — only CSS class names and structure change where necessary, keeping JS hooks intact.
- `data-bs-theme="dark"` stays on `<html>`.
- RTL Hebrew support (`lang="he"`, `dir="rtl"`) must continue working — avoid directional CSS values where RTL-safe alternatives exist.
- No new Python dependencies. All font loading via Google Fonts CDN `<link>` in `<head>`.

### Tom Select restyling
Override Tom Select CSS variables to match Koda tokens: dark background, violet selected item tags, violet hover states, card-level dropdown background.

### Garmin Connected badge
Preserved in navbar right slot. Green variant (`#4ade80`) for connected, amber (`#fbbf24`) for disconnected — matches semantic color tokens.

---

## 8. Out of Scope

- No changes to Python logic, API calls, auth flow, or workout generation
- No new pages or features
- No changes to the muscle map SVG paths (only CSS fill colors updated)
- No changes to `garminforge/` library code
