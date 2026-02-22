# Notification Scheduler Engine.
# Processes daily notification seeding and 5-minute send/reminder cycles.

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import Optional

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.db.mongo import get_client
from app.db.notification_state import (
    get_all_pending_states,
    upsert_state,
    update_scheduled_utc,
)
from app.services.fcm_service import send_data_message
from app.services.notification_templates import get_template, SNOOZE_MINUTES

logger = logging.getLogger(__name__)

DB_NAME = settings.MONGO_DB_NAME


# Default notification preferences

DEFAULT_PREFS = {
    "timezone": "Asia/Kolkata",
    "global_enabled":      True,
    "sleep_enabled":       True,
    "hydration_enabled":   True,
    "nutrition_enabled":   True,
    # Sleep
    "wake_time":            "07:00",
    "bedtime_time":         "22:30",
    # Nutrition
    "breakfast_time":       "08:00",
    "mid_morning_time":     "10:30",
    "lunch_time":           "13:00",
    "afternoon_break_time": "16:00",
    "dinner_time":          "19:30",
    "post_dinner_time":     "21:00",
    # Hydration — equal spread between wake (07:00) and bedtime (22:30)
    "hydration_1_time":     "08:45",
    "hydration_2_time":     "10:30",
    "hydration_3_time":     "12:15",
    "hydration_4_time":     "14:00",
    "hydration_5_time":     "15:45",
    "hydration_6_time":     "17:30",
    "hydration_7_time":     "19:15",
    "hydration_8_time":     "21:00",
}


# Helpers

def _parse_local_time(time_str: str, date_str: str, tz_name: str) -> datetime:
    """
    Convert a "HH:MM" string + date "YYYY-MM-DD" in the given timezone
    to a UTC-aware datetime.
    """
    try:
        tz = pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        tz = pytz.utc

    local_dt = tz.localize(
        datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    )
    return local_dt.astimezone(pytz.utc)


def _build_schedule(user_doc: dict, date_str: str, skip_past: bool = True) -> list[dict]:
    """
    Build today's notification schedule for a user.

    Always enabled — 16 fixed slots:
      Sleep (2):     wake, bedtime
      Nutrition (6): breakfast, mid_morning, lunch, afternoon_break,
                     dinner, post_dinner
      Hydration (8): hydration_1 … hydration_8 (250 ml each)

    When skip_past=True (default, used by midnight seed), slots whose
    scheduled_utc is already in the past are skipped to avoid a burst of
    stale notifications.

    When skip_past=False (used by save_preferences), ALL 16 slots are
    returned so that editing a past-due time still updates the stored
    scheduled_utc in MongoDB.

    Returns list of {slot_label, notification_type, scheduled_utc}.
    """
    prefs = {**DEFAULT_PREFS, **(user_doc.get("notification_prefs") or {})}
    
    # Global Killswitch
    if not prefs.get("global_enabled", True):
        logger.info("Global notifications disabled for uid=%s", user_doc.get("firebase_uid"))
        return []

    tz_name = prefs.get("timezone", "Asia/Kolkata")
    now_utc = datetime.now(timezone.utc)

    slots = []

    # ── Sleep (2) ─────────────────────────────────────────────────────────
    if prefs.get("sleep_enabled", True):
        sleep_map = [
            ("wake",    "wake_time"),
            ("bedtime", "bedtime_time"),
        ]
        for notif_type, key in sleep_map:
            t = prefs.get(key)
            if t:
                utc = _parse_local_time(t, date_str, tz_name)
                if not skip_past or utc >= now_utc:
                    slots.append({
                        "slot_label":        notif_type,
                        "notification_type": notif_type,
                        "scheduled_utc":     utc,
                    })

    # ── Nutrition (6) ─────────────────────────────────────────────────────
    if prefs.get("nutrition_enabled", True):
        nutrition_map = [
            ("breakfast",       "breakfast_time"),
            ("mid_morning",     "mid_morning_time"),
            ("lunch",           "lunch_time"),
            ("afternoon_break", "afternoon_break_time"),
            ("dinner",          "dinner_time"),
            ("post_dinner",     "post_dinner_time"),
        ]
        for notif_type, key in nutrition_map:
            t = prefs.get(key)
            if t:
                utc = _parse_local_time(t, date_str, tz_name)
                if not skip_past or utc >= now_utc:
                    slots.append({
                        "slot_label":        notif_type,
                        "notification_type": notif_type,
                        "scheduled_utc":     utc,
                    })

    # ── Hydration (8) ─────────────────────────────────────────────────────
    if prefs.get("hydration_enabled", True):
        for idx in range(1, 9):
            key = f"hydration_{idx}_time"
            t = prefs.get(key)
            if t:
                utc = _parse_local_time(t, date_str, tz_name)
                if not skip_past or utc >= now_utc:
                    slots.append({
                        "slot_label":        f"hydration_{idx}",
                        "notification_type": "hydration",
                        "scheduled_utc":     utc,
                    })

    return slots


