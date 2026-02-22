# Daily log routes for sleep, hydration, and nutrition.
from __future__ import annotations

import math
import re
from datetime import datetime, date as dt_date, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongo import get_daily_logs_collection, get_users_collection
from app.models.daily_log import (
    DailyLogResponse,
    HydrationLogRequest,
    NutritionLogRequest,
    SleepEntryMode,
    SleepLogRequest,
)
from app.services.scoring import recompute_scores

router = APIRouter(tags=["Daily Logs"])


# Helpers

def _today() -> str:
    return dt_date.today().isoformat()   # "YYYY-MM-DD"


def _now_hhmm() -> str:
    """Return current time as HH:MM in IST (Asia/Kolkata)."""
    import pytz
    return datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%H:%M")


def _parse_to_minutes(t: str) -> int:
    """
    Parse HH:MM (24-hr) or H:MM AM/PM to total minutes since midnight.
    Returns -1 on failure.
    """
    t = t.strip()
    # 12-hr format: e.g. "10:30 PM"
    m = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)", t, re.IGNORECASE)
    if m:
        h, mi, period = int(m.group(1)), int(m.group(2)), m.group(3).upper()
        if period == "PM" and h != 12:
            h += 12
        if period == "AM" and h == 12:
            h = 0
        return h * 60 + mi
    # 24-hr format: "23:10"
    m = re.match(r"(\d{1,2}):(\d{2})$", t)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    return -1


def _minutes_to_hhmm(minutes: int) -> str:
    minutes = minutes % (24 * 60)
    h, m = divmod(minutes, 60)
    return f"{h:02d}:{m:02d}"


def _compute_sleep_fields(req: SleepLogRequest) -> dict:
    """
    Resolve / compute all sleep fields from the request.
    Returns a dict ready to $set into the 'sleep' subdocument.
    Raises HTTPException on invalid combos.
    """
    bed_min  = _parse_to_minutes(req.bed_time)  if req.bed_time  else -1
    wake_min = _parse_to_minutes(req.wake_time) if req.wake_time else -1

    hours: Optional[float] = req.hours

    has_bed  = bed_min  >= 0
    has_wake = wake_min >= 0
    has_hrs  = hours is not None

    if not has_bed and not has_wake and not has_hrs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one of: bed_time, wake_time, hours",
        )

    # Derive missing fields
    if has_bed and has_wake:
        # cross-midnight support
        diff = wake_min - bed_min
        if diff <= 0:
            diff += 24 * 60
        hours = round(diff / 60, 2)
    elif has_bed and has_hrs:
        wake_min = (bed_min + int(hours * 60)) % (24 * 60)
        has_wake = True
    elif has_wake and has_hrs:
        bed_min = (wake_min - int(hours * 60)) % (24 * 60)
        has_bed = True

    result: dict = {
        "entry_mode": req.entry_mode,
        "source":     req.source,
        "logged_at":  datetime.now(timezone.utc).isoformat(),
    }
    if hours is not None:
        result["hours"] = round(hours, 2)
    if has_bed:
        result["bed_time"]  = _minutes_to_hhmm(bed_min)
    if has_wake:
        result["wake_time"] = _minutes_to_hhmm(wake_min)

    return result


async def _get_user_targets(
    firebase_uid: str, users_col: AsyncIOMotorCollection
) -> tuple[float, int, int]:
    """Return (sleep_target_hours, water_target_ml, calorie_target) from profile."""
    user = await users_col.find_one({"firebase_uid": firebase_uid})
    if not user:
        return 8.0, 2500, 2000
    targets = user.get("targets") or {}
    return (
        float(targets.get("sleep_target_hours", 8.0)),
        int(targets.get("water_target_ml",  2500)),
        int(targets.get("calorie_target",   2000)),
    )


# Endpoints

@router.post("/sleep", summary="Log today's sleep")
async def log_sleep(
    body: SleepLogRequest,
    uid: str = Query(..., description="Firebase UID"),
    logs_col:  AsyncIOMotorCollection = Depends(get_daily_logs_collection),
    users_col: AsyncIOMotorCollection = Depends(get_users_collection),
):
    firebase_uid = uid
    today        = _today()

    # Check for existing sleep entry
    existing = await logs_col.find_one(
        {"firebase_uid": firebase_uid, "date": today},
        {"sleep": 1},
    )
    existing_sleep = (existing or {}).get("sleep") or {}
    if existing_sleep.get("hours") is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sleep already logged for today. Only one sleep entry per day is allowed.",
        )

    sleep_doc = _compute_sleep_fields(body)
    # Preserve any partial wake/bedtime already set from notifications
    if not sleep_doc.get("wake_time") and existing_sleep.get("wake_time"):
        sleep_doc["wake_time"] = existing_sleep["wake_time"]
    if not sleep_doc.get("bed_time") and existing_sleep.get("bed_time"):
        sleep_doc["bed_time"] = existing_sleep["bed_time"]

    # Upsert: create day doc if it doesn't exist, then set sleep section
    await logs_col.update_one(
        {"firebase_uid": firebase_uid, "date": today},
        {
            "$set":         {"sleep": sleep_doc, "updated_at": datetime.now(timezone.utc)},
            "$setOnInsert": {"firebase_uid": firebase_uid, "date": today},
        },
        upsert=True,
    )

    sleep_hrs, water_ml, cal = await _get_user_targets(firebase_uid, users_col)
    scores = await recompute_scores(
        logs_col, firebase_uid, today,
        sleep_target_hours=sleep_hrs,
        water_target_ml=water_ml,
        calorie_target=cal,
    )
    return {"status": "ok", "sleep": sleep_doc, "scores": scores}


