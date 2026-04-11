# Koda UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild every web template and the CSS from scratch in Koda's visual language, rebranding from GarminForge to Koda across the entire UI.

**Architecture:** Replace `web/static/css/style.css` with a complete Koda stylesheet using CSS custom properties, then rebuild each template one by one. Login/register are standalone (no `extends base.html`) to allow full-width cinematic hero. All existing Python logic, JS hooks (class names), and Bootstrap grid are preserved untouched.

**Tech Stack:** Bootstrap 5 (grid only), CSS custom properties, Syne + Inter + JetBrains Mono (Google Fonts), SortableJS (existing), Tom Select (existing), Jinja2 templates, FastAPI

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `web/static/css/style.css` | Replace entirely | All Koda design tokens, component styles, animations |
| `web/templates/base.html` | Modify | Google Fonts link, φ mark navbar, `{% block main_class %}` |
| `web/templates/login_forge.html` | Replace entirely | Standalone cinematic hero + login form |
| `web/templates/index.html` | Replace entirely | Standalone — same layout as login_forge |
| `web/templates/register.html` | Replace entirely | Standalone — same hero + registration form |
| `web/templates/dashboard.html` | Replace entirely | Hero greeting bar + 2-panel generator/preview |
| `web/templates/workout_preview.html` | Replace entirely | Workout card with sortable exercise list |
| `web/templates/my_plans.html` | Replace entirely | Page hero + plan card grid |
| `web/templates/my_programs.html` | Replace entirely | Page hero + program card grid |
| `web/templates/my_program_detail.html` | Replace entirely | Page hero + sessions table |
| `web/templates/my_progress.html` | Replace entirely | Page hero + 4 stat cards + session table |
| `web/templates/my_profile.html` | Replace entirely | Page hero + avatar card + fitness info |
| `web/templates/questionnaire.html` | Modify in place | Update CSS tokens only, preserve all JS logic |
| `web/templates/mfa.html` | Replace entirely | Centered card with φ mark + code input |
| `web/templates/sso.html` | Replace entirely | Centered card + iframe |
| `web/templates/waiting.html` | Replace entirely | Centered card + violet spinner |
| `web/translations.py` | Modify | Add new keys, update "GarminForge" → "Koda" in values |

---

## Task 1: Koda CSS — Design Tokens and Core Components

**Files:**
- Replace: `web/static/css/style.css`

- [ ] **Step 1: Write the complete Koda stylesheet**

Replace the entire file with:

