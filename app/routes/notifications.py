"""
Notification routes
  POST /notifications/register-token    — store FCM token for a user
  GET  /notifications/preferences       — get user notification prefs
  POST /notifications/preferences       — set user notification prefs
  POST /notifications/ack               — mark slot resolved (no log written)
  POST /notifications/quick-log         — log data from notification action
  POST /notifications/send-test         — manually fire a test notification
  GET  /notifications/status            — view today's notification states
  POST /notifications/seed              — manually trigger seed_daily_states
  POST /notifications/cycle             — manually trigger run_notification_cycle
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.db.mongo import get_client, get_daily_logs_collection, get_users_collection
from app.db.notification_state import (
    get_user_states_for_date,
    mark_resolved,
    update_scheduled_utc,
    upsert_state,
)
from app.scheduler.notification_scheduler import run_notification_cycle, seed_daily_states
from app.services.fcm_service import send_data_message
from app.services.notification_templates import (
    ML_ACTION_MAP,
    SNOOZE_MINUTES,
    get_template,
)
from app.core.config import settings

router = APIRouter(tags=["Notifications"])

DB_NAME = settings.MONGO_DB_NAME


# ─────────────────────────────────────────────────────────────────────────────
# Request / response models
# ─────────────────────────────────────────────────────────────────────────────

class RegisterTokenRequest(BaseModel):
    uid: str
    fcm_token: str


class NotificationPrefsRequest(BaseModel):
    uid: str
    enabled: bool = True
    timezone: str = "UTC"
    wake_time: str = "07:00"
    breakfast_time: str = "08:00"
    lunch_time: str = "13:00"
    dinner_time: str = "19:30"
    bedtime_time: str = "22:30"
    hydration_interval_hours: float = 3.0
    custom_slots: list[dict] = []


class AckRequest(BaseModel):
    uid: str
    slot_label: str
    date: Optional[str] = None


class QuickLogRequest(BaseModel):
    uid: str
    notification_type: str   # wake|breakfast|lunch|dinner|hydration|bedtime|custom
    slot_label: str
    action: str              # ml_250|ml_500|ml_750|i_am_awake|light_meal|full_meal|skipped|log_now|logged|skip|snooze_15|snooze_30
    value: Optional[str] = None   # free-form, not currently used
    date: Optional[str] = None


class SendTestRequest(BaseModel):
    uid: str
    notification_type: str = "hydration"


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_hhmm() -> str:
    return datetime.now().strftime("%H:%M")


async def _get_user(uid: str) -> dict:
    client = get_client()
    db = client[DB_NAME]
    user = await db["users"].find_one({"firebase_uid": uid}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{uid}' not found")
    return user


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/register-token", summary="Register or refresh FCM device token")
async def register_token(body: RegisterTokenRequest):
    """
    Called on every app open from Flutter.
    Stores the latest FCM token so the scheduler can send pushes.
    """
    client = get_client()
    db = client[DB_NAME]
    result = await db["users"].update_one(
        {"firebase_uid": body.uid},
        {"$set": {"fcm_token": body.fcm_token}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found. Create profile first.")
    return {"status": "ok", "message": "FCM token registered"}


@router.get("/preferences", summary="Get notification preferences")
async def get_preferences(uid: str = Query(...)):
    user = await _get_user(uid)
    default_prefs = {
        "enabled": False,
        "timezone": "Asia/Kolkata",
        "wake_time": "07:00",
        "breakfast_time": "08:00",
        "lunch_time": "13:00",
        "dinner_time": "19:30",
        "bedtime_time": "22:30",
        "hydration_interval_hours": 3,
        "custom_slots": [],
    }
    prefs = {**default_prefs, **(user.get("notification_prefs") or {})}
    return {"uid": uid, "preferences": prefs}


@router.post("/preferences", summary="Save notification preferences")
async def save_preferences(body: NotificationPrefsRequest):
    client = get_client()
    db = client[DB_NAME]
    prefs = body.model_dump(exclude={"uid"})
    result = await db["users"].update_one(
        {"firebase_uid": body.uid},
        {"$set": {"notification_prefs": prefs}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found.")

    # Auto-seed today's states when preferences are saved
    today = _today()
    user = await _get_user(body.uid)
    from app.scheduler.notification_scheduler import _build_schedule
    slots = _build_schedule(user, today)
    for slot in slots:
        await upsert_state(
            firebase_uid=body.uid,
            date=today,
            slot_label=slot["slot_label"],
            notification_type=slot["notification_type"],
            scheduled_utc=slot["scheduled_utc"],
            status="pending",
        )

    return {
        "status": "ok",
        "message": f"Preferences saved. {len(slots)} notification slots seeded for today.",
        "slots_seeded": len(slots),
    }


@router.post("/ack", summary="Acknowledge (dismiss) a notification without logging")
async def acknowledge(body: AckRequest):
    """
    Marks a slot as resolved without writing any health log.
    Used when the user has already logged manually and dismisses the reminder.
    """
    date = body.date or _today()
    await mark_resolved(
        firebase_uid=body.uid,
        date=date,
        slot_label=body.slot_label,
        action_taken="dismissed",
    )
    return {"status": "ok", "message": "Notification acknowledged"}


@router.post("/quick-log", summary="Log health data directly from a notification action")
async def quick_log(body: QuickLogRequest):
    """
    The core quick-log endpoint.

    Called by the Flutter background isolate when the user taps
    a notification action button (no app open needed).

    Supported actions per notification_type:
      hydration  → ml_250 / ml_500 / ml_750  : appends hydration entry
      wake       → i_am_awake                : sets sleep.wake_time = now
      breakfast / lunch / dinner → light_meal / full_meal / skipped
      bedtime    → log_now                   : sets sleep.bed_time = now
      any        → snooze_15 / snooze_30     : reschedules the slot
      any        → skip                      : marks resolved, no log
    """
    date = body.date or _today()
    action = body.action

    # ── Snooze ──────────────────────────────────────────────────────────────
    if action in SNOOZE_MINUTES:
        new_time = datetime.now(timezone.utc) + timedelta(minutes=SNOOZE_MINUTES[action])
        await update_scheduled_utc(
            firebase_uid=body.uid,
            date=date,
            slot_label=body.slot_label,
            new_scheduled_utc=new_time,
            new_status="pending",
        )
        return {"status": "snoozed", "resend_in_minutes": SNOOZE_MINUTES[action]}

    # ── Skip ────────────────────────────────────────────────────────────────
    if action == "skip":
        await mark_resolved(body.uid, date, body.slot_label, "skipped")
        return {"status": "ok", "message": "Skipped"}

    # ── Hydration ────────────────────────────────────────────────────────────
    if body.notification_type == "hydration" and action in ML_ACTION_MAP:
        ml = ML_ACTION_MAP[action]
        logs_col = await get_daily_logs_collection()
        now_hhmm = _now_hhmm()

        await logs_col.update_one(
            {"firebase_uid": body.uid, "date": date},
            {
                "$push": {
                    "hydration.entries": {"time": now_hhmm, "ml": ml, "source": "notification"}
                },
                "$inc": {"hydration.total_ml": ml},
                "$setOnInsert": {"firebase_uid": body.uid, "date": date},
            },
            upsert=True,
        )
        await mark_resolved(body.uid, date, body.slot_label, action)
        return {"status": "ok", "message": f"💧 {ml} ml logged", "ml_added": ml}

    # ── Wake time ────────────────────────────────────────────────────────────
    if body.notification_type == "wake" and action == "i_am_awake":
        logs_col = await get_daily_logs_collection()
        now_hhmm = _now_hhmm()
        await logs_col.update_one(
            {"firebase_uid": body.uid, "date": date},
            {
                "$set": {"sleep.wake_time": now_hhmm},
                "$setOnInsert": {"firebase_uid": body.uid, "date": date},
            },
            upsert=True,
        )
        await mark_resolved(body.uid, date, body.slot_label, action)
        return {"status": "ok", "message": f"☀️ Wake time {now_hhmm} logged"}

    # ── Bedtime ──────────────────────────────────────────────────────────────
    if body.notification_type == "bedtime" and action == "log_now":
        logs_col = await get_daily_logs_collection()
        now_hhmm = _now_hhmm()
        await logs_col.update_one(
            {"firebase_uid": body.uid, "date": date},
            {
                "$set": {"sleep.bed_time": now_hhmm},
                "$setOnInsert": {"firebase_uid": body.uid, "date": date},
            },
            upsert=True,
        )
        await mark_resolved(body.uid, date, body.slot_label, action)
        return {"status": "ok", "message": f"🌙 Bed time {now_hhmm} logged"}

    # ── Meals ────────────────────────────────────────────────────────────────
    if body.notification_type in ("breakfast", "lunch", "dinner"):
        if action in ("light_meal", "full_meal", "skipped"):
            logs_col = await get_daily_logs_collection()
            await logs_col.update_one(
                {"firebase_uid": body.uid, "date": date},
                {
                    "$set": {
                        f"nutrition.meal_flags.{body.notification_type}": action
                    },
                    "$setOnInsert": {"firebase_uid": body.uid, "date": date},
                },
                upsert=True,
            )
            await mark_resolved(body.uid, date, body.slot_label, action)
            return {
                "status": "ok",
                "message": f"🍽️ {body.notification_type.capitalize()} marked as {action}",
            }

    # ── Generic logged ───────────────────────────────────────────────────────
    if action == "logged":
        await mark_resolved(body.uid, date, body.slot_label, "logged")
        return {"status": "ok", "message": "✅ Logged"}

    raise HTTPException(
        status_code=400,
        detail=f"Unrecognised action '{action}' for type '{body.notification_type}'",
    )


@router.post("/send-test", summary="Send a test FCM notification to a user")
async def send_test(body: SendTestRequest):
    """Manually fire a test notification. Useful for Streamlit debugging."""
    user = await _get_user(body.uid)
    token = user.get("fcm_token")
    if not token:
        raise HTTPException(
            status_code=400,
            detail="No FCM token registered for this user. Call /register-token first.",
        )

    template = get_template(body.notification_type)
    today = _today()
    slot_label = f"test_{body.notification_type}"
    data = template.to_fcm_data(
        uid=body.uid,
        slot_label=slot_label,
        date=today,
        is_reminder=False,
        reminder_count=0,
    )
    result = send_data_message(token, data)
    if result.success:
        return {"status": "sent", "message_id": result.message_id}
    raise HTTPException(status_code=502, detail=f"FCM error: {result.error}")


@router.get("/status", summary="View today's notification states for a user")
async def get_status(uid: str = Query(...), date: Optional[str] = Query(None)):
    date = date or _today()
    states = await get_user_states_for_date(uid, date)
    # Convert datetime objects to ISO strings for JSON
    serialised = []
    for s in states:
        row = {}
        for k, v in s.items():
            row[k] = v.isoformat() if isinstance(v, datetime) else v
        serialised.append(row)
    return {"uid": uid, "date": date, "states": serialised, "count": len(serialised)}


@router.post("/seed", summary="Manually seed today's notification states for all users")
async def seed_states(date: Optional[str] = Query(None)):
    count = await seed_daily_states(date)
    return {"status": "ok", "slots_seeded": count}


@router.post("/cycle", summary="Manually trigger the notification cycle (for testing)")
async def trigger_cycle():
    stats = await run_notification_cycle()
    return {"status": "ok", "cycle_stats": stats}