@router.post("/hydration", summary="Log a hydration entry")
async def log_hydration(
    body: HydrationLogRequest,
    uid: str = Query(..., description="Firebase UID"),
    logs_col:  AsyncIOMotorCollection = Depends(get_daily_logs_collection),
    users_col: AsyncIOMotorCollection = Depends(get_users_collection),
):
    firebase_uid = uid
    today        = _today()
    # Get timestamps
    logged_time    = body.logged_time or _now_hhmm()
    estimated_time = body.estimated_time or logged_time

    entry = {"amount_ml": body.amount_ml, "estimated_time": estimated_time, "logged_time": logged_time}

    await logs_col.update_one(
        {"firebase_uid": firebase_uid, "date": today},
        {
            "$inc":         {"hydration.total_ml": body.amount_ml},
            "$push":        {"hydration.entries": entry},
            "$set":         {"updated_at": datetime.now(timezone.utc)},
            "$setOnInsert": {"firebase_uid": firebase_uid, "date": today},
        },
        upsert=True,
    )

    sleep_hrs, water_ml, cal = await _get_user_targets(firebase_uid, users_col)
    scores = await recompute_scores(
        logs_col, firebase_uid, today,
        sleep_target_hours=sleep_hrs,
        water_target_ml=water_ml,
        calorie_target=cal,
    )
    return {"status": "ok", "entry": entry, "scores": scores}


@router.post("/nutrition", summary="Log a meal / nutrition entry")
async def log_nutrition(
    body: NutritionLogRequest,
    uid: str = Query(..., description="Firebase UID"),
    logs_col:  AsyncIOMotorCollection = Depends(get_daily_logs_collection),
    users_col: AsyncIOMotorCollection = Depends(get_users_collection),
):
    firebase_uid = uid
    today        = _today()
    # Get timestamps
    logged_time    = body.logged_time or _now_hhmm()
    estimated_time = body.estimated_time or logged_time

    # Compute per-item totals and meal subtotal
    items_list = [item.model_dump() for item in body.items]
    meal_calories = sum(i["cal"] for i in items_list)
    total_protein = sum(i["protein"] for i in items_list)
    total_carbs   = sum(i["carbs"]   for i in items_list)
    total_fat     = sum(i["fat"]     for i in items_list)

    entry = {
        "meal_type":      body.meal_type,
        "estimated_time": estimated_time,
        "logged_time":    logged_time,
        "items":          items_list,
        "meal_calories":  meal_calories,
    }

    await logs_col.update_one(
        {"firebase_uid": firebase_uid, "date": today},
        {
            "$push": {"nutrition.entries": entry},
            "$inc":  {
                "nutrition.totals.calories": meal_calories,
                "nutrition.totals.protein":  total_protein,
                "nutrition.totals.carbs":    total_carbs,
                "nutrition.totals.fat":      total_fat,
            },
            "$set":         {"updated_at": datetime.now(timezone.utc)},
            "$setOnInsert": {"firebase_uid": firebase_uid, "date": today},
        },
        upsert=True,
    )

    sleep_hrs, water_ml, cal = await _get_user_targets(firebase_uid, users_col)
    scores = await recompute_scores(
        logs_col, firebase_uid, today,
        sleep_target_hours=sleep_hrs,
        water_target_ml=water_ml,
        calorie_target=cal,
    )
    return {"status": "ok", "entry": entry, "scores": scores}


@router.get("/today", summary="Get today's complete log")
async def get_today_log(
    uid: str = Query(..., description="Firebase UID"),
    logs_col:  AsyncIOMotorCollection = Depends(get_daily_logs_collection),
    users_col: AsyncIOMotorCollection = Depends(get_users_collection),
):
    firebase_uid = uid
    today        = _today()
    doc = await logs_col.find_one(
        {"firebase_uid": firebase_uid, "date": today},
        {"_id": 0},
    )
    if not doc:
        return {"firebase_uid": firebase_uid, "date": today, "message": "No log for today yet"}

    # Recompute scores on every read so they stay accurate even if targets
    # were updated after the last log entry.
    sleep_hrs, water_ml, cal = await _get_user_targets(firebase_uid, users_col)
    scores = await recompute_scores(
        logs_col, firebase_uid, today,
        sleep_target_hours=sleep_hrs,
        water_target_ml=water_ml,
        calorie_target=cal,
    )
    doc["scores"] = scores
    return doc


@router.get("/{log_date}", summary="Get log for a specific date (YYYY-MM-DD)")
async def get_log_by_date(
    log_date: str,
    uid: str = Query(..., description="Firebase UID"),
    logs_col: AsyncIOMotorCollection = Depends(get_daily_logs_collection),
):
    firebase_uid = uid
    # validate format
    try:
        dt_date.fromisoformat(log_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    doc = await logs_col.find_one(
        {"firebase_uid": firebase_uid, "date": log_date},
        {"_id": 0},
    )
    if not doc:
        return {"firebase_uid": firebase_uid, "date": log_date, "message": "No log for this date"}
    return doc
