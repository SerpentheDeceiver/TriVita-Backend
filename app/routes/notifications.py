# Notification routes for management and operations.

from __future__ import annotations

import asyncio
import logging
import traceback
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
    HYDRATION_ML_PER_SLOT,
    NUTRITION_MEAL_TYPES,
    SNOOZE_MINUTES,
    get_template,
)
from app.core.config import settings

router = APIRouter(tags=["Notifications"])

DB_NAME = settings.MONGO_DB_NAME

logger = logging.getLogger(__name__)


# Models

class RegisterTokenRequest(BaseModel):
    uid: str
    fcm_token: str


class NotificationPrefsRequest(BaseModel):
    uid: str
    timezone: str = "Asia/Kolkata"
    
    # Master Toggles
    global_enabled:      bool = True
    sleep_enabled:       bool = True
    hydration_enabled:   bool = True
    nutrition_enabled:   bool = True
    dark_mode:           bool = False

    # Individual Toggles
    wake_enabled:           bool = True
    bedtime_enabled:        bool = True
    breakfast_enabled:       bool = True
    mid_morning_enabled:      bool = True
    lunch_enabled:           bool = True
    afternoon_break_enabled:  bool = True
    dinner_enabled:          bool = True
    post_dinner_enabled:      bool = True
    hydration_1_enabled:      bool = True
    hydration_2_enabled:      bool = True
    hydration_3_enabled:      bool = True
    hydration_4_enabled:      bool = True
    hydration_5_enabled:      bool = True
    hydration_6_enabled:      bool = True
    hydration_7_enabled:      bool = True
    hydration_8_enabled:      bool = True

    # Sleep (2)
    wake_time:            str = "07:00"
    bedtime_time:         str = "22:30"
    # Nutrition (6)
    breakfast_time:       str = "08:00"
    mid_morning_time:     str = "10:30"
    lunch_time:           str = "13:00"
    afternoon_break_time: str = "16:00"
    dinner_time:          str = "19:30"
    post_dinner_time:     str = "21:00"
    # Hydration (8)
    hydration_1_time:     str = "08:45"
    hydration_2_time:     str = "10:30"
    hydration_3_time:     str = "12:15"
    hydration_4_time:     str = "14:00"
    hydration_5_time:     str = "15:45"
    hydration_6_time:     str = "17:30"
    hydration_7_time:     str = "19:15"
    hydration_8_time:     str = "21:00"


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


# Helpers

def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_hhmm(tz_name: str = "Asia/Kolkata") -> str:
    """Return current time as HH:MM in the user's local timezone (default IST)."""
    import pytz
    tz = pytz.timezone(tz_name)
    return datetime.now(tz).strftime("%H:%M")


