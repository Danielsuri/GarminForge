# Questionnaire Wizard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the static scrollable questionnaire form with a step-by-step animated wizard where one question card is visible at a time, transitioning with a fade+scale animation.

**Architecture:** Pure front-end change — only `web/templates/questionnaire.html` is replaced. All 8 cards (7 questions + summary) are server-rendered in the HTML. CSS transitions handle the animation; ~100 lines of vanilla JS handle navigation, progress bar, dot indicators, slider labels, and the summary screen. Native `<input>` elements inside `<label>` wrappers ensure form submission works unchanged. CSS `:has(input:checked)` handles option highlighting without JS.

**Tech Stack:** Jinja2, Bootstrap 5.3.8 (dark theme, already on page), vanilla JS (no new deps), CSS transitions

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `tests/test_questionnaire.py` | Regression test: rendered HTML contains all 7 field names |
| Replace | `web/templates/questionnaire.html` | Full wizard template |

---

### Task 1: Regression test — field names present in rendered page

**Files:**
- Create: `tests/test_questionnaire.py`

- [ ] **Step 1: Write the failing test**

```python
"""
Regression tests for the questionnaire wizard template.
Verifies that the rendered HTML contains all form field names
the backend handler expects — guarding against accidental renames.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from web.app import app
from web.models import User


def _make_user() -> User:
    return User(
        id="test-qx-001",
        email="wizard@test.com",
        questionnaire_completed=False,
        age=None,
        diet_json=None,
        health_conditions_json=None,
        preferred_equipment_json=None,
        fitness_level=None,
        fitness_goals_json=None,
        weekly_workout_days=None,
    )


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


class TestQuestionnaireTemplate:
    def _get_page(self, client):
        user = _make_user()
        with patch("web.routes_my.get_current_user", return_value=user):
            return client.get("/my/questionnaire")

    def test_returns_200(self, client):
        assert self._get_page(client).status_code == 200

    def test_has_age_field(self, client):
        assert 'name="age"' in self._get_page(client).text

    def test_has_fitness_level_field(self, client):
        assert 'name="fitness_level"' in self._get_page(client).text

    def test_has_weekly_workout_days_field(self, client):
        assert 'name="weekly_workout_days"' in self._get_page(client).text

    def test_has_fitness_goals_field(self, client):
        assert 'name="fitness_goals"' in self._get_page(client).text

    def test_has_equipment_field(self, client):
        assert 'name="equipment"' in self._get_page(client).text

    def test_has_diet_field(self, client):
        assert 'name="diet"' in self._get_page(client).text

    def test_has_health_conditions_field(self, client):
        assert 'name="health_conditions"' in self._get_page(client).text

    def test_form_posts_to_questionnaire(self, client):
        assert 'action="/my/questionnaire"' in self._get_page(client).text

    def test_skip_posts_to_skip_route(self, client):
        assert 'action="/my/questionnaire/skip"' in self._get_page(client).text

    def test_seven_wcard_elements(self, client):
        """One card per question (not counting summary)."""
        html = self._get_page(client).text
        assert html.count('class="wcard') >= 7
```