```css
/* =========================================================
   Koda — design system stylesheet
   Bootstrap 5 grid is kept. All Bootstrap color vars are
   overridden via :root custom properties below.
   ========================================================= */

/* ---------- Design Tokens ---------- */
:root {
  /* Backgrounds */
  --color-canvas:      #090b14;
  --color-surface:     #0d1117;
  --color-card:        #111827;
  --color-card-raised: #1a2035;
  --color-hero-bg:     #0e0b1f;

  /* Brand (Violet/Indigo) */
  --color-brand-deep:  #4c1d95;
  --color-brand-dark:  #6d28d9;
  --color-brand:       #7c3aed;
  --color-brand-mid:   #8b5cf6;
  --color-brand-light: #a78bfa;
  --color-brand-pale:  #ddd6fe;

  /* Semantic */
  --color-success:     #16a34a;
  --color-success-lt:  #4ade80;
  --color-warning:     #d97706;
  --color-warning-lt:  #fbbf24;
  --color-danger:      #dc2626;
  --color-danger-lt:   #f87171;

  /* Text */
  --text-primary:      #ffffff;
  --text-body:         rgba(255,255,255,0.75);
  --text-secondary:    rgba(255,255,255,0.45);
  --text-muted:        rgba(255,255,255,0.25);
  --text-accent:       #a78bfa;

  /* Borders */
  --border-default:    rgba(255,255,255,0.07);
  --border-brand:      rgba(124,58,237,0.4);
  --border-brand-faint: rgba(124,58,237,0.15);

  /* Shadows / glows */
  --glow-brand:        0 0 40px rgba(124,58,237,0.08);
  --focus-ring:        0 0 0 3px rgba(124,58,237,0.15);

  /* Radius */
  --radius-card:   14px;
  --radius-inner:  10px;
  --radius-input:   8px;
  --radius-badge:  20px;

  /* Legacy aliases (keep JS/templates that reference these working) */
  --garmin-blue:   #7c3aed;
  --card-bg:       #111827;
  --card-border:   rgba(255,255,255,0.07);
}

/* Bootstrap dark theme override */
[data-bs-theme="dark"] {
  --bs-body-bg:         var(--color-canvas);
  --bs-body-color:      var(--text-body);
  --bs-border-color:    var(--border-default);
  --bs-card-bg:         var(--color-card);
  --bs-link-color:      var(--color-brand-light);
  --bs-link-hover-color: var(--color-brand-pale);
}

/* ---------- Base ---------- */
*,
*::before,
*::after { box-sizing: border-box; }

body {
  background-color: var(--color-canvas);
  color: var(--text-body);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 14px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

main { flex: 1; }

h1, h2, h3, h4, h5, h6 { color: var(--text-primary); }

a { color: var(--color-brand-light); text-decoration: none; }
a:hover { color: var(--color-brand-pale); }

/* ---------- Page fade-in ---------- */
@keyframes koda-fade-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

main { animation: koda-fade-in 0.3s ease; }

/* ---------- Koda φ mark ---------- */
.koda-phi {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 2px solid var(--color-brand);
  flex-shrink: 0;
}

.koda-phi::before {
  content: '';
  position: absolute;
  left: -1px;
  right: -1px;
  top: 50%;
  height: 2px;
  background: var(--color-brand);
  transform: translateY(-50%);
}

.koda-phi::after {
  content: '';
  position: absolute;
  top: -1px;
  bottom: -1px;
  left: 50%;
  width: 2px;
  background: var(--color-brand);
  transform: translateX(-50%);
}

.koda-phi--lg {
  width: 56px;
  height: 56px;
}

.koda-phi--sm {
  width: 24px;
  height: 24px;
}

/* ---------- Wordmark ---------- */
.koda-wordmark {
  font-family: 'Inter', sans-serif;
  font-weight: 800;
  font-size: 15px;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  color: var(--text-primary);
  line-height: 1;
}

/* ---------- Navbar ---------- */
.koda-navbar {
  height: 54px;
  background: rgba(13,17,23,0.97);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-brand-faint);
  position: sticky;
  top: 0;
  z-index: 1030;
  display: flex;
  align-items: center;
}

.koda-navbar .container-fluid {
  display: flex;
  align-items: center;
  gap: 8px;
}

.koda-nav-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
}

.koda-nav-links {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-inline-start: 24px;
}

.koda-nav-link {
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  padding: 5px 10px;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
  text-decoration: none;
}

.koda-nav-link:hover {
  color: var(--text-primary);
  background: rgba(124,58,237,0.08);
}

.koda-nav-link.active {
  color: var(--color-brand-light);
  background: rgba(124,58,237,0.12);
}

.koda-nav-right {
  margin-inline-start: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Garmin connected badge */
.koda-badge-connected,
.koda-badge-disconnected {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 20px;
  letter-spacing: 0.3px;
}

.koda-badge-connected {
  background: rgba(74,222,128,0.1);
  border: 1px solid rgba(74,222,128,0.25);
  color: var(--color-success-lt);
}

.koda-badge-disconnected {
  background: rgba(251,191,36,0.1);
  border: 1px solid rgba(251,191,36,0.25);
  color: var(--color-warning-lt);
}

.koda-badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

/* Avatar circle */
.koda-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-brand-dark), var(--color-brand-mid));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}

/* Mobile hamburger */
.koda-hamburger {
  display: none;
  background: none;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  border-radius: 6px;
  padding: 5px 8px;
  cursor: pointer;
  margin-inline-start: auto;
}

/* Mobile nav drawer */
.koda-nav-drawer {
  display: none;
  background: var(--color-surface);
  border-bottom: 1px solid var(--border-brand-faint);
  padding: 12px 16px;
}

.koda-nav-drawer.open { display: block; }

/* Navbar scroll shadow */
.koda-navbar.scrolled {
  box-shadow: 0 1px 0 rgba(124,58,237,0.2);
}

/* ---------- Hero texture helpers ---------- */
.koda-hero-texture {
  position: absolute;
  inset: 0;
  background-image:
    repeating-linear-gradient(0deg,   rgba(124,58,237,0.04) 0, rgba(124,58,237,0.04) 1px, transparent 1px, transparent 56px),
    repeating-linear-gradient(90deg,  rgba(124,58,237,0.04) 0, rgba(124,58,237,0.04) 1px, transparent 1px, transparent 56px);
  pointer-events: none;
}

@keyframes koda-glow-pulse {
  0%, 100% { transform: scale(1);   opacity: 0.7; }
  50%       { transform: scale(1.05); opacity: 1; }
}

.koda-hero-glow {
  position: absolute;
  width: 480px;
  height: 480px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(124,58,237,0.15) 0%, transparent 70%);
  pointer-events: none;
  animation: koda-glow-pulse 4s ease-in-out infinite;
}

.koda-hero-glow--br { bottom: -120px; right: -120px; }
.koda-hero-glow--tl { top: -120px;    left: -120px; }

/* ---------- Page hero (inner pages) ---------- */
.koda-page-hero {
  background: linear-gradient(135deg, #0e0b1f, #130d2a, #0a0d1a);
  border-bottom: 1px solid var(--border-brand-faint);
  padding: 32px 0;
  position: relative;
  overflow: hidden;
}

.koda-page-hero .koda-eyebrow {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 3px;
  color: var(--color-brand-light);
  margin-bottom: 6px;
}

.koda-page-hero .koda-page-title {
  font-family: 'Syne', sans-serif;
  font-weight: 800;
  font-size: 30px;
  color: var(--text-primary);
  margin: 0;
}

/* ---------- Cards ---------- */
.koda-card {
  background: var(--color-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-card);
  padding: 20px;
  transition: border-color 0.15s;
}

.koda-card:hover { border-color: rgba(124,58,237,0.25); }

.koda-card--active {
  border-color: var(--border-brand);
  box-shadow: var(--glow-brand);
}

/* ---------- Stat cards ---------- */
.koda-stat-card {
  background: rgba(124,58,237,0.08);
  border: 1px solid rgba(124,58,237,0.18);
  border-radius: 12px;
  padding: 14px 18px;
  text-align: center;
}

.koda-stat-value {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  font-size: 24px;
  color: var(--color-brand-light);
  line-height: 1.1;
}

.koda-stat-label {
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--text-muted);
  margin-top: 4px;
}

/* ---------- Buttons ---------- */
.btn-koda-primary {
  background: linear-gradient(135deg, #7c3aed, #a78bfa);
  color: #fff;
  border: none;
  border-radius: var(--radius-input);
  padding: 11px 20px;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  transition: filter 0.15s, transform 0.07s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-koda-primary:hover  { filter: brightness(1.08); }
.btn-koda-primary:active { transform: scale(0.98); }
.btn-koda-primary:disabled { opacity: 0.55; cursor: not-allowed; }

.btn-koda-secondary {
  background: rgba(124,58,237,0.12);
  border: 1px solid rgba(124,58,237,0.35);
  color: var(--color-brand-light);
  border-radius: var(--radius-input);
  padding: 10px 18px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-koda-secondary:hover { background: rgba(124,58,237,0.2); }

.btn-koda-ghost {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  border-radius: var(--radius-input);
  padding: 10px 18px;
  font-weight: 500;
  font-size: 14px;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-koda-ghost:hover { border-color: rgba(255,255,255,0.25); color: var(--text-body); }

.btn-koda-success {
  background: linear-gradient(135deg, #22c55e, #16a34a);
  color: #fff;
  border: none;
  border-radius: var(--radius-input);
  padding: 11px 20px;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  transition: filter 0.15s, transform 0.07s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-koda-success:hover  { filter: brightness(1.08); }
.btn-koda-success:active { transform: scale(0.98); }
.btn-koda-success:disabled { opacity: 0.55; cursor: not-allowed; }

/* Loading spinner (toggled via JS class — never set innerHTML) */
.koda-spinner {
  display: none;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: koda-spin 0.6s linear infinite;
  flex-shrink: 0;
}

.is-loading .koda-spinner { display: inline-block; }

@keyframes koda-spin {
  to { transform: rotate(360deg); }
}

/* Keep existing .btn-garmin working (legacy alias) */
.btn-garmin {
  background: linear-gradient(135deg, #22c55e, #16a34a);
  border-color: transparent;
  color: #fff;
  font-weight: 700;
  transition: filter 0.15s, transform 0.07s;
}
.btn-garmin:hover  { filter: brightness(1.08); color: #fff; }
.btn-garmin:active { transform: scale(0.98); }

/* ---------- Inputs ---------- */
.koda-input {
  width: 100%;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: var(--radius-input);
  padding: 11px 14px;
  color: var(--text-primary);
  font-size: 14px;
  font-family: 'Inter', sans-serif;
  transition: background 0.15s, border-color 0.15s, box-shadow 0.15s;
  outline: none;
}

.koda-input:focus {
  background: rgba(124,58,237,0.07);
  border-color: rgba(124,58,237,0.6);
  box-shadow: var(--focus-ring);
}

.koda-input::placeholder { color: var(--text-muted); }

/* Password visibility toggle */
.koda-input-group {
  position: relative;
}

.koda-input-group .koda-input { padding-inline-end: 44px; }

.koda-input-toggle {
  position: absolute;
  inset-block-start: 50%;
  inset-inline-end: 14px;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0;
  font-size: 15px;
  line-height: 1;
}

/* ---------- Section label ---------- */
.koda-section-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 3px;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

/* ---------- Badges ---------- */
.koda-badge {
  display: inline-flex;
  align-items: center;
  border-radius: var(--radius-badge);
  padding: 3px 10px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.koda-badge--violet {
  background: rgba(124,58,237,0.15);
  color: var(--color-brand-light);
  border: 1px solid rgba(124,58,237,0.3);
}

.koda-badge--green {
  background: rgba(74,222,128,0.1);
  color: var(--color-success-lt);
  border: 1px solid rgba(74,222,128,0.2);
}

.koda-badge--amber {
  background: rgba(251,191,36,0.1);
  color: var(--color-warning-lt);
  border: 1px solid rgba(251,191,36,0.2);
}

.koda-badge--red {
  background: rgba(248,113,113,0.1);
  color: var(--color-danger-lt);
  border: 1px solid rgba(248,113,113,0.2);
}

.koda-badge--slate {
  background: rgba(255,255,255,0.06);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
}

/* ---------- Progress bar ---------- */
.koda-progress-track {
  height: 4px;
  background: rgba(255,255,255,0.07);
  border-radius: 3px;
  overflow: hidden;
}

.koda-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-brand), var(--color-brand-light));
  border-radius: 3px;
  transition: width 0.4s ease;
}

/* ---------- Motivational quote block ---------- */
.koda-quote {
  border-inline-start: 3px solid var(--color-brand);
  border-radius: 0 12px 12px 0;
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(124,58,237,0.1), rgba(167,139,250,0.05));
  transition: opacity 0.4s ease;
}

.koda-quote p {
  font-family: 'Syne', sans-serif;
  font-weight: 700;
  font-size: 15px;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.45;
}

.koda-quote.fade-out { opacity: 0; }

/* ---------- Divider with text ---------- */
.koda-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 500;
  margin: 20px 0;
}

.koda-divider::before,
.koda-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-default);
}

/* ---------- Play button (workout card) ---------- */
.play-btn-charged {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: none;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  flex-shrink: 0;
  font-size: 14px;
  transition: filter 0.15s;
}

.play-btn-charged:hover { filter: brightness(1.12); }

@keyframes play-ring-pulse {
  0%   { transform: scale(1);   opacity: 0.6; }
  70%  { transform: scale(1.45); opacity: 0; }
  100% { transform: scale(1.45); opacity: 0; }
}

.play-btn-charged::before {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 2px solid #22c55e;
  animation: play-ring-pulse 2.4s ease-out infinite;
}

/* ---------- Exercise list ---------- */
.exercise-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--color-card-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-inner);
  transition: border-color 0.15s, opacity 0.2s, transform 0.2s;
  cursor: default;
}

.exercise-item:hover { border-color: rgba(124,58,237,0.25); }

.exercise-item.removing {
  opacity: 0;
  transform: translateX(20px);
}

.step-number {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(124,58,237,0.15);
  border: 1px solid rgba(124,58,237,0.3);
  color: var(--color-brand-light);
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.drag-handle {
  color: var(--text-muted);
  cursor: grab;
  font-size: 14px;
  flex-shrink: 0;
}

.drag-handle:active { cursor: grabbing; }

/* SortableJS ghost / chosen states (JS hooks — do not rename) */
.sortable-ghost {
  opacity: 0.35;
  background: rgba(124,58,237,0.08);
}

.sortable-chosen {
  border-color: var(--border-brand) !important;
  box-shadow: var(--glow-brand);
}

/* Circuit block */
.koda-circuit-block {
  border: 1px solid rgba(124,58,237,0.3);
  border-radius: var(--radius-inner);
  overflow: hidden;
  margin-bottom: 8px;
}

.koda-circuit-header {
  background: rgba(124,58,237,0.1);
  padding: 8px 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.koda-circuit-body {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* ---------- Goal cards (dashboard generator) ---------- */
.koda-goal-card {
  background: var(--color-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-inner);
  padding: 12px 10px;
  cursor: pointer;
  text-align: center;
  transition: border-color 0.15s, background 0.15s;
  position: relative;
}

.koda-goal-card:hover {
  border-color: rgba(124,58,237,0.35);
  background: rgba(124,58,237,0.05);
}

.koda-goal-card.selected {
  border-color: var(--color-brand);
  background: rgba(124,58,237,0.1);
}

.koda-goal-card input[type="radio"] {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.koda-goal-icon { font-size: 20px; margin-bottom: 4px; }

.koda-goal-name {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-primary);
}

/* ---------- Range slider ---------- */
.koda-range {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 4px;
  background: rgba(255,255,255,0.1);
  border-radius: 3px;
  outline: none;
  cursor: pointer;
}

.koda-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-brand), var(--color-brand-light));
  cursor: pointer;
  box-shadow: 0 0 8px rgba(124,58,237,0.4);
}

.koda-range::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-brand), var(--color-brand-light));
  cursor: pointer;
  border: none;
}

.koda-duration-value {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  font-size: 28px;
  color: var(--color-brand-light);
  line-height: 1;
}

/* ---------- Dashboard greeting bar ---------- */
.koda-greeting-bar {
  background: linear-gradient(135deg, #0e0b1f, #130d2a, #0a0d1a);
  border-bottom: 1px solid var(--border-brand-faint);
  padding: 24px 0;
  position: relative;
  overflow: hidden;
}

.koda-greeting {
  font-family: 'Syne', sans-serif;
  font-weight: 800;
  font-size: 26px;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.2;
}

.koda-greeting-day {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 3px;
  color: var(--color-brand-light);
  margin-bottom: 4px;
}

.koda-stat-pill {
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  padding: 10px 16px;
  text-align: center;
  min-width: 80px;
}

.koda-stat-pill-value {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  font-size: 20px;
  color: var(--color-brand-light);
}

.koda-stat-pill-label {
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: var(--text-muted);
}

/* ---------- Tom Select overrides ---------- */
.ts-wrapper .ts-control {
  background: rgba(255,255,255,0.05) !important;
  border: 1px solid rgba(255,255,255,0.1) !important;
  border-radius: var(--radius-input) !important;
  color: var(--text-primary) !important;
  padding: 8px 12px !important;
  min-height: 42px;
}

.ts-wrapper.focus .ts-control {
  border-color: rgba(124,58,237,0.6) !important;
  box-shadow: var(--focus-ring) !important;
  background: rgba(124,58,237,0.07) !important;
}

.ts-wrapper .ts-dropdown {
  background: var(--color-card-raised) !important;
  border: 1px solid var(--border-brand-faint) !important;
  border-radius: var(--radius-input) !important;
}

.ts-wrapper .ts-dropdown .option:hover,
.ts-wrapper .ts-dropdown .option.active {
  background: rgba(124,58,237,0.12) !important;
  color: var(--text-primary) !important;
}

.ts-wrapper .ts-dropdown .option.selected {
  background: rgba(124,58,237,0.2) !important;
}

.ts-wrapper .item {
  background: rgba(124,58,237,0.15) !important;
  border: 1px solid rgba(124,58,237,0.35) !important;
  color: var(--color-brand-light) !important;
  border-radius: 6px !important;
  font-size: 12px !important;
  font-weight: 600 !important;
}

/* ---------- Muscle map SVG ---------- */
.muscle-primary   { fill: #a78bfa; }
.muscle-secondary { fill: rgba(167,139,250,0.4); }
.muscle-neutral   { fill: rgba(255,255,255,0.07); }

/* ---------- Tables ---------- */
.koda-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.koda-table th {
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--text-muted);
  padding: 10px 14px;
  text-align: start;
  border-bottom: 1px solid var(--border-default);
}

.koda-table td {
  padding: 12px 14px;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  color: var(--text-body);
}

.koda-table tr:hover td { background: rgba(255,255,255,0.02); }

/* ---------- Auth centered card layout ---------- */
.koda-auth-centered {
  min-height: 100vh;
  background: var(--color-canvas);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.koda-auth-card {
  width: 100%;
  max-width: 420px;
  background: var(--color-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-card);
  padding: 36px 32px;
  text-align: center;
}

/* ---------- Profile avatar card ---------- */
.koda-avatar-card {
  background: var(--color-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-card);
  padding: 28px 20px;
  text-align: center;
}

.koda-avatar-lg {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-brand-dark), var(--color-brand-mid));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  margin: 0 auto 14px;
}

/* ---------- Info row ---------- */
.koda-info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-default);
  font-size: 13px;
}

.koda-info-row:last-child { border-bottom: none; }

.koda-info-label { color: var(--text-secondary); }
.koda-info-value { color: var(--text-primary); font-weight: 500; }

/* ---------- Plan / program cards ---------- */
.koda-plan-card {
  background: var(--color-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-card);
  overflow: hidden;
  transition: border-color 0.15s, box-shadow 0.15s;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.koda-plan-card:hover {
  border-color: rgba(124,58,237,0.3);
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}

.koda-plan-card--active {
  border-color: var(--border-brand);
  box-shadow: var(--glow-brand);
}

.koda-plan-card-body { padding: 18px; flex: 1; }
.koda-plan-card-footer {
  padding: 12px 18px;
  border-top: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* ---------- Empty states ---------- */
.koda-empty {
  padding: 60px 20px;
  text-align: center;
}

.koda-empty .koda-phi {
  margin: 0 auto 16px;
  opacity: 0.35;
}

.koda-empty-title {
  font-family: 'Syne', sans-serif;
  font-weight: 800;
  font-size: 20px;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.koda-empty-body { color: var(--text-secondary); font-size: 13px; }

/* ---------- Mobile toggle (dashboard sections) ---------- */
.koda-section-toggle {
  display: none;
  position: sticky;
  top: 54px;
  z-index: 100;
  background: var(--color-surface);
  border-bottom: 1px solid var(--border-default);
  padding: 8px 16px;
  gap: 8px;
}

.koda-section-toggle button {
  flex: 1;
  padding: 8px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  border: 1px solid var(--border-default);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.koda-section-toggle button.active {
  background: rgba(124,58,237,0.12);
  border-color: rgba(124,58,237,0.4);
  color: var(--color-brand-light);
}

/* ---------- Questionnaire wizard ---------- */
.wopt {
  background: var(--color-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-inner);
  padding: 12px 16px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.wopt.selected,
.wopt:has(input:checked) {
  border-color: var(--color-brand);
  background: rgba(124,58,237,0.1);
}

.wtag {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  border-radius: var(--radius-badge);
  border: 1px solid var(--border-default);
  background: var(--color-card);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.wtag.selected,
.wtag:has(input:checked) {
  border-color: var(--color-brand);
  background: rgba(124,58,237,0.1);
  color: var(--color-brand-light);
}

/* ---------- Responsive ---------- */
@media (max-width: 767px) {
  .koda-nav-links { display: none; }
  .koda-badge-connected,
  .koda-badge-disconnected { display: none; }
  .koda-hamburger { display: flex; }

  .koda-page-hero { padding: 18px 0; }
  .koda-page-hero .koda-page-title { font-size: 22px; }

  .koda-greeting { font-size: 20px; }
  .koda-greeting-bar { padding: 16px 0; }

  .koda-section-toggle { display: flex; }

  .koda-auth-card { padding: 28px 20px; }
}

@media (min-width: 768px) and (max-width: 1023px) {
  .koda-page-hero .koda-page-title { font-size: 26px; }
}
```

- [ ] **Step 2: Verify the file saved correctly**

Run: `wc -l web/static/css/style.css`
Expected: 550+ lines

- [ ] **Step 3: Commit**

