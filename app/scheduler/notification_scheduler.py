"""
Notification Scheduler Engine.

Responsibilities:
  1. seed_daily_states()  — run at midnight (or manually) to insert
     `pending` notification_state docs for every user's schedule today.
  2. run_notification_cycle()  — run every 5 min to:
       • send FCM for due slots (pending → sent)
       • send 15-min reminder (sent → reminded_15)
       • send 30-min reminder (reminded_15 → reminded_30)
       • expire after 45 min with no response (reminded_30 → expired)

APScheduler 3.x  (AsyncIOScheduler)  is used so jobs run in the same
asyncio event loop as FastAPI, avoiding thread-safety issues with Motor.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
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


# ─────────────────────────────────────────────────────────────────────────────
# Default notification prefs (used when user hasn't set preferences)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_PREFS = {
    "enabled": False,
    "timezone": "UTC",
    "wake_time": "07:00",
    "breakfast_time": "08:00",
    "lunch_time": "13:00",
    "dinner_time": "19:30",
    "bedtime_time": "22:30",
    "hydration_interval_hours": 3,
    "custom_slots": [],
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

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


def _build_schedule(user_doc: dict, date_str: str) -> list[dict]:
    """
    Build today's notification schedule for a user.
    Returns list of {slot_label, notification_type, scheduled_utc}.
    """
    prefs = {**DEFAULT_PREFS, **(user_doc.get("notification_prefs") or {})}

    if not prefs.get("enabled", False):
        return []

    tz_name = prefs.get("timezone", "UTC")
    slots = []

    # Fixed slots
    fixed = [
        ("wake",      "wake_time"),
        ("breakfast", "breakfast_time"),
        ("lunch",     "lunch_time"),
        ("dinner",    "dinner_time"),
        ("bedtime",   "bedtime_time"),
    ]
    for notif_type, pref_key in fixed:
        t = prefs.get(pref_key)
        if t:
            slots.append({
                "slot_label": notif_type,
                "notification_type": notif_type,
                "scheduled_utc": _parse_local_time(t, date_str, tz_name),
            })

    # Hydration slots  — spread evenly from wake_time to bedtime_time
    interval_h = float(prefs.get("hydration_interval_hours", 3))
    wake_str   = prefs.get("wake_time", "07:00")
    bed_str    = prefs.get("bedtime_time", "22:30")
    wake_utc   = _parse_local_time(wake_str, date_str, tz_name)
    bed_utc    = _parse_local_time(bed_str,  date_str, tz_name)

    current = wake_utc + timedelta(hours=interval_h)
    idx = 1
    while current < bed_utc:
        slots.append({
            "slot_label": f"hydration_{idx}",
            "notification_type": "hydration",
            "scheduled_utc": current,
        })
        current += timedelta(hours=interval_h)
        idx += 1

    # Custom slots
    for cs in prefs.get("custom_slots", []):
        label = cs.get("label", f"custom_{idx}")
        t     = cs.get("time")
        if t:
            slots.append({
                "slot_label": label,
                "notification_type": "custom",
                "scheduled_utc": _parse_local_time(t, date_str, tz_name),
            })

    return slots


# ─────────────────────────────────────────────────────────────────────────────
# Core async jobs
# ─────────────────────────────────────────────────────────────────────────────

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
            result = send_data_message(token, data)
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
                result = send_data_message(token, data)
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
                result = send_data_message(token, data)
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
                await upsert_state(
                    firebase_uid=uid, date=date_str,
                    slot_label=slot_label, notification_type=notif_type,
                    scheduled_utc=scheduled,
                    status="expired",
                )
                stats["expired"] += 1

    logger.info("Notification cycle done: %s", stats)
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# APScheduler factory
# ─────────────────────────────────────────────────────────────────────────────

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