# Core Scheduler Jobs

async def seed_daily_states(date_str: Optional[str] = None) -> int:
    """
    Insert `pending` notification_state docs for every enabled user.
    Safe to call multiple times (upsert_state uses upsert=True with $setOnInsert).
    Returns the number of slots seeded.
    """
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    client = get_client()
    db = client[DB_NAME]

    users_cursor = db["users"].find(
        {"fcm_token": {"$exists": True, "$ne": None}},
        {"firebase_uid": 1, "notification_prefs": 1, "_id": 0},
    )
    users = await users_cursor.to_list(length=10000)

    seeded = 0
    for user in users:
        uid  = user["firebase_uid"]
        slots = _build_schedule(user, date_str)
        for slot in slots:
            await upsert_state(
                firebase_uid=uid,
                date=date_str,
                slot_label=slot["slot_label"],
                notification_type=slot["notification_type"],
                scheduled_utc=slot["scheduled_utc"],
                status="pending",
            )
            seeded += 1

    logger.info("seed_daily_states: seeded %d slots for %s", seeded, date_str)
    return seeded


async def run_notification_cycle() -> dict:
    """
    Main scheduler cycle — called every SCHEDULER_INTERVAL_MINUTES.

    For each non-resolved state doc for today:
      pending    + now >= scheduled_utc                      → send FCM → sent
      sent       + now >= sent_at + 15 min                   → send reminder → reminded_15
      reminded_15 + now >= reminded_15_at + 15 min           → send final   → reminded_30
      reminded_30 + now >= reminded_30_at + 15 min           → expire        → expired
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")

    client = get_client()
    db = client[DB_NAME]

    states = await get_all_pending_states(date_str)

    stats = {"sent": 0, "reminded_15": 0, "reminded_30": 0, "expired": 0, "skipped": 0}

    if not states:
        return stats

    # Batch-fetch FCM tokens for relevant users
    uids = list({s["firebase_uid"] for s in states})
    users_cursor = db["users"].find(
        {"firebase_uid": {"$in": uids}},
        {"firebase_uid": 1, "fcm_token": 1, "_id": 0},
    )
    token_map: dict[str, str] = {
        u["firebase_uid"]: u.get("fcm_token", "")
        for u in await users_cursor.to_list(length=len(uids))
    }

    # Track UIDs whose token was found invalid this cycle — skip them immediately
    # and clear from DB once rather than hitting FCM on every slot.
    stale_uids: set[str] = set()

    async def _clear_token(uid: str) -> None:
        """Remove the stale FCM token from MongoDB so we stop retrying."""
        await db["users"].update_one(
            {"firebase_uid": uid},
            {"$unset": {"fcm_token": ""}},
        )
        logger.warning("Cleared stale FCM token for uid=%s", uid)

    for state in states:
        uid        = state["firebase_uid"]
        token      = token_map.get(uid, "")
        status     = state["status"]
        slot_label = state["slot_label"]
        notif_type = state["notification_type"]
        scheduled  = state["scheduled_utc"]

        # Make datetime timezone-aware if stored as naive UTC
        if isinstance(scheduled, datetime) and scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=timezone.utc)

        if not token or uid in stale_uids:
            stats["skipped"] += 1
            continue

        template = get_template(notif_type)

        if status == "pending" and now >= scheduled:
            data = template.to_fcm_data(
                uid=uid, slot_label=slot_label, date=date_str,
                is_reminder=False, reminder_count=0,
            )
            result = await asyncio.get_event_loop().run_in_executor(
                None, partial(send_data_message, token, data)
            )
            if result.success:
                await upsert_state(
                    firebase_uid=uid, date=date_str,
                    slot_label=slot_label, notification_type=notif_type,
                    scheduled_utc=scheduled,
                    status="sent", sent_at=now,
                )
                stats["sent"] += 1
            else:
                logger.warning("FCM send failed for %s/%s: %s", uid, slot_label, result.error)
                if result.error == "token_unregistered":
                    stale_uids.add(uid)
                    await _clear_token(uid)

        elif status == "sent":
            sent_at = state.get("sent_at")
            if isinstance(sent_at, datetime) and sent_at.tzinfo is None:
                sent_at = sent_at.replace(tzinfo=timezone.utc)
            if sent_at and now >= sent_at + timedelta(minutes=settings.REMINDER_15_MINUTES):
                data = template.to_fcm_data(
                    uid=uid, slot_label=slot_label, date=date_str,
                    is_reminder=True, reminder_count=1,
                )
                result = await asyncio.get_event_loop().run_in_executor(
                    None, partial(send_data_message, token, data)
                )
                if result.success:
                    await upsert_state(
                        firebase_uid=uid, date=date_str,
                        slot_label=slot_label, notification_type=notif_type,
                        scheduled_utc=scheduled,
                        status="reminded_15", reminded_15_at=now,
                    )
                    stats["reminded_15"] += 1

        elif status == "reminded_15":
            r15 = state.get("reminded_15_at")
            if isinstance(r15, datetime) and r15.tzinfo is None:
                r15 = r15.replace(tzinfo=timezone.utc)
            if r15 and now >= r15 + timedelta(minutes=settings.REMINDER_15_MINUTES):
                data = template.to_fcm_data(
                    uid=uid, slot_label=slot_label, date=date_str,
                    is_reminder=True, reminder_count=2,
                )
                result = await asyncio.get_event_loop().run_in_executor(
                    None, partial(send_data_message, token, data)
                )
                if result.success:
                    await upsert_state(
                        firebase_uid=uid, date=date_str,
                        slot_label=slot_label, notification_type=notif_type,
                        scheduled_utc=scheduled,
                        status="reminded_30", reminded_30_at=now,
                    )
                    stats["reminded_30"] += 1

        elif status == "reminded_30":
            r30 = state.get("reminded_30_at")
            if isinstance(r30, datetime) and r30.tzinfo is None:
                r30 = r30.replace(tzinfo=timezone.utc)
            if r30 and now >= r30 + timedelta(minutes=settings.REMINDER_15_MINUTES):
                # All types expire after the third reminder — user can
                # always re-snooze via the need_15_min / need_30_min buttons.
                await upsert_state(
                    firebase_uid=uid, date=date_str,
                    slot_label=slot_label, notification_type=notif_type,
                    scheduled_utc=scheduled,
                    status="expired",
                )
                stats["expired"] += 1

    logger.info("Notification cycle done: %s", stats)
    return stats


# Scheduler Factory

def create_scheduler() -> AsyncIOScheduler:
    """
    Create and configure the APScheduler AsyncIOScheduler.
    Call scheduler.start() from the FastAPI lifespan context.
    """
    scheduler = AsyncIOScheduler(timezone="UTC")

    # Every N minutes: process pending notifications
    scheduler.add_job(
        run_notification_cycle,
        trigger="interval",
        minutes=settings.SCHEDULER_INTERVAL_MINUTES,
        id="notification_cycle",
        name="Notification cycle",
        replace_existing=True,
        misfire_grace_time=60,
    )

    # Every day at 00:01 UTC: seed tomorrow's notification states
    scheduler.add_job(
        seed_daily_states,
        trigger="cron",
        hour=0,
        minute=1,
        id="seed_daily",
        name="Seed daily notification states",
        replace_existing=True,
    )

    return scheduler