```bash
git add web/static/css/style.css
git commit -m "feat(koda): replace stylesheet with Koda design system tokens and components"
```

---

## Task 2: Update base.html

**Files:**
- Modify: `web/templates/base.html`

- [ ] **Step 1: Read the current file**

Run: `cat -n web/templates/base.html`
Expected: ~80 lines, Bootstrap navbar, emoji brand mark, `<main class="container-xl py-4">`

- [ ] **Step 2: Replace base.html with the Koda version**

Write the complete new file:

```html
<!doctype html>
<html lang="{{ lang }}" dir="{{ 'rtl' if lang == 'he' else 'ltr' }}" data-bs-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Koda{% endblock %}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
  <link rel="stylesheet" href="{{ url_for('static', path='/css/style.css') }}?v=2">
  {% block extra_head %}{% endblock %}
</head>
<body>

<nav class="koda-navbar">
  <div class="container-fluid px-3 px-lg-4">
    <a href="{{ url_for('dashboard') }}" class="koda-nav-brand">
      <span class="koda-phi" aria-hidden="true"></span>
      <span class="koda-wordmark">Koda</span>
    </a>

    {% if current_user %}
    <div class="koda-nav-links">
      <a href="{{ url_for('dashboard') }}"
         class="koda-nav-link{% if active_page == 'generate' %} active{% endif %}">
        {{ t('nav_generate') }}
      </a>
      <a href="{{ url_for('my_plans') }}"
         class="koda-nav-link{% if active_page == 'plans' %} active{% endif %}">
        {{ t('nav_my_plans') }}
      </a>
      <a href="{{ url_for('my_programs') }}"
         class="koda-nav-link{% if active_page == 'programs' %} active{% endif %}">
        {{ t('nav_programs') }}
      </a>
      <a href="{{ url_for('progress') }}"
         class="koda-nav-link{% if active_page == 'progress' %} active{% endif %}">
        {{ t('nav_progress') }}
      </a>
    </div>
    {% endif %}

    <div class="koda-nav-right">
      {% if current_user %}
        {% if garmin_connected %}
          <span class="koda-badge-connected">
            <span class="koda-badge-dot"></span>
            {{ t('nav_garmin_connected') }}
          </span>
        {% else %}
          <span class="koda-badge-disconnected">
            <span class="koda-badge-dot"></span>
            {{ t('nav_garmin_not_connected') }}
          </span>
        {% endif %}
        <div class="koda-avatar">
          {{ (current_user.name or current_user.email or 'K')[0]|upper }}
        </div>
        <a href="{{ url_for('logout') }}" class="koda-nav-link d-none d-lg-inline-flex">
          {{ t('nav_logout') }}
        </a>
      {% else %}
        <a href="{{ url_for('login_page') }}" class="koda-nav-link">{{ t('nav_sign_in') }}</a>
        <a href="{{ url_for('register_page') }}" class="btn-koda-primary" style="padding:7px 14px;font-size:13px;">
          {{ t('nav_register') }}
        </a>
      {% endif %}

      <button class="koda-hamburger" id="kodaHamburger" aria-label="Menu">&#9776;</button>
    </div>
  </div>
</nav>

{% if current_user %}
<div class="koda-nav-drawer" id="kodaDrawer">
  <a href="{{ url_for('dashboard') }}" class="koda-nav-link d-block mb-1">{{ t('nav_generate') }}</a>
  <a href="{{ url_for('my_plans') }}" class="koda-nav-link d-block mb-1">{{ t('nav_my_plans') }}</a>
  <a href="{{ url_for('my_programs') }}" class="koda-nav-link d-block mb-1">{{ t('nav_programs') }}</a>
  <a href="{{ url_for('progress') }}" class="koda-nav-link d-block mb-1">{{ t('nav_progress') }}</a>
  <a href="{{ url_for('logout') }}" class="koda-nav-link d-block mt-2" style="color:var(--text-muted)">{{ t('nav_logout') }}</a>
</div>
{% endif %}

<main class="{% block main_class %}container-xl py-4{% endblock %}">
  {% block content %}{% endblock %}
</main>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
{% block scripts %}{% endblock %}

<script>
  // Navbar scroll shadow
  window.addEventListener('scroll', function() {
    document.querySelector('.koda-navbar').classList.toggle('scrolled', window.scrollY > 10);
  }, { passive: true });

  // Mobile hamburger
  var btn = document.getElementById('kodaHamburger');
  var drawer = document.getElementById('kodaDrawer');
  if (btn && drawer) {
    btn.addEventListener('click', function() {
      drawer.classList.toggle('open');
    });
  }
</script>
</body>
</html>
```

- [ ] **Step 3: Add the missing `nav_generate` translation key**

In `web/translations.py`, find the `# --- Navbar ---` section and add `"nav_generate"` after `"nav_my_plans"`:

```python
        "nav_generate":            "Generate",
```

Do the same in the `"he"` dict (Task 13 will handle Hebrew strings — for now just add the key with an English fallback by adding only to `"en"`).

- [ ] **Step 4: Verify no NameError from missing translation key**

Run the server briefly: `python run.py &` then `curl -s http://127.0.0.1:8000/ | head -5 && kill %1`
Expected: HTML response without Python traceback

- [ ] **Step 5: Commit**

```bash
git add web/templates/base.html web/translations.py
git commit -m "feat(koda): rebuild navbar with phi mark, Koda wordmark, and mobile drawer"
```

---

## Task 3: Login and Index Pages (Cinematic Hero)

**Files:**
- Replace: `web/templates/login_forge.html`
- Replace: `web/templates/index.html`

Both are standalone templates (no `{% extends %}`).

- [ ] **Step 1: Replace login_forge.html**

```html
<!doctype html>
<html lang="{{ lang }}" dir="{{ 'rtl' if lang == 'he' else 'ltr' }}" data-bs-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sign In — Koda</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
  <link rel="stylesheet" href="{{ url_for('static', path='/css/style.css') }}?v=2">
  <style>
    body { overflow-x: hidden; }

    /* ---- Desktop: two-column split ---- */
    .koda-login-wrap {
      display: grid;
      grid-template-columns: 1fr 420px;
      min-height: 100vh;
    }

    /* ---- Hero panel ---- */
    .koda-login-hero {
      background: linear-gradient(160deg, #0e0b1f, #130d2a, #0a0f1e);
      position: relative;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      padding: 32px 48px;
    }

    .koda-login-hero .koda-hero-brand {
      display: flex;
      align-items: center;
      gap: 10px;
      z-index: 1;
    }

    .koda-login-hero .hero-body {
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: center;
      z-index: 1;
      max-width: 560px;
    }

    .koda-login-eyebrow {
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 3px;
      color: var(--color-brand-light);
      margin-bottom: 14px;
    }

    .koda-login-headline {
      font-family: 'Syne', sans-serif;
      font-weight: 800;
      font-size: 44px;
      color: var(--text-primary);
      line-height: 1.1;
      margin-bottom: 18px;
    }

    .koda-login-tagline {
      font-size: 15px;
      color: var(--text-secondary);
      line-height: 1.6;
      max-width: 420px;
      margin-bottom: 40px;
    }

    .koda-login-hero .koda-quote-wrap {
      z-index: 1;
    }

    /* ---- Form panel ---- */
    .koda-login-form-panel {
      background: var(--color-surface);
      border-inline-start: 1px solid var(--border-brand-faint);
      display: flex;
      flex-direction: column;
      justify-content: center;
      padding: 48px 40px;
    }

    .koda-form-eyebrow {
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 3px;
      color: var(--color-brand-light);
      margin-bottom: 4px;
    }

    .koda-form-title {
      font-family: 'Syne', sans-serif;
      font-weight: 800;
      font-size: 26px;
      color: var(--text-primary);
      margin-bottom: 4px;
    }

    .koda-form-sub {
      font-size: 13px;
      color: var(--text-secondary);
      margin-bottom: 28px;
    }

    .koda-field { margin-bottom: 16px; }

    .koda-field label {
      display: block;
      font-size: 12px;
      font-weight: 600;
      color: var(--text-secondary);
      margin-bottom: 6px;
    }

    .koda-sso-btn {
      width: 100%;
      background: rgba(255,255,255,0.05);
      border: 1px solid var(--border-default);
      border-radius: var(--radius-input);
      padding: 11px 18px;
      color: var(--text-body);
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      transition: background 0.15s, border-color 0.15s;
      text-decoration: none;
    }

    .koda-sso-btn:hover {
      background: rgba(255,255,255,0.08);
      border-color: rgba(255,255,255,0.18);
      color: var(--text-primary);
    }

    .koda-form-footer {
      margin-top: 20px;
      font-size: 13px;
      color: var(--text-secondary);
      text-align: center;
    }

    /* ---- Mobile ---- */
    @media (max-width: 767px) {
      .koda-login-wrap {
        display: block;
        position: relative;
        min-height: 100vh;
      }

      .koda-login-hero {
        position: fixed;
        inset: 0;
        padding: 24px 20px 40vh;
        z-index: 0;
      }

      .koda-login-headline { font-size: 26px; }
      .koda-login-tagline  { display: none; }

      .koda-login-form-panel {
        position: relative;
        z-index: 1;
        margin-top: 40vh;
        background: rgba(13,17,23,0.88);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(124,58,237,0.3);
        border-radius: 18px 18px 0 0;
        border-inline-start: none;
        border-bottom: none;
        min-height: 60vh;
        justify-content: flex-start;
        padding: 28px 20px;
      }
    }
  </style>
</head>
<body>
<div class="koda-login-wrap">

  <!-- Hero panel -->
  <div class="koda-login-hero">
    <div class="koda-hero-texture"></div>
    <div class="koda-hero-glow koda-hero-glow--br"></div>
    <div class="koda-hero-glow koda-hero-glow--tl" style="opacity:0.4;"></div>

    <div class="koda-hero-brand">
      <span class="koda-phi" aria-hidden="true"></span>
      <span class="koda-wordmark">Koda</span>
    </div>

    <div class="hero-body">
      <div class="koda-login-eyebrow">Precision Training System</div>
      <h1 class="koda-login-headline">Structure is<br>the edge<br>you need.</h1>
      <p class="koda-login-tagline">
        Generate personalised strength workouts and push them directly to Garmin Connect.
      </p>

      <div class="koda-quote-wrap">
        <div class="koda-quote">
          <p id="heroQuote">The steady baseline compounds.</p>
        </div>
      </div>
    </div>
  </div>

  <!-- Form panel -->
  <div class="koda-login-form-panel">
    <div class="koda-form-eyebrow">Welcome Back</div>
    <h2 class="koda-form-title">Sign in to Koda</h2>
    <p class="koda-form-sub">Continue your structured training.</p>

    {% if error %}
    <div style="background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.3);border-radius:8px;padding:10px 14px;margin-bottom:16px;color:#f87171;font-size:13px;">
      {{ error }}
    </div>
    {% endif %}

    <form method="post" action="{{ url_for('login') }}" id="loginForm" novalidate>
      <div class="koda-field">
        <label for="email">{{ t('auth_email') }}</label>
        <input id="email" name="email" type="email" class="koda-input"
               placeholder="you@example.com" autocomplete="email" required>
      </div>

      <div class="koda-field">
        <label for="password">{{ t('auth_password') }}</label>
        <div class="koda-input-group">
          <input id="password" name="password" type="password" class="koda-input"
                 placeholder="••••••••" autocomplete="current-password" required>
          <button type="button" class="koda-input-toggle" id="pwToggle" aria-label="Show password">&#128065;</button>
        </div>
      </div>

      <button type="submit" class="btn-koda-primary w-100 justify-content-center mt-2" id="loginBtn">
        <span class="koda-spinner" aria-hidden="true"></span>
        <span class="koda-btn-label">{{ t('auth_sign_in_btn') }}</span>
      </button>
    </form>

    {% if sso_url %}
    <div class="koda-divider">{{ t('auth_or_email') }}</div>
    <a href="{{ sso_url }}" class="koda-sso-btn">
      <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
        <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"/>
        <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"/>
        <path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"/>
        <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58z"/>
      </svg>
      Continue with Google
    </a>
    {% endif %}

    <div class="koda-form-footer">
      {{ t('auth_new_here') }}
      <a href="{{ url_for('register_page') }}" style="color:var(--color-brand-light);font-weight:600;">
        {{ t('auth_create_free') }} →
      </a>
    </div>
  </div>
</div>

<script>
(function() {
  // Password visibility toggle
  var pwToggle = document.getElementById('pwToggle');
  var pwField  = document.getElementById('password');
  if (pwToggle && pwField) {
    pwToggle.addEventListener('click', function() {
      var isText = pwField.type === 'text';
      pwField.type = isText ? 'password' : 'text';
    });
  }

  // Login form — loading state (no innerHTML, spinner via CSS class)
  var form     = document.getElementById('loginForm');
  var loginBtn = document.getElementById('loginBtn');
  var MSG_SIGNING_IN = '{{ t("auth_signing_in") }}';
  if (form && loginBtn) {
    form.addEventListener('submit', function() {
      loginBtn.disabled = true;
      loginBtn.classList.add('is-loading');
      loginBtn.querySelector('.koda-btn-label').textContent = MSG_SIGNING_IN;
    });
  }

  // Rotating quotes
  var quotes = [
    'The steady baseline compounds.',
    'Structure is the edge you need.',
    'Turn intention into architecture.',
    'Consistency is the infrastructure.',
    'Precision over hype. Every session.'
  ];
  var el  = document.getElementById('heroQuote');
  var idx = 0;
  if (el) {
    setInterval(function() {
      var quoteBlock = el.closest('.koda-quote');
      if (quoteBlock) { quoteBlock.classList.add('fade-out'); }
      setTimeout(function() {
        idx = (idx + 1) % quotes.length;
        el.textContent = quotes[idx];
        if (quoteBlock) { quoteBlock.classList.remove('fade-out'); }
      }, 400);
    }, 8000);
  }
})();
</script>
</body>
</html>
```