async def _get_user(uid: str) -> dict:
    client = get_client()
    db = client[DB_NAME]
    user = await db["users"].find_one({"firebase_uid": uid}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{uid}' not found")
    return user


# Endpoints

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
        "timezone":            "Asia/Kolkata",
        "global_enabled":      True,
        "sleep_enabled":       True,
        "hydration_enabled":   True,
        "nutrition_enabled":   True,
        "dark_mode":           False,
        "wake_enabled":           True,
        "bedtime_enabled":        True,
        "breakfast_enabled":       True,
        "mid_morning_enabled":      True,
        "lunch_enabled":           True,
        "afternoon_break_enabled":  True,
        "dinner_enabled":          True,
        "post_dinner_enabled":      True,
        "hydration_1_enabled":      True,
        "hydration_2_enabled":      True,
        "hydration_3_enabled":      True,
        "hydration_4_enabled":      True,
        "hydration_5_enabled":      True,
        "hydration_6_enabled":      True,
        "hydration_7_enabled":      True,
        "hydration_8_enabled":      True,
        "wake_time":            "07:00",
        "bedtime_time":         "22:30",
        "breakfast_time":       "08:00",
        "mid_morning_time":     "10:30",
        "lunch_time":           "13:00",
        "afternoon_break_time": "16:00",
        "dinner_time":          "19:30",
        "post_dinner_time":     "21:00",
        "hydration_1_time":     "08:45",
        "hydration_2_time":     "10:30",
        "hydration_3_time":     "12:15",
        "hydration_4_time":     "14:00",
        "hydration_5_time":     "15:45",
        "hydration_6_time":     "17:30",
        "hydration_7_time":     "19:15",
        "hydration_8_time":     "21:00",
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

    # Seed today's slots immediately when preferences are saved.
    # We use skip_past=True so that if the user saves their schedule at 11:00 AM,
    # slots like "Breakfast" at 8:00 AM are NOT seeded and won't fire immediately.
    today = _today()
    user  = await _get_user(body.uid)
    from app.scheduler.notification_scheduler import _build_schedule
    slots = _build_schedule(user, today, skip_past=True)
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
        "status":       "ok",
        "message":      f"Preferences saved. {len(slots)} upcoming slots seeded for today.",
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
    Unified 3-action quick-log endpoint.

    Actions for every notification type:
      yes          → immediately log to daily_logs and mark resolved
      need_15_min  → reschedule slot +15 min, status reset to pending
      need_30_min  → reschedule slot +30 min, status reset to pending

    Logging behaviour per type:
      wake            → sleep.wake_time = now
      bedtime         → sleep.bed_time  = now
      hydration_*     → hydration entry +250 ml
      breakfast / mid_morning / lunch / afternoon_break /
      dinner / post_dinner  → nutrition entry for that meal type
    """
    logger.info(
        "[QUICK-LOG] uid=%s type=%s slot=%s action=%s",
        body.uid, body.notification_type, body.slot_label, body.action
    )

    date   = body.date or _today()
    action = body.action

    # ── Snooze ──────────────────────────────────────────────────────────────
    if action in SNOOZE_MINUTES:
        snooze_mins = SNOOZE_MINUTES[action]
        new_time = datetime.now(timezone.utc) + timedelta(minutes=snooze_mins)
        print(f"[QUICK-LOG] ⏱ Snoozing {snooze_mins} min → new_utc={new_time.isoformat()}")
        try:
            await update_scheduled_utc(
                firebase_uid=body.uid,
                date=date,
                slot_label=body.slot_label,
                new_scheduled_utc=new_time,
                new_status="pending",
            )
            print(f"[QUICK-LOG] ✅ Snooze saved for slot={body.slot_label}")
        except Exception as exc:
            print(f"[QUICK-LOG] ❌ Snooze update_scheduled_utc error: {exc}")
            logger.error("[QUICK-LOG] Snooze error: %s\n%s", exc, traceback.format_exc())
            raise
        return {"status": "snoozed", "resend_in_minutes": snooze_mins}

    # ── Yes — log and resolve ────────────────────────────────────────────────
    if action != "yes":
        print(f"[QUICK-LOG] ❌ Unknown action={action!r}")
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action '{action}'. Expected 'yes', 'need_15_min', or 'need_30_min'.",
        )

    try:
        user = await _get_user(body.uid)
        prefs = user.get("notification_prefs") or {}
        user_tz = prefs.get("timezone", "Asia/Kolkata")

        logs_col = await get_daily_logs_collection()
        now_hhmm = _now_hhmm(user_tz)
        now_utc_iso = datetime.now(timezone.utc).isoformat()
        print(f"[QUICK-LOG] 🕐 now_hhmm={now_hhmm} (tz={user_tz})  date={date}  uid={body.uid}")

        # ── Wake ────────────────────────────────────────────────────────────
        if body.notification_type == "wake":
            print(f"[QUICK-LOG] ☀️ Writing wake_time={now_hhmm} to daily_logs")
            result = await logs_col.update_one(
                {"firebase_uid": body.uid, "date": date},
                {
                    "$set": {
                        "sleep.wake_time":  now_hhmm,
                        "sleep.source":     "notification",
                        "sleep.entry_mode": "notification",
                        "sleep.logged_at":  now_utc_iso,
                    },
                    "$setOnInsert": {"firebase_uid": body.uid, "date": date},
                },
                upsert=True,
            )
            print(
                f"[QUICK-LOG] ☀️ wake update result — "
                f"matched={result.matched_count}  modified={result.modified_count}  "
                f"upserted_id={result.upserted_id}"
            )
            await mark_resolved(body.uid, date, body.slot_label, "yes")
            return {"status": "ok", "message": f"☀️ Wake time {now_hhmm} logged"}

        # ── Bedtime ──────────────────────────────────────────────────────────
        if body.notification_type == "bedtime":
            print(f"[QUICK-LOG] 🌙 Writing bed_time={now_hhmm} to daily_logs")
            result = await logs_col.update_one(
                {"firebase_uid": body.uid, "date": date},
                {
                    "$set": {
                        "sleep.bed_time":   now_hhmm,
                        "sleep.source":     "notification",
                        "sleep.entry_mode": "notification",
                        "sleep.logged_at":  now_utc_iso,
                    },
                    "$setOnInsert": {"firebase_uid": body.uid, "date": date},
                },
                upsert=True,
            )
            print(
                f"[QUICK-LOG] 🌙 bedtime update result — "
                f"matched={result.matched_count}  modified={result.modified_count}  "
                f"upserted_id={result.upserted_id}"
            )
            await mark_resolved(body.uid, date, body.slot_label, "yes")
            return {"status": "ok", "message": f"🌙 Bedtime {now_hhmm} logged"}

        # ── Hydration — 250 ml per slot ──────────────────────────────────────
        if body.notification_type == "hydration":
            ml = HYDRATION_ML_PER_SLOT
            print(f"[QUICK-LOG] 💧 Writing hydration {ml} ml  slot={body.slot_label}")
            result = await logs_col.update_one(
                {"firebase_uid": body.uid, "date": date},
                {
                    "$push": {
                        "hydration.entries": {
                            "amount_ml":       ml,
                            "logged_time":     now_hhmm,
                            "estimated_time":  now_hhmm,
                            "source":          "notification",
                        }
                    },
                    "$inc":         {"hydration.total_ml": ml},
                    "$set":         {"updated_at": datetime.now(timezone.utc)},
                    "$setOnInsert": {"firebase_uid": body.uid, "date": date},
                },
                upsert=True,
            )
            print(
                f"[QUICK-LOG] 💧 hydration update result — "
                f"matched={result.matched_count}  modified={result.modified_count}  "
                f"upserted_id={result.upserted_id}"
            )
            await mark_resolved(body.uid, date, body.slot_label, "yes")
            return {"status": "ok", "message": f"💧 {ml} ml logged", "ml_added": ml}

        # ── Nutrition — all 6 meal types ─────────────────────────────────────
        if body.notification_type in NUTRITION_MEAL_TYPES:
            meal_type = body.notification_type
            print(f"[QUICK-LOG] 🍽️ Writing nutrition meal_type={meal_type}")
            result = await logs_col.update_one(
                {"firebase_uid": body.uid, "date": date},
                {
                    "$push": {
                        "nutrition.entries": {
                            "meal_type":      meal_type,
                            "logged_time":    now_hhmm,
                            "estimated_time": now_hhmm,
                            "source":         "notification",
                            "items":          [],
                        }
                    },
                    "$set":         {"updated_at": datetime.now(timezone.utc)},
                    "$setOnInsert": {"firebase_uid": body.uid, "date": date},
                },
                upsert=True,
            )
            print(
                f"[QUICK-LOG] 🍽️ nutrition update result — "
                f"matched={result.matched_count}  modified={result.modified_count}  "
                f"upserted_id={result.upserted_id}"
            )
            await mark_resolved(body.uid, date, body.slot_label, "yes")
            msg = f"🍽️ {meal_type.replace('_', ' ').title()} logged at {now_hhmm}"
            print(f"[QUICK-LOG] ✅ {msg}")
            return {"status": "ok", "message": msg}

        print(f"[QUICK-LOG] ❌ Unrecognised notification_type={body.notification_type!r}")
        raise HTTPException(
            status_code=400,
            detail=f"Unrecognised notification_type '{body.notification_type}'",
        )

    except HTTPException:
        raise
    except Exception as exc:
        tb = traceback.format_exc()
        print(f"[QUICK-LOG] ❌ EXCEPTION: {exc}\n{tb}")
        logger.error("[QUICK-LOG] Unhandled exception: %s\n%s", exc, tb)
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}")


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
    # Convert datetime objects to ISO strings for JSON.
    # Motor returns timezone-naive datetimes from MongoDB (UTC stored values).
    # We must tag them as UTC (+00:00) before serialising so that Flutter's
    # DateTime.parse(...).toLocal() correctly converts them to device local time.
    serialised = []
    for s in states:
        row = {}
        for k, v in s.items():
            if isinstance(v, datetime):
                # Ensure UTC tzinfo is attached before calling isoformat()
                if v.tzinfo is None:
                    v = v.replace(tzinfo=timezone.utc)
                row[k] = v.isoformat()   # e.g. "2026-02-21T04:17:00+00:00"
            else:
                row[k] = v
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