- [ ] **Step 2: Run test — expect FAIL (wcard class doesn't exist in old template)**

```
pytest tests/test_questionnaire.py -v
```

Expected: `test_seven_wcard_elements` FAILS, others PASS (old template has same field names).

- [ ] **Step 3: Commit the test**

```bash
git add tests/test_questionnaire.py
git commit -m "test: add questionnaire wizard template regression tests"
```

---

### Task 2: Replace questionnaire template with animated wizard

**Files:**
- Replace: `web/templates/questionnaire.html`

- [ ] **Step 1: Replace the entire file with the wizard template**

Write the following to `web/templates/questionnaire.html` (complete replacement):

```html
{% extends "base.html" %}
{% block title %}GarminForge — {% if is_retake %}Update Profile{% else %}Set Up Your Profile{% endif %}{% endblock %}

{% block head %}
<style>
.wizard-outer { max-width: 420px; margin: 0 auto; }
.wizard-meta { display: flex; justify-content: space-between; font-size: 11px; color: #666; margin-bottom: 6px; }
.wizard-track { height: 4px; background: #1e2030; border-radius: 2px; margin-bottom: 28px; }
.wizard-fill  { height: 4px; background: #0066cc; border-radius: 2px; transition: width .4s ease; }

.wizard-stage { position: relative; min-height: 360px; }

.wcard {
  background: #1a1d2e;
  border: 1px solid #2a2d40;
  border-radius: 16px;
  padding: 26px 24px;
  position: absolute; top: 0; left: 0; right: 0;
  opacity: 0;
  transform: scale(.94) translateY(14px);
  pointer-events: none;
  transition: opacity .3s ease, transform .3s ease;
  will-change: opacity, transform;
}
.wcard.active {
  opacity: 1; transform: none;
  pointer-events: all;
  position: relative;
}
.wcard.exiting {
  opacity: 0;
  transform: scale(.94) translateY(-10px);
  position: absolute; top: 0; left: 0; right: 0;
  pointer-events: none;
}

.wcard-label { font-size: 11px; font-weight: 600; color: #0066cc; text-transform: uppercase; letter-spacing: .07em; margin-bottom: 8px; }
.wcard-title { font-size: 18px; font-weight: 700; color: #fff; margin-bottom: 20px; line-height: 1.3; }

/* Sliders */
.slider-display { font-size: 42px; font-weight: 800; color: #0066cc; text-align: center; margin-bottom: 10px; line-height: 1; }
.slider-unit   { font-size: 14px; font-weight: 400; color: #666; }
.slider-limits { display: flex; justify-content: space-between; font-size: 11px; color: #555; margin-top: 4px; }
input[type=range].wrange { width: 100%; accent-color: #0066cc; }

/* Option cards — radio and checkbox styled as clickable cards */
.wopts       { display: flex; flex-direction: column; gap: 8px; }
.wopts--row  { flex-direction: row; }
.wopts--grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

.wopt {
  display: flex; align-items: center;
  background: #13151f; border: 1.5px solid #252840; border-radius: 10px;
  padding: 11px 16px; font-size: 14px; color: #bbb; cursor: pointer;
  transition: border-color .18s, background .18s, color .18s; user-select: none;
}
.wopts--row  .wopt { flex: 1; justify-content: center; }
.wopts--grid .wopt { font-size: 13px; padding: 10px 12px; }
.wopt:has(input:checked) { border-color: #0066cc; background: #0066cc18; color: #fff; }
.wopt input { display: none; }

/* Equipment tag cloud */
.wtags { display: flex; flex-wrap: wrap; gap: 7px; }
.wtag {
  display: inline-flex; align-items: center;
  background: #13151f; border: 1.5px solid #252840; border-radius: 20px;
  padding: 6px 14px; font-size: 13px; color: #bbb; cursor: pointer;
  transition: border-color .18s, background .18s, color .18s; user-select: none;
}
.wtag:has(input:checked) { border-color: #0066cc; background: #0066cc22; color: #fff; }
.wtag input { display: none; }

/* Nav buttons */
.wnav      { display: flex; gap: 10px; margin-top: 22px; }
.wnav-back { flex: 1; background: transparent; border: 1.5px solid #252840; border-radius: 10px; padding: 10px 14px; color: #666; font-size: 13px; cursor: pointer; transition: border-color .18s, color .18s; }
.wnav-back:hover { border-color: #444; color: #aaa; }
.wnav-next, .wnav-save { flex: 2.5; background: #0066cc; border: none; border-radius: 10px; padding: 10px 14px; color: #fff; font-size: 14px; font-weight: 600; cursor: pointer; transition: background .18s; }
.wnav-next:hover { background: #0055aa; }
.wnav-save { background: #22863a; }
.wnav-save:hover { background: #1a6b30; }
.wnav-save:disabled { background: #1a2a1a; color: #445; cursor: default; }

/* Dot strip */
.wdots { display: flex; gap: 7px; justify-content: center; margin-top: 20px; }
.wdot { width: 7px; height: 7px; border-radius: 50%; background: #252840; transition: background .3s, transform .3s; }
.wdot--active { background: #0066cc; transform: scale(1.3); }
.wdot--done   { background: #0066cc55; }

/* Summary */
.wsum-row { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 10px; font-size: 13px; }
.wsum-key { color: #666; width: 120px; flex-shrink: 0; padding-top: 3px; }
.wbadge   { display: inline-block; background: #0066cc22; border: 1px solid #0066cc44; color: #7ab8ff; border-radius: 20px; padding: 3px 10px; font-size: 12px; margin: 2px 3px 2px 0; }
</style>
{% endblock %}

{% block content %}
<div class="wizard-outer">

  <div class="wizard-meta">
    <span id="wStepLabel">Question 1 of 7</span>
    <span id="wPctLabel">14%</span>
  </div>
  <div class="wizard-track">
    <div class="wizard-fill" id="wFill" style="width:14%"></div>
  </div>

  <form method="post" action="/my/questionnaire" id="wForm">
    <div class="wizard-stage" id="wStage">

      <!-- Card 0: Age -->
      <div class="wcard active" id="wc0">
        <div class="wcard-label">About you</div>
        <div class="wcard-title">How old are you?</div>
        <div class="slider-display" id="ageDisplay">
          {{ existing_age if existing_age else 28 }}&nbsp;<span class="slider-unit">years old</span>
        </div>
        <input type="range" class="wrange" name="age" id="ageRange"
               min="13" max="80" value="{{ existing_age if existing_age else 28 }}" />
        <div class="slider-limits"><span>13</span><span>80+</span></div>
        <div class="wnav">
          <button type="button" class="wnav-next" onclick="wNext()">Continue &#8594;</button>
        </div>
      </div>

      <!-- Card 1: Fitness level -->
      <div class="wcard" id="wc1">
        <div class="wcard-label">Experience</div>
        <div class="wcard-title">What is your fitness level?</div>
        <div class="wopts wopts--row">
          {% for level in fitness_levels %}
          <label class="wopt">
            <input type="radio" name="fitness_level" value="{{ level }}"
                   {% if existing_fitness_level == level %}checked{% endif %}>
            {{ level }}
          </label>
          {% endfor %}
        </div>
        <div class="wnav">
          <button type="button" class="wnav-back" onclick="wBack()">&#8592; Back</button>
          <button type="button" class="wnav-next" onclick="wNext()">Continue &#8594;</button>
        </div>
      </div>

      <!-- Card 2: Days per week -->
      <div class="wcard" id="wc2">
        <div class="wcard-label">Commitment</div>
        <div class="wcard-title">How many days per week do you work out?</div>
        <div class="slider-display" id="daysDisplay">
          {{ existing_weekly_days if existing_weekly_days else 3 }}&nbsp;<span class="slider-unit" id="daysUnit">{{ 'day / week' if existing_weekly_days == 1 else 'days / week' }}</span>
        </div>
        <input type="range" class="wrange" name="weekly_workout_days" id="daysRange"
               min="1" max="7" value="{{ existing_weekly_days if existing_weekly_days else 3 }}" />
        <div class="slider-limits"><span>1</span><span>7</span></div>
        <div class="wnav">
          <button type="button" class="wnav-back" onclick="wBack()">&#8592; Back</button>
          <button type="button" class="wnav-next" onclick="wNext()">Continue &#8594;</button>
        </div>
      </div>

      <!-- Card 3: Fitness goals -->
      <div class="wcard" id="wc3">
        <div class="wcard-label">Goals</div>
        <div class="wcard-title">What are your fitness goals?</div>
        <div class="wopts">
          {% for opt in goal_options %}
          <label class="wopt">
            <input type="checkbox" name="fitness_goals" value="{{ opt.value }}"
                   {% if opt.value in existing_goals %}checked{% endif %}>
            {{ opt.label }}
          </label>
          {% endfor %}
        </div>
        <div class="wnav">
          <button type="button" class="wnav-back" onclick="wBack()">&#8592; Back</button>
          <button type="button" class="wnav-next" onclick="wNext()">Continue &#8594;</button>
        </div>
      </div>

      <!-- Card 4: Equipment -->
      <div class="wcard" id="wc4">
        <div class="wcard-label">Equipment</div>
        <div class="wcard-title">What equipment do you have access to?</div>
        <div class="wtags">
          {% for eq in equipment_options %}
          <label class="wtag">
            <input type="checkbox" name="equipment" value="{{ eq.tag }}"
                   {% if eq.tag in existing_equipment %}checked{% endif %}>
            {{ eq.icon }} {{ eq.label }}
          </label>
          {% endfor %}
        </div>
        <div class="wnav">
          <button type="button" class="wnav-back" onclick="wBack()">&#8592; Back</button>
          <button type="button" class="wnav-next" onclick="wNext()">Continue &#8594;</button>
        </div>
      </div>

      <!-- Card 5: Diet -->
      <div class="wcard" id="wc5">
        <div class="wcard-label">Diet</div>
        <div class="wcard-title">Do you follow a specific diet?</div>
        <div class="wopts wopts--grid">
          {% for opt in diet_options %}
          <label class="wopt">
            <input type="checkbox" name="diet" value="{{ opt.value }}"
                   {% if opt.value in existing_diet %}checked{% endif %}>
            {{ opt.label }}
          </label>
          {% endfor %}
        </div>
        <div class="wnav">
          <button type="button" class="wnav-back" onclick="wBack()">&#8592; Back</button>
          <button type="button" class="wnav-next" onclick="wNext()">Continue &#8594;</button>
        </div>
      </div>

      <!-- Card 6: Health conditions -->
      <div class="wcard" id="wc6">
        <div class="wcard-label">Health</div>
        <div class="wcard-title">Any health or medical conditions we should know about?</div>
        <div class="wopts wopts--grid">
          {% for opt in health_options %}
          <label class="wopt">
            <input type="checkbox" name="health_conditions" value="{{ opt.value }}"
                   {% if opt.value in existing_health %}checked{% endif %}>
            {{ opt.label }}
          </label>
          {% endfor %}
        </div>
        <div class="wnav">
          <button type="button" class="wnav-back" onclick="wBack()">&#8592; Back</button>
          <button type="button" class="wnav-next" onclick="wNext()">Continue &#8594;</button>
        </div>
      </div>

      <!-- Card 7: Summary -->
      <div class="wcard" id="wc7">
        <div class="wcard-label">All done</div>
        <div class="wcard-title" style="font-size:16px">Here&#8217;s your profile &#8212; looks good?</div>
        <div id="wSummary"></div>
        <div class="wnav">
          <button type="button" class="wnav-back" onclick="wBack()">&#8592; Edit</button>
          <button type="submit" class="wnav-save" id="wSaveBtn">&#10003; Save Profile</button>
        </div>
      </div>

    </div>{# /wizard-stage #}
  </form>

  {% if not is_retake %}
  <div class="text-center mt-3">
    <form method="post" action="/my/questionnaire/skip" style="display:inline">
      <button type="submit" class="btn btn-link text-muted small p-0">Skip for now</button>
    </form>
  </div>
  {% else %}
  <div class="text-center mt-3">
    <a href="/my/profile" class="text-muted small">Cancel</a>
  </div>
  {% endif %}

  <div class="wdots" id="wDots"></div>

</div>{# /wizard-outer #}
{% endblock %}

{% block scripts %}
<script>
(function () {
  var TOTAL = 7;
  var cur = 0;

  /* ── Progress bar ── */
  function setProgress(step) {
    var pct = Math.round((step / TOTAL) * 100);
    document.getElementById('wFill').style.width = pct + '%';
    document.getElementById('wPctLabel').textContent = pct + '%';
    document.getElementById('wStepLabel').textContent =
      step < TOTAL ? 'Question ' + (step + 1) + ' of ' + TOTAL : 'Review';
  }

  /* ── Dot strip ── */
  function renderDots(step) {
    var wrap = document.getElementById('wDots');
    while (wrap.firstChild) wrap.removeChild(wrap.firstChild);
    for (var i = 0; i < TOTAL; i++) {
      var d = document.createElement('div');
      d.className = 'wdot' +
        (i === step ? ' wdot--active' : (i < step ? ' wdot--done' : ''));
      wrap.appendChild(d);
    }
  }

  /* ── Card transition (fade + scale) ── */
  function transition(next) {
    var outEl = document.getElementById('wc' + cur);
    var inEl  = document.getElementById('wc' + next);
    if (!outEl || !inEl) return;

    outEl.classList.remove('active');
    outEl.classList.add('exiting');

    cur = next;
    setProgress(cur);
    renderDots(cur);
    if (cur === TOTAL) buildSummary();

    /* Force the browser to see inEl's initial transform before transitioning */
    inEl.style.position = 'absolute';
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        inEl.style.position = '';
        inEl.classList.add('active');
      });
    });

    setTimeout(function () { outEl.classList.remove('exiting'); }, 380);
  }

  window.wNext = function () { if (cur < TOTAL) transition(cur + 1); };
  window.wBack = function () { if (cur > 0)     transition(cur - 1); };

  /* ── Age slider ── */
  document.getElementById('ageRange').addEventListener('input', function () {
    var d = document.getElementById('ageDisplay');
    while (d.firstChild) d.removeChild(d.firstChild);
    d.appendChild(document.createTextNode(this.value + '\u00a0'));
    var s = document.createElement('span');
    s.className = 'slider-unit';
    s.textContent = 'years old';
    d.appendChild(s);
  });

  /* ── Days slider ── */
  document.getElementById('daysRange').addEventListener('input', function () {
    var v = parseInt(this.value, 10);
    var d = document.getElementById('daysDisplay');
    while (d.firstChild) d.removeChild(d.firstChild);
    d.appendChild(document.createTextNode(v + '\u00a0'));
    var s = document.createElement('span');
    s.className = 'slider-unit';
    s.textContent = v === 1 ? 'day\u00a0/\u00a0week' : 'days\u00a0/\u00a0week';
    d.appendChild(s);
  });

  /* ── Summary builder (DOM-only, no innerHTML) ── */
  function getCheckedText(fieldName) {
    var inputs = document.querySelectorAll('input[name="' + fieldName + '"]:checked');
    var texts = [];
    for (var i = 0; i < inputs.length; i++) {
      texts.push(inputs[i].closest('label').textContent.trim());
    }
    return texts;
  }

  function getRadioText(fieldName) {
    var inp = document.querySelector('input[name="' + fieldName + '"]:checked');
    return inp ? [inp.closest('label').textContent.trim()] : [];
  }

  function makeBadge(text) {
    var s = document.createElement('span');
    s.className = 'wbadge';
    s.textContent = text;
    return s;
  }

  function makeRow(key, texts) {
    var row = document.createElement('div');
    row.className = 'wsum-row';
    var k = document.createElement('span');
    k.className = 'wsum-key';
    k.textContent = key;
    row.appendChild(k);
    var v = document.createElement('span');
    var items = texts.length ? texts : ['—'];
    items.forEach(function (t) { v.appendChild(makeBadge(t)); });
    row.appendChild(v);
    return row;
  }

  function buildSummary() {
    var wrap = document.getElementById('wSummary');
    while (wrap.firstChild) wrap.removeChild(wrap.firstChild);
    wrap.appendChild(makeRow('Age',
      [document.getElementById('ageRange').value + '\u00a0years old']));
    wrap.appendChild(makeRow('Level',      getRadioText('fitness_level')));
    wrap.appendChild(makeRow('Days\u00a0/\u00a0week',
      [document.getElementById('daysRange').value]));
    wrap.appendChild(makeRow('Goals',      getCheckedText('fitness_goals')));
    wrap.appendChild(makeRow('Equipment',  getCheckedText('equipment')));
    wrap.appendChild(makeRow('Diet',       getCheckedText('diet')));
    wrap.appendChild(makeRow('Health',     getCheckedText('health_conditions')));
  }

  /* ── Disable save on submit ── */
  document.getElementById('wForm').addEventListener('submit', function () {
    var btn = document.getElementById('wSaveBtn');
    btn.disabled = true;
    btn.textContent = 'Saving\u2026';
  });

  /* ── Init ── */
  setProgress(0);
  renderDots(0);
}());
</script>
{% endblock %}
```

- [ ] **Step 2: Run the regression tests — all must pass**

```
pytest tests/test_questionnaire.py -v
```

Expected: all 11 tests PASS. If any fail, the field name or class name in the template is wrong — fix until all pass.

- [ ] **Step 3: Run the full test suite — no regressions**

```
pytest --ignore=tests/test_editing_e2e.py -q
```

Expected: same pass count as before (45 passed, 1 skipped).

- [ ] **Step 4: Commit**

```bash
git add web/templates/questionnaire.html
git commit -m "feat: replace questionnaire with animated step wizard"
```

---

## Self-Review

**Spec coverage:**
- ✅ Step wizard with one question per screen
- ✅ Fade + scale transition (exit: scale .94 + translateY(-10px); enter: scale .94 + translateY(14px) → none)
- ✅ Progress bar + dot strip updating each step
- ✅ Age as range slider (13–80)
- ✅ Days/week as range slider (1–7)
- ✅ Fitness level as 3-option radio row
- ✅ Goals/diet/health as checkbox lists
- ✅ Equipment as tag cloud
- ✅ Summary screen with badge chips before submit
- ✅ Back/Continue on every step; "Edit ←" on summary
- ✅ Pre-population of existing answers on retake (Jinja2 `checked`/`value` attributes)
- ✅ Skip button posts to `/my/questionnaire/skip`
- ✅ No backend changes
- ✅ No new JS dependencies

**Placeholder scan:** None found.

**Type consistency:** All JS function names (`wNext`, `wBack`, `buildSummary`, `transition`, `makeRow`, `makeBadge`, `getCheckedText`, `getRadioText`) are defined before use. All DOM IDs (`wc0`–`wc7`, `ageRange`, `daysRange`, `ageDisplay`, `daysDisplay`, `wFill`, `wPctLabel`, `wStepLabel`, `wDots`, `wSummary`, `wSaveBtn`, `wForm`) appear in the template exactly once.