- [ ] **Step 2: Replace index.html**

`index.html` is the direct Garmin Connect login page. Give it the same two-column cinematic layout but with Garmin-specific copy:

```html
<!doctype html>
<html lang="{{ lang }}" dir="{{ 'rtl' if lang == 'he' else 'ltr' }}" data-bs-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Connect Garmin — Koda</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
  <link rel="stylesheet" href="{{ url_for('static', path='/css/style.css') }}?v=2">
  <style>
    body { overflow-x: hidden; }
    .koda-login-wrap { display: grid; grid-template-columns: 1fr 420px; min-height: 100vh; }
    .koda-login-hero { background: linear-gradient(160deg, #0e0b1f, #130d2a, #0a0f1e); position: relative; overflow: hidden; display: flex; flex-direction: column; padding: 32px 48px; }
    .koda-login-hero .hero-body { flex: 1; display: flex; flex-direction: column; justify-content: center; z-index: 1; max-width: 560px; }
    .koda-login-eyebrow { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 3px; color: var(--color-brand-light); margin-bottom: 14px; }
    .koda-login-headline { font-family: 'Syne', sans-serif; font-weight: 800; font-size: 44px; color: var(--text-primary); line-height: 1.1; margin-bottom: 18px; }
    .koda-login-tagline { font-size: 15px; color: var(--text-secondary); line-height: 1.6; max-width: 420px; margin-bottom: 40px; }
    .koda-login-hero .koda-hero-brand { display: flex; align-items: center; gap: 10px; z-index: 1; }
    .koda-login-form-panel { background: var(--color-surface); border-inline-start: 1px solid var(--border-brand-faint); display: flex; flex-direction: column; justify-content: center; padding: 48px 40px; }
    .koda-form-eyebrow { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 3px; color: var(--color-brand-light); margin-bottom: 4px; }
    .koda-form-title { font-family: 'Syne', sans-serif; font-weight: 800; font-size: 26px; color: var(--text-primary); margin-bottom: 4px; }
    .koda-form-sub { font-size: 13px; color: var(--text-secondary); margin-bottom: 28px; }
    .koda-field { margin-bottom: 16px; }
    .koda-field label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; }
    .koda-form-footer { margin-top: 20px; font-size: 13px; color: var(--text-secondary); text-align: center; }
    @media (max-width: 767px) {
      .koda-login-wrap { display: block; position: relative; min-height: 100vh; }
      .koda-login-hero { position: fixed; inset: 0; padding: 24px 20px 40vh; z-index: 0; }
      .koda-login-headline { font-size: 26px; }
      .koda-login-tagline  { display: none; }
      .koda-login-form-panel { position: relative; z-index: 1; margin-top: 40vh; background: rgba(13,17,23,0.88); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(124,58,237,0.3); border-radius: 18px 18px 0 0; border-inline-start: none; border-bottom: none; min-height: 60vh; justify-content: flex-start; padding: 28px 20px; }
    }
  </style>
</head>
<body>
<div class="koda-login-wrap">
  <div class="koda-login-hero">
    <div class="koda-hero-texture"></div>
    <div class="koda-hero-glow koda-hero-glow--br"></div>
    <div class="koda-hero-brand">
      <span class="koda-phi" aria-hidden="true"></span>
      <span class="koda-wordmark">Koda</span>
    </div>
    <div class="hero-body">
      <div class="koda-login-eyebrow">Precision Training System</div>
      <h1 class="koda-login-headline">Connect your<br>Garmin.<br>Train with precision.</h1>
      <p class="koda-login-tagline">Link your Garmin Connect account to push workouts directly to your device.</p>
      <div class="koda-quote">
        <p id="heroQuote">Consistency is the infrastructure.</p>
      </div>
    </div>
  </div>

  <div class="koda-login-form-panel">
    <div class="koda-form-eyebrow">Garmin Account</div>
    <h2 class="koda-form-title">Sign in to Garmin</h2>
    <p class="koda-form-sub">Use your Garmin Connect credentials.</p>

    {% if error %}
    <div style="background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.3);border-radius:8px;padding:10px 14px;margin-bottom:16px;color:#f87171;font-size:13px;">
      {{ error }}
    </div>
    {% endif %}

    <form method="post" action="{{ url_for('garmin_login') }}" id="garminLoginForm" novalidate>
      <div class="koda-field">
        <label for="email">{{ t('auth_email') }}</label>
        <input id="email" name="email" type="email" class="koda-input"
               placeholder="you@garmin.com" autocomplete="email" required>
      </div>
      <div class="koda-field">
        <label for="password">{{ t('auth_password') }}</label>
        <div class="koda-input-group">
          <input id="password" name="password" type="password" class="koda-input"
                 placeholder="••••••••" autocomplete="current-password" required>
          <button type="button" class="koda-input-toggle" id="pwToggle" aria-label="Show password">&#128065;</button>
        </div>
      </div>
      <button type="submit" class="btn-koda-primary w-100 justify-content-center mt-2" id="garminLoginBtn">
        <span class="koda-spinner" aria-hidden="true"></span>
        <span class="koda-btn-label">{{ t('auth_signing_in_garmin', default='Connect Garmin Account') }}</span>
      </button>
    </form>

    <div class="koda-form-footer">
      <a href="{{ url_for('dashboard') }}" style="color:var(--text-secondary);">← Back to dashboard</a>
    </div>
  </div>
</div>
<script>
(function() {
  var pwToggle = document.getElementById('pwToggle');
  var pwField  = document.getElementById('password');
  if (pwToggle && pwField) {
    pwToggle.addEventListener('click', function() {
      pwField.type = pwField.type === 'text' ? 'password' : 'text';
    });
  }
  var form = document.getElementById('garminLoginForm');
  var btn  = document.getElementById('garminLoginBtn');
  if (form && btn) {
    form.addEventListener('submit', function() {
      btn.disabled = true;
      btn.classList.add('is-loading');
      btn.querySelector('.koda-btn-label').textContent = '{{ t("auth_signing_in") }}';
    });
  }
  var quotes = ['The steady baseline compounds.','Structure is the edge you need.','Turn intention into architecture.','Consistency is the infrastructure.','Precision over hype. Every session.'];
  var el = document.getElementById('heroQuote');
  var idx = 0;
  if (el) {
    setInterval(function() {
      var qb = el.closest('.koda-quote');
      if (qb) qb.classList.add('fade-out');
      setTimeout(function() {
        idx = (idx + 1) % quotes.length;
        el.textContent = quotes[idx];
        if (qb) qb.classList.remove('fade-out');
      }, 400);
    }, 8000);
  }
})();
</script>
</body>
</html>
```

- [ ] **Step 3: Check that the login page loads without errors**

Run: `python run.py &` then `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/login && kill %1`
Expected: `200`

- [ ] **Step 4: Commit**

```bash
git add web/templates/login_forge.html web/templates/index.html
git commit -m "feat(koda): rebuild login and Garmin connect pages with cinematic hero layout"
```

---

## Task 4: Register Page

**Files:**
- Replace: `web/templates/register.html`

- [ ] **Step 1: Replace register.html**

Same two-column layout as login. Only the form panel contents differ:

```html
<!doctype html>
<html lang="{{ lang }}" dir="{{ 'rtl' if lang == 'he' else 'ltr' }}" data-bs-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Create Account — Koda</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
  <link rel="stylesheet" href="{{ url_for('static', path='/css/style.css') }}?v=2">
  <style>
    body { overflow-x: hidden; }
    .koda-login-wrap { display: grid; grid-template-columns: 1fr 420px; min-height: 100vh; }
    .koda-login-hero { background: linear-gradient(160deg, #0e0b1f, #130d2a, #0a0f1e); position: relative; overflow: hidden; display: flex; flex-direction: column; padding: 32px 48px; }
    .koda-login-hero .hero-body { flex: 1; display: flex; flex-direction: column; justify-content: center; z-index: 1; max-width: 560px; }
    .koda-login-eyebrow { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 3px; color: var(--color-brand-light); margin-bottom: 14px; }
    .koda-login-headline { font-family: 'Syne', sans-serif; font-weight: 800; font-size: 44px; color: var(--text-primary); line-height: 1.1; margin-bottom: 18px; }
    .koda-login-tagline { font-size: 15px; color: var(--text-secondary); line-height: 1.6; max-width: 420px; margin-bottom: 40px; }
    .koda-login-hero .koda-hero-brand { display: flex; align-items: center; gap: 10px; z-index: 1; }
    .koda-login-form-panel { background: var(--color-surface); border-inline-start: 1px solid var(--border-brand-faint); display: flex; flex-direction: column; justify-content: center; padding: 48px 40px; }
    .koda-form-eyebrow { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 3px; color: var(--color-brand-light); margin-bottom: 4px; }
    .koda-form-title { font-family: 'Syne', sans-serif; font-weight: 800; font-size: 26px; color: var(--text-primary); margin-bottom: 4px; }
    .koda-form-sub { font-size: 13px; color: var(--text-secondary); margin-bottom: 28px; }
    .koda-field { margin-bottom: 16px; }
    .koda-field label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; }
    .koda-form-footer { margin-top: 20px; font-size: 13px; color: var(--text-secondary); text-align: center; }
    @media (max-width: 767px) {
      .koda-login-wrap { display: block; position: relative; min-height: 100vh; }
      .koda-login-hero { position: fixed; inset: 0; padding: 24px 20px 40vh; z-index: 0; }
      .koda-login-headline { font-size: 26px; }
      .koda-login-tagline  { display: none; }
      .koda-login-form-panel { position: relative; z-index: 1; margin-top: 40vh; background: rgba(13,17,23,0.88); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(124,58,237,0.3); border-radius: 18px 18px 0 0; border-inline-start: none; border-bottom: none; min-height: 60vh; justify-content: flex-start; padding: 28px 20px; }
    }
  </style>
</head>
<body>
<div class="koda-login-wrap">
  <div class="koda-login-hero">
    <div class="koda-hero-texture"></div>
    <div class="koda-hero-glow koda-hero-glow--br"></div>
    <div class="koda-hero-brand">
      <span class="koda-phi" aria-hidden="true"></span>
      <span class="koda-wordmark">Koda</span>
    </div>
    <div class="hero-body">
      <div class="koda-login-eyebrow">Precision Training System</div>
      <h1 class="koda-login-headline">Structure is<br>the edge<br>you need.</h1>
      <p class="koda-login-tagline">Generate personalised strength workouts and push them directly to Garmin Connect.</p>
      <div class="koda-quote">
        <p id="heroQuote">Turn intention into architecture.</p>
      </div>
    </div>
  </div>

  <div class="koda-login-form-panel">
    <div class="koda-form-eyebrow">New Account</div>
    <h2 class="koda-form-title">Create Koda Account</h2>
    <p class="koda-form-sub">{{ t('auth_register_sub') }}</p>

    {% if error %}
    <div style="background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.3);border-radius:8px;padding:10px 14px;margin-bottom:16px;color:#f87171;font-size:13px;">
      {{ error }}
    </div>
    {% endif %}

    <form method="post" action="{{ url_for('register') }}" id="registerForm" novalidate>
      <div class="koda-field">
        <label for="name">{{ t('auth_name') }} <span style="color:var(--text-muted);">{{ t('auth_optional') }}</span></label>
        <input id="name" name="name" type="text" class="koda-input"
               placeholder="Your name" autocomplete="name">
      </div>
      <div class="koda-field">
        <label for="email">{{ t('auth_email') }}</label>
        <input id="email" name="email" type="email" class="koda-input"
               placeholder="you@example.com" autocomplete="email" required>
      </div>
      <div class="koda-field">
        <label for="password">{{ t('auth_password') }} <span style="color:var(--text-muted);">{{ t('auth_min_chars') }}</span></label>
        <div class="koda-input-group">
          <input id="password" name="password" type="password" class="koda-input"
                 placeholder="••••••••" autocomplete="new-password" required minlength="8">
          <button type="button" class="koda-input-toggle" id="pwToggle" aria-label="Show password">&#128065;</button>
        </div>
      </div>
      <button type="submit" class="btn-koda-primary w-100 justify-content-center mt-2" id="registerBtn">
        <span class="koda-spinner" aria-hidden="true"></span>
        <span class="koda-btn-label">{{ t('auth_create_btn') }}</span>
      </button>
    </form>

    <div class="koda-form-footer">
      {{ t('auth_have_account') }}
      <a href="{{ url_for('login_page') }}" style="color:var(--color-brand-light);font-weight:600;">
        {{ t('auth_sign_in_link') }} →
      </a>
    </div>
  </div>
</div>

<script>
(function() {
  var pwToggle = document.getElementById('pwToggle');
  var pwField  = document.getElementById('password');
  if (pwToggle && pwField) {
    pwToggle.addEventListener('click', function() {
      pwField.type = pwField.type === 'text' ? 'password' : 'text';
    });
  }
  var form = document.getElementById('registerForm');
  var btn  = document.getElementById('registerBtn');
  var MSG  = '{{ t("auth_creating") }}';
  if (form && btn) {
    form.addEventListener('submit', function() {
      btn.disabled = true;
      btn.classList.add('is-loading');
      btn.querySelector('.koda-btn-label').textContent = MSG;
    });
  }
  var quotes = ['The steady baseline compounds.','Structure is the edge you need.','Turn intention into architecture.','Consistency is the infrastructure.','Precision over hype. Every session.'];
  var el = document.getElementById('heroQuote');
  var idx = 2;
  if (el) {
    setInterval(function() {
      var qb = el.closest('.koda-quote');
      if (qb) qb.classList.add('fade-out');
      setTimeout(function() {
        idx = (idx + 1) % quotes.length;
        el.textContent = quotes[idx];
        if (qb) qb.classList.remove('fade-out');
      }, 400);
    }, 8000);
  }
})();
</script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add web/templates/register.html
git commit -m "feat(koda): rebuild register page with cinematic hero layout"
```

