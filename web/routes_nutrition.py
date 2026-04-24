"""
Nutrition routes for GarminForge:
  POST /nutrition/profile        — save questionnaire answers, trigger plan generation
  GET  /nutrition                — 3-tab nutrition page
  POST /nutrition/regenerate     — delete current week plan, trigger fresh generation
  GET  /push/vapid-public-key    — serve VAPID public key for Web Push
  POST /push/subscribe           — save push subscription JSON
  GET  /notifications/unread-count — unread notification count
  GET  /notifications/recent     — last 10 notifications as JSON
  POST /notifications/{notif_id}/read  — mark notification as read
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from web.auth_utils import require_user
from web.db import get_db
from web.models import MealSuggestion, Notification, NutritionPlan, User
from web.nutrition_generator import generate_weekly_plan, last_sunday
from web.rendering import render_template

logger = logging.getLogger(__name__)
router = APIRouter()


class NutritionProfileBody(BaseModel):
    meals_per_day: int
    cooking_time: str
    calorie_mode: str
    allergies: list[str]
    avoid: list[str]
    cant_resist: list[str]


class PushSubscriptionBody(BaseModel):
    subscription: dict[str, Any]


class SuggestMealBody(BaseModel):
    description: str


class ConfirmSuggestionBody(BaseModel):
    meal_json: dict[str, Any]


def _send_pending_push(user: User, db: Session) -> None:
    """Fire unsent push notifications due today or earlier."""
    if not user.push_subscription_json:
        return
    vapid_private = os.environ.get("VAPID_PRIVATE_KEY", "")
    if not vapid_private:
        return
    try:
        from pywebpush import WebPushException, webpush  # type: ignore[import-untyped]

        vapid_email = os.environ.get("VAPID_CLAIM_EMAIL", "mailto:admin@garminforge.com")
        now = datetime.utcnow()
        pending = (
            db.query(Notification)
            .filter(
                Notification.user_id == user.id,
                Notification.scheduled_for <= now,
                Notification.sent_at.is_(None),
                Notification.channel.in_(["push", "both"]),
            )
            .all()
        )
        subscription = json.loads(user.push_subscription_json)
        for notif in pending:
            payload = json.dumps({"title": notif.title_key, "body": notif.body})
            try:
                webpush(
                    subscription_info=subscription,
                    data=payload,
                    vapid_private_key=vapid_private,
                    vapid_claims={"sub": vapid_email},
                )
                notif.sent_at = datetime.utcnow()
            except WebPushException as exc:
                logger.warning("Push failed for notif %s: %s", notif.id, exc)
        db.commit()
    except Exception as exc:
        logger.error("_send_pending_push error: %s", exc)


@router.post("/nutrition/profile")
async def save_nutrition_profile(
    body: NutritionProfileBody,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user = require_user(request, db)
    if user is None:
        raise HTTPException(status_code=401)
    user.nutrition_profile_json = json.dumps({
        "meals_per_day": body.meals_per_day,
        "cooking_time": body.cooking_time,
        "calorie_mode": body.calorie_mode,
        "allergies": body.allergies,
        "avoid": body.avoid,
        "cant_resist": body.cant_resist,
    })
    db.commit()
    background_tasks.add_task(generate_weekly_plan, user, db)
    return JSONResponse({"status": "ok"})


@router.get("/nutrition", response_class=HTMLResponse)
async def nutrition_page(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    user = require_user(request, db)
    if user is None:
        return RedirectResponse("/auth/login-forge", status_code=303)  # type: ignore[return-value]

    if not user.nutrition_profile_json:
        return RedirectResponse("/", status_code=303)  # type: ignore[return-value]

    week_start = last_sunday(date.today())
    plan = db.query(NutritionPlan).filter_by(user_id=user.id, week_start=week_start).first()
    if plan is None:
        plan = NutritionPlan(user_id=user.id, week_start=week_start, status="generating")
        db.add(plan)
        db.commit()
        db.refresh(plan)
        background_tasks.add_task(generate_weekly_plan, user, db)

    plan_data: dict[str, Any] = {}
    if plan.status == "ready" and plan.plan_json:
        plan_data = json.loads(plan.plan_json)

    # Pass saved profile to template so the wizard can pre-fill current values
    nutrition_profile: dict[str, Any] | None = None
    if user.nutrition_profile_json:
        nutrition_profile = json.loads(user.nutrition_profile_json)

    unread_count = (
        db.query(Notification)
        .filter_by(user_id=user.id)
        .filter(Notification.read_at.is_(None))
        .count()
    )

    return render_template(
        "nutrition.html", request, db=db,
        active_page="nutrition",
        plan=plan,
        plan_data=plan_data,
        today_str=str(date.today()),
        unread_count=unread_count,
        nutrition_profile=nutrition_profile,
    )


@router.api_route("/nutrition/regenerate", methods=["GET", "POST"])
async def regenerate_plan(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    user = require_user(request, db)
    if user is None:
        return RedirectResponse("/auth/login-forge", status_code=303)
    week_start = last_sunday(date.today())
    db.query(NutritionPlan).filter_by(user_id=user.id, week_start=week_start).delete()
    db.commit()
    background_tasks.add_task(generate_weekly_plan, user, db)
    return RedirectResponse("/nutrition", status_code=303)


@router.get("/push/vapid-public-key")
async def vapid_public_key() -> JSONResponse:
    return JSONResponse({"publicKey": os.environ.get("VAPID_PUBLIC_KEY", "")})


@router.post("/push/subscribe")
async def push_subscribe(
    body: PushSubscriptionBody,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user = require_user(request, db)
    if user is None:
        raise HTTPException(status_code=401)
    user.push_subscription_json = json.dumps(body.subscription)
    db.commit()
    return JSONResponse({"status": "ok"})


@router.get("/notifications/unread-count")
async def unread_count(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    user = require_user(request, db)
    if user is None:
        return JSONResponse({"count": 0})
    count = (
        db.query(Notification)
        .filter_by(user_id=user.id)
        .filter(Notification.read_at.is_(None))
        .count()
    )
    return JSONResponse({"count": count})


@router.get("/notifications/recent")
async def recent_notifications(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    user = require_user(request, db)
    if user is None:
        return JSONResponse([])
    notifs = (
        db.query(Notification)
        .filter_by(user_id=user.id)
        .order_by(Notification.scheduled_for.desc())
        .limit(10)
        .all()
    )
    return JSONResponse([
        {
            "id": n.id,
            "body": n.body,
            "scheduled_for": n.scheduled_for.isoformat(),
            "read": n.read_at is not None,
        }
        for n in notifs
    ])


@router.post("/notifications/{notif_id}/read")
async def mark_read(
    notif_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user = require_user(request, db)
    if user is None:
        raise HTTPException(status_code=401)
    notif = db.query(Notification).filter_by(id=notif_id, user_id=user.id).first()
    if not notif:
        raise HTTPException(status_code=404)
    notif.read_at = datetime.utcnow()
    db.commit()
    return JSONResponse({"status": "ok"})


_ENRICH_PROMPT = """\
Given this meal description, return a single JSON object with exactly these fields:
name_en, name_he, type (breakfast|lunch|dinner|snack),
kcal (integer), macros ({{protein_g, carbs_g, fat_g}} integers),
cooking_time (quick|medium|elaborate),
positive_tags (array, subset of: kosher/vegetarian/vegan/keto/gluten-free/dairy-free),
ingredient_flags (array, subset of: contains_meat/contains_dairy/contains_pork/\
contains_shellfish/contains_gluten/contains_eggs/contains_nuts/contains_soy/contains_fish),
ingredients (array of {{item_en, item_he, qty, category}}),
prep_note_en (string or null), prep_note_he (string or null).

