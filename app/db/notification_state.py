"""
MongoDB helper for the notification_states collection.

Document shape:
{
    firebase_uid:       str,          # user partition key
    date:               str,          # "YYYY-MM-DD"
    notification_type:  str,          # wake|breakfast|lunch|dinner|hydration|bedtime|custom
    slot_label:         str,          # human-readable slot id (e.g. "hydration_1", "breakfast")
    scheduled_utc:      datetime,
    sent_at:            datetime | None,
    reminded_15_at:     datetime | None,
    reminded_30_at:     datetime | None,
    resolved_at:        datetime | None,
    status:             str,          # pending|sent|reminded_15|reminded_30|resolved|expired
    action_taken:       str | None,   # ml_250|ml_500|ml_750|logged|skipped|snooze_15|snooze_30|i_am_awake|…
}

Compound unique index: (firebase_uid, date, slot_label)
"""

from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongo import get_client
import os

DB_NAME: str = os.getenv("MONGO_DB_NAME", "health_ai")

# ─────────────────────────────────────────────────────────────────────────────
# Collection accessor
# ─────────────────────────────────────────────────────────────────────────────

async def get_notification_states_collection() -> AsyncIOMotorCollection:
    client = get_client()
    db = client[DB_NAME]
    collection = db["notification_states"]
    await collection.create_index(
        [("firebase_uid", 1), ("date", 1), ("slot_label", 1)],
        unique=True,
    )
    return collection


# ─────────────────────────────────────────────────────────────────────────────
# CRUD helpers
# ─────────────────────────────────────────────────────────────────────────────

async def upsert_state(
    firebase_uid: str,
    date: str,
    slot_label: str,
    notification_type: str,
    scheduled_utc: datetime,
    status: str = "pending",
    **kwargs,
) -> None:
    """
    Insert a notification state document, or update status/timestamps
    if it already exists.  `kwargs` can pass sent_at, reminded_15_at, etc.
    """
    col = await get_notification_states_collection()
    update_fields = {
        "notification_type": notification_type,
        "scheduled_utc": scheduled_utc,
        "status": status,
        **kwargs,
    }
    await col.update_one(
        {"firebase_uid": firebase_uid, "date": date, "slot_label": slot_label},
        {
            "$set": update_fields,
            "$setOnInsert": {
                "firebase_uid": firebase_uid,
                "date": date,
                "slot_label": slot_label,
                "sent_at": None,
                "reminded_15_at": None,
                "reminded_30_at": None,
                "resolved_at": None,
                "action_taken": None,
            },
        },
        upsert=True,
    )


async def get_state(
    firebase_uid: str, date: str, slot_label: str
) -> Optional[dict]:
    col = await get_notification_states_collection()
    return await col.find_one(
        {"firebase_uid": firebase_uid, "date": date, "slot_label": slot_label},
        {"_id": 0},
    )


async def mark_resolved(
    firebase_uid: str,
    date: str,
    slot_label: str,
    action_taken: str,
) -> None:
    col = await get_notification_states_collection()
    await col.update_one(
        {"firebase_uid": firebase_uid, "date": date, "slot_label": slot_label},
        {
            "$set": {
                "status": "resolved",
                "resolved_at": datetime.now(timezone.utc),
                "action_taken": action_taken,
            }
        },
    )


async def update_scheduled_utc(
    firebase_uid: str,
    date: str,
    slot_label: str,
    new_scheduled_utc: datetime,
    new_status: str = "pending",
) -> None:
    """Push scheduled_utc forward (snooze) and reset status to pending."""
    col = await get_notification_states_collection()
    await col.update_one(
        {"firebase_uid": firebase_uid, "date": date, "slot_label": slot_label},
        {
            "$set": {
                "scheduled_utc": new_scheduled_utc,
                "status": new_status,
                "sent_at": None,
                "reminded_15_at": None,
                "reminded_30_at": None,
            }
        },
    )


async def get_all_pending_states(date: str) -> list[dict]:
    """
    Return all non-resolved, non-expired state docs for a given date.
    Used by the scheduler bulk cycle.
    """
    col = await get_notification_states_collection()
    cursor = col.find(
        {
            "date": date,
            "status": {"$nin": ["resolved", "expired"]},
        },
        {"_id": 0},
    )
    return await cursor.to_list(length=5000)


async def get_user_states_for_date(firebase_uid: str, date: str) -> list[dict]:
    """All states for a specific user on a specific date."""
    col = await get_notification_states_collection()
    cursor = col.find(
        {"firebase_uid": firebase_uid, "date": date},
        {"_id": 0},
    ).sort("scheduled_utc", 1)
    return await cursor.to_list(length=100)