---

## Task 5: Dashboard Template

**Files:**
- Replace: `web/templates/dashboard.html`

The dashboard uses `{% block main_class %}{% endblock %}` (empty) to escape the default container, then manages its own layout.

- [ ] **Step 1: Read the current dashboard.html to identify all Jinja2 variables and form field names in use**

Run: `grep -n '{{\\|{%\\|name=' web/templates/dashboard.html`
Note every variable (`current_user`, `goals`, `equipment_list`, `duration`, `lang`, etc.) and form field names so they are preserved exactly.

- [ ] **Step 2: Replace dashboard.html**

```html
{% extends "base.html" %}
{% block title %}Generate — Koda{% endblock %}
{% block main_class %}{% endblock %}

{% block content %}
<!-- Greeting bar -->
<div class="koda-greeting-bar">
  <div class="koda-hero-texture"></div>
  <div class="koda-hero-glow koda-hero-glow--br" style="width:300px;height:300px;"></div>
  <div class="container-xl px-3 px-lg-4" style="position:relative;z-index:1;">
    <div class="row align-items-center g-3">
      <div class="col-auto">
        <div class="koda-greeting-day" id="greetingDay"></div>
        <h1 class="koda-greeting">
          {{ t('dashboard_greeting', name=(current_user.name or '').split()[0] if current_user.name else '') }}
        </h1>
      </div>
      <div class="col"></div>
      <div class="col-auto d-flex gap-2">
        <div class="koda-stat-pill">
          <div class="koda-stat-pill-value" id="statPlans">{{ plan_count|default(0) }}</div>
          <div class="koda-stat-pill-label">Plans</div>
        </div>
        <div class="koda-stat-pill">
          <div class="koda-stat-pill-value" id="statRate">{{ completion_rate|default('—') }}</div>
          <div class="koda-stat-pill-label">Completion</div>
        </div>
        <div class="koda-stat-pill d-none d-md-block">
          <div class="koda-stat-pill-value">{{ program_count|default(0) }}</div>
          <div class="koda-stat-pill-label">Programs</div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Mobile section toggle -->
<div class="koda-section-toggle" id="sectionToggle">
  <button class="active" data-target="generatorSection" id="toggleGenerate">Generate</button>
  <button data-target="previewSection" id="togglePreview">Preview</button>
</div>

<!-- Main two-panel layout -->
<div class="container-xl px-3 px-lg-4 py-4">
  <div class="row g-4">

    <!-- Generator panel -->
    <div class="col-lg-4" id="generatorSection">
      <div class="koda-card h-100">
        <form method="post" action="{{ url_for('generate') }}" id="generateForm">

          <!-- Goal -->
          <div class="koda-section-label">{{ t('form_workout_goal') }}</div>
          <div class="row g-2 mb-4" id="goalGrid">
            {% set goal_icons = {
              'burn_fat': '🔥', 'lose_weight': '⚡', 'build_muscle': '💪',
              'build_strength': '🏋️', 'general_fitness': '🎯', 'endurance': '🏃'
            } %}
            {% for goal_key in ['burn_fat','lose_weight','build_muscle','build_strength','general_fitness','endurance'] %}
            <div class="col-4">
              <label class="koda-goal-card{% if selected_goal == goal_key %} selected{% endif %}" data-goal="{{ goal_key }}">
                <input type="radio" name="goal" value="{{ goal_key }}"
                       {% if selected_goal == goal_key %}checked{% endif %}>
                <div class="koda-goal-icon">{{ goal_icons[goal_key] }}</div>
                <div class="koda-goal-name">{{ t('goal_label_' + goal_key) }}</div>
              </label>
            </div>
            {% endfor %}
          </div>

          <!-- Equipment -->
          <div class="koda-section-label mb-2">{{ t('form_available_equipment') }}</div>
          <select id="equipment" name="equipment" multiple class="mb-1" autocomplete="off">
            {% for eq_key in equipment_list %}
            <option value="{{ eq_key }}"
              {% if eq_key in selected_equipment %}selected{% endif %}>
              {{ t('eq_' + eq_key) }}
            </option>
            {% endfor %}
          </select>
          <div style="font-size:11px;color:var(--text-muted);margin-bottom:20px;">
            {{ t('form_equipment_hint') }}
          </div>

          <!-- Duration -->
          <div class="koda-section-label">{{ t('form_session_duration') }}</div>
          <div class="d-flex align-items-baseline gap-2 mb-2">
            <span class="koda-duration-value" id="durationDisplay">{{ duration|default(45) }}</span>
            <span style="color:var(--text-secondary);font-size:13px;">{{ t('form_min') }}</span>
          </div>
          <input type="range" class="koda-range" id="durationSlider" name="duration"
                 min="20" max="90" step="5" value="{{ duration|default(45) }}">
          <div class="d-flex justify-content-between mt-1 mb-4">
            <span style="font-size:11px;color:var(--text-muted);">20 min</span>
            <span style="font-size:11px;color:var(--text-muted);">90 min</span>
          </div>

          <button type="submit" class="btn-koda-primary w-100 justify-content-center" id="generateBtn">
            <span class="koda-spinner" aria-hidden="true"></span>
            <span class="koda-btn-label">⚡ {{ t('form_generate_btn') }}</span>
          </button>
        </form>

        <!-- Muscle map -->
        {% if muscle_map_svg %}
        <div class="mt-4 pt-4" style="border-top:1px solid var(--border-default);">
          <div class="koda-section-label">{{ t('muscle_map_title') }}</div>
          {{ muscle_map_svg|safe }}
          <div class="d-flex gap-3 mt-2">
            <span style="font-size:11px;color:var(--text-muted);">
              <span style="display:inline-block;width:10px;height:10px;background:#a78bfa;border-radius:2px;margin-inline-end:4px;"></span>{{ t('muscle_map_primary') }}
            </span>
            <span style="font-size:11px;color:var(--text-muted);">
              <span style="display:inline-block;width:10px;height:10px;background:rgba(167,139,250,0.4);border-radius:2px;margin-inline-end:4px;"></span>{{ t('muscle_map_secondary') }}
            </span>
          </div>
        </div>
        {% endif %}
      </div>
    </div>

    <!-- Preview panel -->
    <div class="col-lg-8" id="previewSection">
      {% if workout %}
        {% include "workout_preview.html" %}
      {% else %}
      <div class="koda-card h-100 d-flex flex-column align-items-center justify-content-center"
           style="min-height:320px;border-style:dashed;">
        <span class="koda-phi koda-phi--lg mb-3" style="opacity:0.25;" aria-hidden="true"></span>
        <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:18px;color:var(--text-primary);margin-bottom:6px;">
          {{ t('form_placeholder_title') }}
        </div>
        <div style="font-size:13px;color:var(--text-secondary);text-align:center;max-width:280px;">
          {{ t('form_placeholder_body') }}
        </div>
      </div>
      {% endif %}
    </div>

  </div>
</div>
{% endblock %}

{% block scripts %}
<script src="https://cdn.jsdelivr.net/npm/tom-select@2/dist/js/tom-select.complete.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/tom-select@2/dist/css/tom-select.bootstrap5.min.css">
<script>
(function() {
  // Duration slider
  var slider  = document.getElementById('durationSlider');
  var display = document.getElementById('durationDisplay');
  if (slider && display) {
    slider.addEventListener('input', function() {
      display.textContent = this.value;
    });
  }

  // Goal card radio
  document.querySelectorAll('.koda-goal-card').forEach(function(card) {
    card.addEventListener('click', function() {
      document.querySelectorAll('.koda-goal-card').forEach(function(c) { c.classList.remove('selected'); });
      this.classList.add('selected');
    });
  });

  // Generate form — loading state
  var form = document.getElementById('generateForm');
  var btn  = document.getElementById('generateBtn');
  var MSG  = '{{ t("form_generating") }}';
  if (form && btn) {
    form.addEventListener('submit', function() {
      btn.disabled = true;
      btn.classList.add('is-loading');
      btn.querySelector('.koda-btn-label').textContent = MSG;
    });
  }

  // Tom Select
  if (document.getElementById('equipment')) {
    new TomSelect('#equipment', { plugins: ['remove_button'], maxOptions: 50 });
  }

  // Greeting day label
  var dayEl = document.getElementById('greetingDay');
  if (dayEl) {
    var days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
    var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    var now = new Date();
    dayEl.textContent = days[now.getDay()] + ', ' + months[now.getMonth()] + ' ' + now.getDate();
  }

  // Mobile section toggle
  var toggleBtns = document.querySelectorAll('#sectionToggle button');
  toggleBtns.forEach(function(toggleBtn) {
    toggleBtn.addEventListener('click', function() {
      toggleBtns.forEach(function(b) { b.classList.remove('active'); });
      this.classList.add('active');
      var target = document.getElementById(this.dataset.target);
      if (target) { target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    });
  });
})();
</script>
{% endblock %}
```

- [ ] **Step 3: Add `dashboard_greeting` translation key**

In `web/translations.py`, add to the `"en"` dict under `# --- Generator form ---`:

```python
        "dashboard_greeting":  "Good to see you, {name}. Build today\u2019s plan.",
```

- [ ] **Step 4: Commit**

```bash
git add web/templates/dashboard.html web/translations.py
git commit -m "feat(koda): rebuild dashboard with greeting bar and two-panel layout"
```

---

## Task 6: Workout Preview Template

**Files:**
- Replace: `web/templates/workout_preview.html`

This template is `{% include %}`d inside the dashboard preview panel. It must preserve all JS hooks: `.play-btn-charged`, `.drag-handle`, `.exercise-item`, `.sortable-ghost`, `.sortable-chosen`, `.step-number`, `.btn-garmin`.

- [ ] **Step 1: Read the current workout_preview.html to capture all Jinja2 variables and existing JS initialisation blocks**

Run: `grep -n '{{\\|{%\\|id=\\|class=' web/templates/workout_preview.html | head -80`

- [ ] **Step 2: Replace workout_preview.html**