No explanation. Raw JSON only.
Meal description: "{user_input}" """


@router.post("/nutrition/suggest")
async def suggest_meal(
    body: SuggestMealBody,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Enrich a natural-language meal description via Claude and return structured JSON."""
    user = require_user(request, db)
    if user is None:
        raise HTTPException(status_code=401)
    if not body.description.strip():
        raise HTTPException(status_code=400, detail="description is required")

    from web.ai_provider import get_ai_provider

    prompt = _ENRICH_PROMPT.format(user_input=body.description.replace('"', "'"))
    try:
        raw = get_ai_provider().complete(prompt)
        meal_data = json.loads(raw)
    except Exception as exc:
        logger.error("Meal enrichment failed: %s", exc)
        raise HTTPException(status_code=502, detail="AI enrichment failed")

    # Assign a temporary ID (will be replaced at graduation)
    import uuid as _uuid_mod

    meal_data["id"] = f"suggestion_{_uuid_mod.uuid4().hex[:8]}"
    meal_data["type"] = meal_data.get("type", "dinner")

    return JSONResponse(meal_data)


@router.post("/nutrition/suggest/confirm")
async def confirm_suggestion(
    body: ConfirmSuggestionBody,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Save a confirmed meal suggestion as a pending MealSuggestion row."""
    user = require_user(request, db)
    if user is None:
        raise HTTPException(status_code=401)

    suggestion = MealSuggestion(
        user_id=user.id,
        status="pending",
        meal_json=json.dumps(body.meal_json),
    )
    db.add(suggestion)
    db.commit()
    return JSONResponse({"status": "ok", "id": suggestion.id})
