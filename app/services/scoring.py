# Health score computation for daily logs.
from __future__ import annotations
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorCollection


# Individual scorers

def score_sleep(sleep: dict | None, target_hours: float = 8.0) -> int:
    """
    Score based on actual sleep hours vs target.
    100 = met/exceeded target, scales down linearly, floor 0.
    """
    if not sleep:
        return 0
    hours = sleep.get("hours") or 0.0
    if hours <= 0:
        return 0
    ratio = hours / max(target_hours, 1.0)
    score = min(ratio, 1.0) * 100
    return int(round(min(score, 100)))


def score_hydration(hydration: dict | None, target_ml: int = 2500) -> int:
    """Score based on total_ml consumed vs target. Linear 0–100; capped at 100."""
    if not hydration:
        return 0
    total = hydration.get("total_ml") or 0
    if total <= 0:
        return 0
    ratio = total / max(target_ml, 1)
    return int(round(min(ratio * 100, 100)))


def score_nutrition(nutrition: dict | None, target_cal: int = 2000) -> int:
    """Score based on calories eaten vs target — within ±10% = 100,
    linearly decreasing outside that band.
    Protein bonus: if protein within 80%+ of target → tiny bonus capped at 100.
    """
    if not nutrition:
        return 0
    totals = nutrition.get("totals") or {}
    cal = totals.get("calories") or 0
    if cal <= 0:
        return 0
    ratio = cal / max(target_cal, 1)
    if 0.9 <= ratio <= 1.1:
        score = 100.0
    elif ratio < 0.9:
        score = (ratio / 0.9) * 100
    else:
        over = min((ratio - 1.1) / 0.2, 1.0)
        score = 100 - over * 30
    return int(round(max(0, min(score, 100))))


def compute_wellness(sleep_s: int, hydration_s: int, nutrition_s: int) -> int:
    logged_count = sum(1 for s in [sleep_s, hydration_s, nutrition_s] if s > 0)
    if logged_count == 0:
        return 0
    total = sleep_s + hydration_s + nutrition_s
    return int(round(total / 3))


# Main recompute helper

async def recompute_scores(
    db: AsyncIOMotorCollection,
    firebase_uid: str,
    date: str,
    *,
    sleep_target_hours: float = 8.0,
    water_target_ml: int = 2500,
    calorie_target: int = 2000,
) -> dict:
    """
    Fetch the day's document, recompute all scores, persist $set scores.*,
    and return the updated scores dict.
    """
    doc = await db.find_one({"firebase_uid": firebase_uid, "date": date})
    if not doc:
        return {"sleep": 0, "hydration": 0, "nutrition": 0, "wellness": 0}

    s_score = score_sleep(doc.get("sleep"), sleep_target_hours)
    h_score = score_hydration(doc.get("hydration"), water_target_ml)
    n_score = score_nutrition(doc.get("nutrition"), calorie_target)
    w_score = compute_wellness(s_score, h_score, n_score)

    scores = {
        "sleep":     s_score,
        "hydration": h_score,
        "nutrition": n_score,
        "wellness":  w_score,
    }

    await db.update_one(
        {"firebase_uid": firebase_uid, "date": date},
        {"$set": {"scores": scores, "updated_at": datetime.now(timezone.utc)}},
    )
    return scores