```html
{# Included inside the preview panel col in dashboard.html — no extends #}
<div class="koda-card koda-card--active" id="workoutCard">

  <!-- Header row -->
  <div class="d-flex align-items-start gap-3 mb-3">
    <div class="flex-grow-1">
      <div style="font-size:11px;color:var(--color-brand-light);font-weight:600;text-transform:uppercase;letter-spacing:2px;margin-bottom:4px;">
        {{ workout.goal_label }}
      </div>
      <h2 style="font-family:'Syne',sans-serif;font-weight:800;font-size:20px;color:var(--text-primary);margin:0 0 4px;">
        {{ workout.name }}
      </h2>
      <div style="font-size:12px;color:var(--text-secondary);">{{ workout.description }}</div>
    </div>
    <div class="d-flex align-items-center gap-2 flex-shrink-0">
      <button class="play-btn-charged" id="playBtn" aria-label="{{ t('preview_exercises') }}">▶</button>
      <span class="koda-badge koda-badge--violet" style="font-family:'JetBrains Mono',monospace;">
        {{ workout.duration_minutes }} {{ t('form_min') }}
      </span>
    </div>
  </div>

  <!-- Stats row -->
  <div class="row g-2 mb-4">
    <div class="col-4">
      <div class="koda-stat-card">
        <div class="koda-stat-value">{{ workout.exercise_count }}</div>
        <div class="koda-stat-label">{{ t('preview_exercises') }}</div>
      </div>
    </div>
    <div class="col-4">
      <div class="koda-stat-card">
        <div class="koda-stat-value">{{ workout.sets_each }}</div>
        <div class="koda-stat-label">{{ t('preview_sets_each') }}</div>
      </div>
    </div>
    <div class="col-4">
      <div class="koda-stat-card">
        <div class="koda-stat-value">{{ workout.rep_range }}</div>
        <div class="koda-stat-label">{{ t('preview_reps_per_set') }}</div>
      </div>
    </div>
  </div>

  <!-- Exercise list -->
  <div class="koda-section-label">Exercises</div>

  <!-- Warm-up -->
  <div class="koda-badge koda-badge--slate mb-2">{{ t('badge_warmup') }}</div>
  <div class="exercise-item mb-3">
    <span class="step-number">W</span>
    <span style="font-size:13px;color:var(--text-body);flex:1;">{{ t('preview_warmup_label') }}</span>
  </div>

  <!-- Circuit blocks -->
  <div id="exerciseList">
    {% for block in workout.blocks %}
    <div class="koda-circuit-block mb-2" data-block-index="{{ loop.index0 }}">
      <div class="koda-circuit-header">
        <span class="koda-badge koda-badge--violet">{{ t('badge_circuit') }}</span>
        <span style="font-size:11px;color:var(--text-secondary);margin-inline-start:6px;">
          {{ t('preview_circuit_desc_pre') }}{{ block.exercises|length }}{{ t('preview_circuit_desc_post') }}
        </span>
        <span class="ms-auto koda-badge koda-badge--slate">
          {{ t('preview_rounds_badge', n=block.rounds) }}
        </span>
      </div>
      <div class="koda-circuit-body" data-block-sortable>
        {% for ex in block.exercises %}
        <div class="exercise-item" data-exercise-index="{{ loop.index0 }}" data-block="{{ loop.revloop.index0 }}">
          <span class="drag-handle" title="{{ t('edit_drag_to_reorder') }}">⠿</span>
          <span class="step-number">{{ loop.index }}</span>
          <div class="flex-grow-1 min-width-0">
            <div style="font-size:13px;font-weight:600;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
              {{ ex.display_name }}
            </div>
            <div style="font-size:11px;color:var(--text-secondary);">
              {{ ex.sets }}×
              {% if ex.hold_seconds %}{{ ex.hold_seconds }}{{ t('preview_hold') }}
              {% else %}{{ ex.reps_display }} {{ t('preview_reps') }}{% endif %}
              · {{ ex.rest_seconds }}{{ t('preview_rest') }}
              {% if ex.needs %} · {{ t('preview_needs') }} {{ ex.needs }}{% endif %}
            </div>
          </div>
          <div class="d-flex gap-1 flex-shrink-0">
            {% if ex.video_url %}
            <a href="{{ ex.video_url }}" target="_blank" rel="noopener"
               class="btn-koda-ghost" style="padding:5px 8px;font-size:11px;border-radius:6px;"
               title="{{ t('preview_tutorial') }}">▶</a>
            {% endif %}
            <button class="btn-koda-ghost" style="padding:5px 8px;font-size:11px;border-radius:6px;"
                    data-action="replace" data-exercise="{{ ex.key }}"
                    title="{{ t('edit_replace') }}">⇄</button>
            <button class="btn-koda-ghost" style="padding:5px 8px;font-size:11px;border-radius:6px;color:var(--color-danger-lt);"
                    data-action="remove" data-exercise="{{ ex.key }}"
                    title="{{ t('edit_remove') }}">✕</button>
          </div>
        </div>
        {% endfor %}
      </div>
      <div style="padding:8px 14px;font-size:11px;color:var(--text-muted);border-top:1px solid var(--border-default);">
        {{ t('preview_round_footer_pre') }}{{ block.rounds }}{{ t('preview_round_footer_post') }}
      </div>
    </div>
    {% endfor %}
  </div>

  <!-- Cool-down -->
  <div class="koda-badge koda-badge--slate mb-2 mt-1">{{ t('badge_cooldown') }}</div>
  <div class="exercise-item mb-4">
    <span class="step-number">C</span>
    <span style="font-size:13px;color:var(--text-body);flex:1;">{{ t('preview_cooldown_label') }}</span>
  </div>

  <!-- Action buttons -->
  <div class="d-flex flex-wrap gap-2">
    {% if garmin_connected %}
    <form method="post" action="{{ url_for('upload_workout') }}" id="uploadForm" style="flex:1;">
      <button type="submit" class="btn-koda-success w-100 justify-content-center" id="uploadBtn">
        <span class="koda-spinner" aria-hidden="true"></span>
        <span class="koda-btn-label">{{ t('preview_upload_garmin') }} ↑</span>
      </button>
    </form>
    {% else %}
    <a href="{{ url_for('login_page') }}" class="btn-koda-secondary" style="flex:1;justify-content:center;">
      {{ t('preview_connect_btn') }}
    </a>
    {% endif %}

    <form method="post" action="{{ url_for('save_plan') }}" id="saveForm">
      <button type="submit" class="btn-koda-secondary" id="saveBtn">
        <span class="koda-spinner" aria-hidden="true"></span>
        <span class="koda-btn-label">{{ t('preview_save_plans') }}</span>
      </button>
    </form>
  </div>

  {% if schedule_date is defined %}
  <div class="mt-3">
    <div class="koda-section-label">{{ t('preview_schedule_label') }}</div>
    <input type="date" name="schedule_date" class="koda-input" value="{{ schedule_date or '' }}"
           style="max-width:180px;">
    <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">{{ t('preview_schedule_hint') }}</div>
  </div>
  {% endif %}

</div>

<script>
(function() {
  // Upload button loading state
  var uploadForm = document.getElementById('uploadForm');
  var uploadBtn  = document.getElementById('uploadBtn');
  if (uploadForm && uploadBtn) {
    uploadForm.addEventListener('submit', function() {
      uploadBtn.disabled = true;
      uploadBtn.classList.add('is-loading');
      uploadBtn.querySelector('.koda-btn-label').textContent = '{{ t("preview_uploading") }}';
    });
  }

  // Save button loading state
  var saveForm = document.getElementById('saveForm');
  var saveBtn  = document.getElementById('saveBtn');
  if (saveForm && saveBtn) {
    saveForm.addEventListener('submit', function() {
      saveBtn.disabled = true;
      saveBtn.classList.add('is-loading');
      saveBtn.querySelector('.koda-btn-label').textContent = '{{ t("preview_saving") }}';
    });
  }
})();
</script>
```

- [ ] **Step 3: Commit**

```bash
git add web/templates/workout_preview.html
git commit -m "feat(koda): rebuild workout preview card with Koda stat cards and action buttons"
```

---

## Task 7: My Plans Page

**Files:**
- Replace: `web/templates/my_plans.html`

- [ ] **Step 1: Replace my_plans.html**

```html
{% extends "base.html" %}
{% block title %}{{ t('plans_title') }} — Koda{% endblock %}
{% block main_class %}{% endblock %}

{% block content %}
<!-- Page hero -->
<div class="koda-page-hero">
  <div class="koda-hero-texture"></div>
  <div class="koda-hero-glow koda-hero-glow--br" style="width:260px;height:260px;opacity:0.5;"></div>
  <div class="container-xl px-3 px-lg-4" style="position:relative;z-index:1;">
    <div class="d-flex align-items-end justify-content-between flex-wrap gap-3">
      <div>
        <div class="koda-eyebrow">Training Library</div>
        <h1 class="koda-page-title">{{ t('plans_title') }}</h1>
      </div>
      <div class="d-flex align-items-center gap-2">
        {% if plans %}
        <span class="koda-badge koda-badge--slate">{{ plans|length }} {{ t('plans_saved') }}</span>
        {% endif %}
        <a href="{{ url_for('dashboard') }}" class="btn-koda-primary" style="padding:8px 14px;font-size:13px;">
          + {{ t('plans_generate_new') }}
        </a>
      </div>
    </div>
  </div>
</div>

<div class="container-xl px-3 px-lg-4 py-4">
  {% if plans %}
  <div class="row g-3">
    {% for plan in plans %}
    <div class="col-12 col-sm-6 col-xl-4">
      <div class="koda-plan-card{% if plan.is_recent %} koda-plan-card--active{% endif %}">
        <div class="koda-plan-card-body">
          <div class="d-flex align-items-start gap-2 mb-2">
            <span style="font-size:22px;">{{ plan.goal_icon }}</span>
            <div>
              <div style="font-size:15px;font-weight:700;color:var(--text-primary);margin-bottom:2px;">{{ plan.name }}</div>
              <div style="font-size:11px;color:var(--text-secondary);">{{ plan.muscle_groups }}</div>
            </div>
          </div>
          <div class="d-flex flex-wrap gap-1 mt-2">
            <span class="koda-badge koda-badge--violet">{{ plan.goal_label }}</span>
            <span class="koda-badge koda-badge--slate">{{ plan.duration_minutes }} {{ t('form_min') }}</span>
            {% if plan.status == 'uploaded' %}
            <span class="koda-badge koda-badge--green">Uploaded</span>
            {% endif %}
          </div>
        </div>
        <div class="koda-plan-card-footer">
          <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-muted);">
            {{ plan.created_at }}
          </span>
          <div class="d-flex gap-1">
            <a href="{{ url_for('preview_plan', plan_id=plan.id) }}"
               class="btn-koda-ghost" style="padding:5px 10px;font-size:12px;">
              {{ t('plans_preview') }}
            </a>
            <form method="post" action="{{ url_for('delete_plan', plan_id=plan.id) }}"
                  onsubmit="return confirm('{{ t('plans_delete_confirm') }}')">
              <button type="submit" class="btn-koda-ghost"
                      style="padding:5px 10px;font-size:12px;color:var(--color-danger-lt);">✕</button>
            </form>
          </div>
        </div>
      </div>
    </div>
    {% endfor %}
  </div>

  {% else %}
  <div class="koda-empty">
    <span class="koda-phi koda-phi--lg" aria-hidden="true"></span>
    <div class="koda-empty-title">{{ t('plans_no_plans') }}</div>
    <p class="koda-empty-body">{{ t('plans_no_plans_desc') }}</p>
    <a href="{{ url_for('dashboard') }}" class="btn-koda-primary mt-3" style="display:inline-flex;">
      {{ t('plans_generate_btn') }}
    </a>
  </div>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add web/templates/my_plans.html
git commit -m "feat(koda): rebuild My Plans with page hero, card grid, and empty state"
```

---

## Task 8: Programs Pages

**Files:**
- Replace: `web/templates/my_programs.html`
- Replace: `web/templates/my_program_detail.html`

- [ ] **Step 1: Replace my_programs.html**

```html
{% extends "base.html" %}
{% block title %}{{ t('nav_programs') }} — Koda{% endblock %}
{% block main_class %}{% endblock %}

{% block content %}
<div class="koda-page-hero">
  <div class="koda-hero-texture"></div>
  <div class="koda-hero-glow koda-hero-glow--br" style="width:260px;height:260px;opacity:0.5;"></div>
  <div class="container-xl px-3 px-lg-4" style="position:relative;z-index:1;">
    <div class="d-flex align-items-end justify-content-between flex-wrap gap-3">
      <div>
        <div class="koda-eyebrow">Training Architecture</div>
        <h1 class="koda-page-title">{{ t('nav_programs') }}</h1>
      </div>
    </div>
  </div>
</div>

<div class="container-xl px-3 px-lg-4 py-4">
  {% if programs %}
  <div class="row g-3">
    {% for prog in programs %}
    <div class="col-12 col-sm-6 col-xl-4">
      <div class="koda-plan-card">
        <div class="koda-plan-card-body">
          <div class="d-flex align-items-start gap-2 mb-2">
            <span style="font-size:22px;">{{ prog.goal_icon }}</span>
            <div>
              <div style="font-size:15px;font-weight:700;color:var(--text-primary);margin-bottom:2px;">{{ prog.name }}</div>
            </div>
          </div>
          <div class="d-flex flex-wrap gap-1 mt-2">
            <span class="koda-badge koda-badge--violet">{{ prog.duration_weeks }}w</span>
            {% if prog.status == 'active' %}
            <span class="koda-badge koda-badge--green">Active</span>
            {% elif prog.status == 'completed' %}
            <span class="koda-badge koda-badge--slate">Completed</span>
            {% elif prog.status == 'paused' %}
            <span class="koda-badge koda-badge--amber">Paused</span>
            {% endif %}
            {% if prog.periodization %}
            <span class="koda-badge koda-badge--slate">{{ prog.periodization }}</span>
            {% endif %}
          </div>
        </div>
        <div class="koda-plan-card-footer">
          <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-muted);">
            {{ prog.created_at }}
          </span>
          <div class="d-flex gap-1">
            <a href="{{ url_for('program_detail', program_id=prog.id) }}"
               class="btn-koda-ghost" style="padding:5px 10px;font-size:12px;">View</a>
            <form method="post" action="{{ url_for('delete_program', program_id=prog.id) }}"
                  onsubmit="return confirm('Delete this program?')">
              <button type="submit" class="btn-koda-ghost"
                      style="padding:5px 10px;font-size:12px;color:var(--color-danger-lt);">✕</button>
            </form>
          </div>
        </div>
      </div>
    </div>
    {% endfor %}
  </div>
  {% else %}
  <div class="koda-empty">
    <span class="koda-phi koda-phi--lg" aria-hidden="true"></span>
    <div class="koda-empty-title">No programs yet.</div>
    <p class="koda-empty-body">Programs are multi-week training plans. Generate and save workouts to build one.</p>
    <a href="{{ url_for('dashboard') }}" class="btn-koda-primary mt-3" style="display:inline-flex;">
      Generate a Workout
    </a>
  </div>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 2: Replace my_program_detail.html**

```html
{% extends "base.html" %}
{% block title %}{{ program.name }} — Koda{% endblock %}
{% block main_class %}{% endblock %}

{% block content %}
<div class="koda-page-hero">
  <div class="koda-hero-texture"></div>
  <div class="container-xl px-3 px-lg-4" style="position:relative;z-index:1;">
    <div>
      <a href="{{ url_for('my_programs') }}"
         style="font-size:12px;color:var(--text-secondary);text-decoration:none;display:inline-flex;align-items:center;gap:4px;margin-bottom:10px;">
        ← Programs
      </a>
      <div class="d-flex align-items-center gap-2 mb-1">
        <h1 class="koda-page-title" style="margin:0;">{{ program.name }}</h1>
        {% if program.status == 'active' %}
        <span class="koda-badge koda-badge--green">Active</span>
        {% elif program.status == 'completed' %}
        <span class="koda-badge koda-badge--slate">Completed</span>
        {% elif program.status == 'paused' %}
        <span class="koda-badge koda-badge--amber">Paused</span>
        {% endif %}
      </div>
    </div>
  </div>
</div>

<div class="container-xl px-3 px-lg-4 py-4">
  <div class="koda-card">
    <div class="koda-section-label mb-3">Sessions</div>
    {% if sessions %}
    <div style="overflow-x:auto;">
      <table class="koda-table">
        <thead>
          <tr>
            <th>Week</th>
            <th>Day</th>
            <th>Focus</th>
            <th>Scheduled</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {% for session in sessions %}
          <tr>
            <td style="font-family:'JetBrains Mono',monospace;color:var(--color-brand-light);">
              W{{ session.week }}
            </td>
            <td>{{ session.day }}</td>
            <td style="font-weight:500;color:var(--text-primary);">{{ session.focus }}</td>
            <td style="font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--text-secondary);">
              {{ session.scheduled_date or '—' }}
            </td>
            <td>
              {% if session.status == 'done' %}
              <span class="koda-badge koda-badge--green">Done</span>
              {% elif session.status == 'in_progress' %}
              <span class="koda-badge koda-badge--amber">In Progress</span>
              {% else %}
              <span class="koda-badge koda-badge--slate">Scheduled</span>
              {% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
    <div class="koda-empty" style="padding:40px 0;">
      <div class="koda-empty-title" style="font-size:16px;">No sessions scheduled yet.</div>
    </div>
    {% endif %}
  </div>
</div>
{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add web/templates/my_programs.html web/templates/my_program_detail.html
git commit -m "feat(koda): rebuild Programs and Program Detail pages"
```

---

## Task 9: Progress Page

**Files:**
- Replace: `web/templates/my_progress.html`

- [ ] **Step 1: Replace my_progress.html**

```html
{% extends "base.html" %}
{% block title %}{{ t('progress_title') }} — Koda{% endblock %}
{% block main_class %}{% endblock %}

{% block content %}
<div class="koda-page-hero">
  <div class="koda-hero-texture"></div>
  <div class="koda-hero-glow koda-hero-glow--br" style="width:260px;height:260px;opacity:0.5;"></div>
  <div class="container-xl px-3 px-lg-4" style="position:relative;z-index:1;">
    <div class="row align-items-end g-3">
      <div class="col">
        <div class="koda-eyebrow">Performance Tracking</div>
        <h1 class="koda-page-title">{{ t('progress_title') }}</h1>
      </div>
      <div class="col-auto d-none d-md-block">
        <div class="koda-quote" style="max-width:320px;">
          <p id="heroQuote" style="font-size:13px;">Precision over hype. Every session.</p>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="container-xl px-3 px-lg-4 py-4">

  <!-- Summary stats -->
  <div class="row g-3 mb-4">
    <div class="col-6 col-md-3">
      <div class="koda-stat-card">
        <div class="koda-stat-value">{{ stats.total_sessions|default(0) }}</div>
        <div class="koda-stat-label">{{ t('progress_sessions') }}</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div class="koda-stat-card">
        <div class="koda-stat-value">{{ stats.completed|default(0) }}</div>
        <div class="koda-stat-label">{{ t('progress_completed') }}</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div class="koda-stat-card">
        <div class="koda-stat-value">{{ stats.finish_rate|default('—') }}</div>
        <div class="koda-stat-label">{{ t('progress_finish_rate') }}</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div class="koda-stat-card">
        <div class="koda-stat-value">{{ stats.total_minutes|default(0) }}</div>
        <div class="koda-stat-label">{{ t('progress_total_min') }}</div>
      </div>
    </div>
  </div>

  <!-- Session history -->
  <div class="koda-card">
    <div class="koda-section-label mb-3">Session History</div>
    {% if sessions %}
    <div style="overflow-x:auto;">
      <table class="koda-table">
        <thead>
          <tr>
            <th>{{ t('progress_workout') }}</th>
            <th>{{ t('progress_date') }}</th>
            <th>{{ t('progress_duration') }}</th>
            <th>{{ t('progress_progress') }}</th>
            <th>{{ t('progress_status') }}</th>
          </tr>
        </thead>
        <tbody>
          {% for session in sessions %}
          <tr>
            <td style="font-weight:500;color:var(--text-primary);">{{ session.workout_name }}</td>
            <td style="font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--text-secondary);">
              {{ session.date }}
            </td>
            <td style="font-family:'JetBrains Mono',monospace;color:var(--color-brand-light);">
              {{ session.duration_minutes }} {{ t('form_min') }}
            </td>
            <td style="min-width:120px;">
              <div class="koda-progress-track" style="margin-bottom:4px;">
                <div class="koda-progress-fill" style="width:{{ session.completion_pct }}%;"></div>
              </div>
              <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-muted);">
                {{ session.sets_done }}/{{ session.sets_total }}
              </span>
            </td>
            <td>
              {% if session.status == 'done' %}
              <span class="koda-badge koda-badge--green">{{ t('progress_done') }}</span>
              {% elif session.status == 'in_progress' %}
              <span class="koda-badge koda-badge--amber">{{ t('progress_in_progress') }}</span>
              {% else %}
              <span class="koda-badge koda-badge--slate">{{ session.status }}</span>
              {% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
    <div class="koda-empty" style="padding:40px 0;">
      <div class="koda-empty-title" style="font-size:16px;">{{ t('progress_no_sessions') }}</div>
      <p class="koda-empty-body">{{ t('progress_no_sessions_desc') }}</p>
      <a href="{{ url_for('dashboard') }}" class="btn-koda-primary mt-3" style="display:inline-flex;">
        {{ t('progress_generate_btn') }}
      </a>
    </div>
    {% endif %}
  </div>

</div>
{% endblock %}

{% block scripts %}
<script>
(function() {
  var quotes = ['The steady baseline compounds.','Structure is the edge you need.','Turn intention into architecture.','Consistency is the infrastructure.','Precision over hype. Every session.'];
  var el = document.getElementById('heroQuote');
  var idx = 4;
  if (el) {
    setInterval(function() {
      var qb = el.closest('.koda-quote');
      if (qb) qb.classList.add('fade-out');
      setTimeout(function() {
        idx = (idx + 1) % quotes.length;
        el.textContent = quotes[idx];
        if (qb) qb.classList.remove('fade-out');
      }, 400);
    }, 8000);
  }
})();
</script>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add web/templates/my_progress.html
git commit -m "feat(koda): rebuild Progress page with stat cards and session history table"
```

---

## Task 10: Profile Page

**Files:**
- Replace: `web/templates/my_profile.html`

- [ ] **Step 1: Replace my_profile.html**

```html
{% extends "base.html" %}
{% block title %}Profile — Koda{% endblock %}
{% block main_class %}{% endblock %}

{% block content %}
<div class="koda-page-hero">
  <div class="koda-hero-texture"></div>
  <div class="container-xl px-3 px-lg-4" style="position:relative;z-index:1;">
    <div class="d-flex align-items-center justify-content-between flex-wrap gap-3">
      <div>
        <div class="koda-eyebrow">Account</div>
        <h1 class="koda-page-title">
          {{ (profile.name or current_user.email or 'Your') }}'s Profile
        </h1>
      </div>
      <a href="{{ url_for('questionnaire') }}" class="btn-koda-ghost">Edit Profile</a>
    </div>
  </div>
</div>

<div class="container-xl px-3 px-lg-4 py-4">
  <div class="row g-4">

    <!-- Avatar card -->
    <div class="col-12 col-md-4 col-lg-3">
      <div class="koda-avatar-card">
        <div class="koda-avatar-lg">
          {{ (profile.name or current_user.email or 'K')[0]|upper }}
        </div>
        <div style="font-weight:700;font-size:17px;color:var(--text-primary);margin-bottom:2px;">
          {{ profile.name or 'Koda User' }}
        </div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--text-secondary);margin-bottom:16px;">
          {{ current_user.email }}
        </div>
        <div class="d-flex justify-content-center gap-3 mb-4">
          <div class="text-center">
            <div style="font-family:'JetBrains Mono',monospace;font-weight:700;font-size:18px;color:var(--color-brand-light);">
              {{ profile.plan_count|default(0) }}
            </div>
            <div style="font-size:9px;text-transform:uppercase;letter-spacing:2px;color:var(--text-muted);">Plans</div>
          </div>
          <div style="width:1px;background:var(--border-default);"></div>
          <div class="text-center">
            <div style="font-family:'JetBrains Mono',monospace;font-weight:700;font-size:18px;color:var(--color-brand-light);">
              {{ profile.session_count|default(0) }}
            </div>
            <div style="font-size:9px;text-transform:uppercase;letter-spacing:2px;color:var(--text-muted);">Sessions</div>
          </div>
        </div>
        <hr style="border-color:var(--border-default);margin:0 0 16px;">
        {% if not garmin_connected %}
        <a href="{{ url_for('login_page') }}" class="btn-koda-primary w-100 justify-content-center" style="font-size:13px;">
          Reconnect Garmin
        </a>
        {% else %}
        <div class="koda-badge-connected justify-content-center w-100" style="padding:8px;">
          <span class="koda-badge-dot"></span>
          Garmin Connected
        </div>
        {% endif %}
      </div>
    </div>

    <!-- Fitness profile -->
    <div class="col-12 col-md-8 col-lg-9">
      {% if profile.has_questionnaire %}
      <div class="koda-card mb-3">
        <div class="koda-section-label mb-2">Fitness Profile</div>
        <div class="koda-info-row">
          <span class="koda-info-label">Age</span>
          <span class="koda-info-value">{{ profile.age or '—' }}</span>
        </div>
        <div class="koda-info-row">
          <span class="koda-info-label">Fitness Level</span>
          <span class="koda-info-value">{{ profile.fitness_level|title or '—' }}</span>
        </div>
        <div class="koda-info-row">
          <span class="koda-info-label">Training Days / Week</span>
          <span class="koda-info-value" style="font-family:'JetBrains Mono',monospace;color:var(--color-brand-light);">
            {{ profile.weekly_days or '—' }}
          </span>
        </div>
        {% if profile.height or profile.weight %}
        <div class="koda-info-row">
          <span class="koda-info-label">Height / Weight</span>
          <span class="koda-info-value" style="font-family:'JetBrains Mono',monospace;">
            {{ profile.height or '—' }} cm / {{ profile.weight or '—' }} kg
          </span>
        </div>
        {% endif %}
      </div>

      {% if profile.goals %}
      <div class="koda-card mb-3">
        <div class="koda-section-label mb-2">Goals</div>
        <div class="d-flex flex-wrap gap-2">
          {% for g in profile.goals %}
          <span class="koda-badge koda-badge--violet">{{ g }}</span>
          {% endfor %}
        </div>
      </div>
      {% endif %}

      {% if profile.equipment %}
      <div class="koda-card mb-3">
        <div class="koda-section-label mb-2">Equipment</div>
        <div class="d-flex flex-wrap gap-2">
          {% for eq in profile.equipment %}
          <span class="koda-badge koda-badge--slate">{{ t('eq_' + eq) }}</span>
          {% endfor %}
        </div>
      </div>
      {% endif %}

      {% if profile.health_conditions %}
      <div class="koda-card">
        <div class="koda-section-label mb-2">Health Notes</div>
        <div class="d-flex flex-wrap gap-2">
          {% for h in profile.health_conditions %}
          <span class="koda-badge koda-badge--amber">{{ h }}</span>
          {% endfor %}
        </div>
      </div>
      {% endif %}

      {% else %}
      <div class="koda-card">
        <div class="koda-empty" style="padding:40px 0;">
          <span class="koda-phi koda-phi--lg" aria-hidden="true"></span>
          <div class="koda-empty-title" style="font-size:18px;margin-top:12px;">Complete your fitness profile</div>
          <p class="koda-empty-body">Answer a few questions so Koda can personalise your workouts.</p>
          <a href="{{ url_for('questionnaire') }}" class="btn-koda-primary mt-3" style="display:inline-flex;">
            Set Up Profile
          </a>
        </div>
      </div>
      {% endif %}
    </div>

  </div>
</div>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add web/templates/my_profile.html
git commit -m "feat(koda): rebuild Profile page with avatar card and fitness info sections"
```

---

## Task 11: Questionnaire

**Files:**
- Modify: `web/templates/questionnaire.html`

The questionnaire has complex JS (step transitions, tag selection, slider). Preserve all JS exactly. Only update the color token references in inline styles from old Garmin blue values to Koda tokens.

- [ ] **Step 1: Read the full questionnaire template**

Run: `cat -n web/templates/questionnaire.html`

- [ ] **Step 2: Update colour values in inline styles only**

Find these specific old values and replace them:
- `#0066cc` → `var(--color-brand)` (or `#7c3aed`)
- `#0066CC` → `var(--color-brand)`
- `background-color: #1a1d20` → `background-color: var(--color-card)`
- `border: 1px solid #2d3139` → `border: 1px solid var(--border-default)`

Do NOT change any JS logic, class names, element IDs, or structure.

Use targeted `Edit` operations — one per changed value to avoid unintended matches.

- [ ] **Step 3: Commit**

```bash
git add web/templates/questionnaire.html
git commit -m "feat(koda): update questionnaire color tokens to Koda brand palette"
```

---

## Task 12: Auth Utility Pages (MFA, SSO, Waiting)

**Files:**
- Replace: `web/templates/mfa.html`
- Replace: `web/templates/sso.html`
- Replace: `web/templates/waiting.html`

- [ ] **Step 1: Replace mfa.html**

```html
{% extends "base.html" %}
{% block title %}Verification — Koda{% endblock %}

{% block content %}
<div class="koda-auth-centered">
  <div class="koda-auth-card">
    <span class="koda-phi koda-phi--lg mx-auto mb-4" aria-hidden="true"
          style="display:flex;"></span>
    <h1 style="font-family:'Syne',sans-serif;font-weight:800;font-size:22px;color:var(--text-primary);margin-bottom:6px;">
      Two-Factor Authentication
    </h1>
    <p style="font-size:13px;color:var(--text-secondary);margin-bottom:24px;">
      Enter the 6-digit code from your authenticator app.
    </p>

    {% if error %}
    <div style="background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.3);border-radius:8px;padding:10px 14px;margin-bottom:16px;color:#f87171;font-size:13px;">
      {{ error }}
    </div>
    {% endif %}

    <form method="post" action="{{ url_for('mfa_verify') }}" id="mfaForm" novalidate>
      <div class="koda-field mb-3">
        <input id="mfaCode" name="code" type="text" class="koda-input"
               placeholder="000000"
               autocomplete="one-time-code"
               inputmode="numeric"
               pattern="[0-9]{6}"
               maxlength="6"
               style="text-align:center;font-family:'JetBrains Mono',monospace;font-size:24px;letter-spacing:8px;">
      </div>
      <button type="submit" class="btn-koda-primary w-100 justify-content-center" id="mfaBtn">
        <span class="koda-spinner" aria-hidden="true"></span>
        <span class="koda-btn-label">Verify</span>
      </button>
    </form>
  </div>
</div>
{% endblock %}

{% block scripts %}
<script>
(function() {
  // Auto-submit on 6 digits
  var codeInput = document.getElementById('mfaCode');
  var mfaForm   = document.getElementById('mfaForm');
  var mfaBtn    = document.getElementById('mfaBtn');
  if (codeInput && mfaForm) {
    codeInput.addEventListener('input', function() {
      if (this.value.replace(/\D/g, '').length === 6) {
        this.value = this.value.replace(/\D/g, '');
        if (mfaBtn) {
          mfaBtn.disabled = true;
          mfaBtn.classList.add('is-loading');
          mfaBtn.querySelector('.koda-btn-label').textContent = 'Verifying\u2026';
        }
        mfaForm.submit();
      }
    });
  }
})();
</script>
{% endblock %}
```

- [ ] **Step 2: Replace sso.html**

```html
{% extends "base.html" %}
{% block title %}Connect — Koda{% endblock %}

{% block content %}
<div class="container-xl px-3 px-lg-4 py-5">
  <div class="row justify-content-center">
    <div class="col-12 col-md-8 col-lg-6">
      <div class="koda-card mb-3">
        <div class="text-center mb-4">
          <span class="koda-phi koda-phi--lg mx-auto mb-3" aria-hidden="true"
                style="display:flex;"></span>
          <h1 style="font-family:'Syne',sans-serif;font-weight:800;font-size:20px;color:var(--text-primary);">
            Connect to Garmin
          </h1>
          <p style="font-size:13px;color:var(--text-secondary);">
            Sign in with your Garmin Connect account below.
          </p>
        </div>
        {% if sso_iframe_url %}
        <div style="border:1px solid var(--border-default);border-radius:var(--radius-inner);overflow:hidden;">
          <iframe src="{{ sso_iframe_url }}"
                  style="width:100%;min-height:480px;border:none;background:var(--color-card);"
                  title="Garmin Connect SSO">
          </iframe>
        </div>
        {% endif %}
      </div>
      <div class="text-center">
        <a href="{{ url_for('dashboard') }}"
           style="font-size:13px;color:var(--text-secondary);">← Back to dashboard</a>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 3: Replace waiting.html**

```html
{% extends "base.html" %}
{% block title %}Connecting — Koda{% endblock %}

{% block content %}
<div class="koda-auth-centered">
  <div class="koda-auth-card">
    <div style="width:48px;height:48px;border:3px solid rgba(124,58,237,0.2);border-top-color:var(--color-brand);border-radius:50%;animation:koda-spin 0.8s linear infinite;margin:0 auto 20px;">
    </div>
    <h1 style="font-family:'Syne',sans-serif;font-weight:800;font-size:20px;color:var(--text-primary);margin-bottom:6px;">
      {{ status_message|default('Connecting to Garmin Connect\u2026') }}
    </h1>
    <p style="font-size:13px;color:var(--text-secondary);">
      This usually takes just a moment.
    </p>
    {% if redirect_url %}
    <meta http-equiv="refresh" content="3;url={{ redirect_url }}">
    {% endif %}
  </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Commit**

```bash
git add web/templates/mfa.html web/templates/sso.html web/templates/waiting.html
git commit -m "feat(koda): rebuild MFA, SSO, and waiting pages with Koda auth card layout"
```

---

## Task 13: Brand String Updates (GarminForge → Koda)

**Files:**
- Modify: `web/translations.py`

- [ ] **Step 1: Update all "GarminForge" occurrences in translation values**

Search the file:

Run: `grep -n "GarminForge\|Garmin Forge\|garminforge" web/translations.py`

For each match, update the string value to say "Koda" instead. Common locations:
- `"footer_text"` — change from `"unofficial Garmin Connect workout tool"` to `"Your precision training system"`
- `"auth_tagline"` — change from `"Generate personalised strength workouts and send them directly to Garmin Connect."` to `"Structure your training. Push to Garmin Connect."`
- Page `<title>` strings — search for any `"GarminForge"` in title translation values

Use `Edit` for each changed line. Example:

Change:
```python
        "footer_text": "unofficial Garmin Connect workout tool",
```
To:
```python
        "footer_text": "Your precision training system",
```

Change:
```python
        "auth_tagline":         "Generate personalised strength workouts and send them directly to Garmin Connect.",
```
To:
```python
        "auth_tagline":         "Structure your training. Push to Garmin Connect.",
```

- [ ] **Step 2: Update the Hebrew dict with the new `nav_generate` key added in Task 2**

Run: `grep -n '"he"' web/translations.py` to find the Hebrew section, then add:

```python
        "nav_generate":            "צור",
```

- [ ] **Step 3: Add `dashboard_greeting` to the Hebrew dict**

```python
        "dashboard_greeting":  "\u05d8\u05d5\u05d1 \u05dc\u05e8\u05d0\u05d5\u05ea\u05da, {name}. \u05d1\u05e0\u05d4 \u05d0\u05ea \u05ea\u05d5\u05db\u05e0\u05d9\u05ea \u05d4\u05d9\u05d5\u05dd.",
```

(This is: "טוב לראותך, {name}. בנה את תוכנית היום.")

- [ ] **Step 4: Search templates for any remaining hardcoded "GarminForge" text**

Run: `grep -rn "GarminForge\|Garmin Forge" web/templates/`

For each match, replace the literal text with `Koda`.

- [ ] **Step 5: Final check — search app.py for hardcoded brand strings**

Run: `grep -n "GarminForge\|Garmin Forge" web/app.py`

Update any matches found.

- [ ] **Step 6: Commit**

```bash
git add web/translations.py web/app.py web/templates/
git commit -m "feat(koda): replace all GarminForge brand strings with Koda"
```

---

## Final Verification

- [ ] **Start the server and visit each page**

```bash
python run.py &
```

Visit in browser:
1. `http://127.0.0.1:8000/login` — cinematic hero, form panel, quote rotation
2. `http://127.0.0.1:8000/register` — same layout, registration form
3. `http://127.0.0.1:8000/dashboard` — greeting bar, generator, placeholder preview
4. `http://127.0.0.1:8000/plans` — page hero, card grid or empty state
5. `http://127.0.0.1:8000/programs` — page hero, card grid or empty state
6. `http://127.0.0.1:8000/progress` — page hero, stat cards, session table
7. `http://127.0.0.1:8000/profile` — page hero, avatar card, profile info

Check:
- Navbar shows φ + KODA wordmark
- Fonts loaded (Syne, Inter, JetBrains Mono visible)
- Violet accent color throughout
- No broken template errors in server logs
- Mobile view: hamburger visible, login form floats above hero

- [ ] **Kill the server**

```bash
kill %1
```
