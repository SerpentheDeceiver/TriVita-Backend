# Meal Plan routes: Generation and persistence.

from datetime import date as dt_date, datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument

from app.db.mongo import get_daily_logs_collection, get_meal_plans_collection, get_users_collection
from app.agents.nutrition_agent import nutrition_agent, generate_full_day_plan

router = APIRouter(tags=["Meal Plan"])


def _today() -> str:
    return dt_date.today().isoformat()


def _build_profile_state(profile: dict, log: dict) -> dict:
    """Shared helper: build the agent state dict from profile + daily log."""
    targets   = profile.get("targets", {})
    nutrition = log.get("nutrition", {})
    totals    = nutrition.get("totals", {})
    return {
        "calorie_target":          targets.get("calorie_target",  2000),
        "protein_target":          targets.get("protein_target",  150),
        "water_target_ml":         targets.get("water_target_ml", 2500),
        "weight":                  profile.get("weight_kg",               70),
        "age":                     profile.get("age",                     25),
        "gender":                  profile.get("gender",                  "male"),
        "weight_goal":             profile.get("goal",                    "maintain"),
        "target_weight_change_kg": profile.get("target_weight_change_kg", 0),
        "target_timeline_weeks":   profile.get("timeline_weeks",          12),
        "activity_level":          profile.get("activity_level",          "moderate"),
        "total_daily_calories":    totals.get("calories", 0),
        "total_daily_protein":     totals.get("protein",  0),
        "sleep_hours":             (log.get("sleep") or {}).get("hours", 7),
        "hydration_score":         (log.get("scores") or {}).get("hydration", 50),
        "exercise_duration":       0,
        "exercise_type":           "none",
        "budget_per_meal":         10,
    }


# Endpoints

@router.get("/meal-plan/saved", summary="Get saved meal plan for a date")
async def get_saved_meal_plan(
    uid:  str = Query(..., description="Firebase UID"),
    date: str = Query(None, description="Date YYYY-MM-DD (defaults to today)"),
    meal_plans_col: AsyncIOMotorCollection = Depends(get_meal_plans_collection),
):
    target_date = date or _today()
    plan = await meal_plans_col.find_one(
        {"firebase_uid": uid, "date": target_date}, {"_id": 0}
    )
    if not plan:
        return {"exists": False, "date": target_date, "uid": uid}
    return {"exists": True, **plan}



@router.post("/meal-plan/generate", summary="AI-generate a full-day meal plan")
async def generate_meal_plan(
    body: dict = Body(...),
    users_col: AsyncIOMotorCollection = Depends(get_users_collection),
    logs_col:  AsyncIOMotorCollection = Depends(get_daily_logs_collection),
):
    uid          = body.get("uid")
    cuisine_type = body.get("cuisine_type", "international")

    if not uid:
        raise HTTPException(status_code=400, detail="uid is required")

    profile = await users_col.find_one({"firebase_uid": uid}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    log = await logs_col.find_one(
        {"firebase_uid": uid, "date": _today()}, {"_id": 0}
    ) or {}

    state = _build_profile_state(profile, log)
    state["cuisine_type"] = cuisine_type

    result = generate_full_day_plan(state)

    targets = profile.get("targets", {})
    return {
        "uid":           uid,
        "cuisine_type":  cuisine_type,
        "ai_generated":  result.get("ai_nutrition_generated", False),
        "meals":         result.get("full_day_meals", []),
        "daily_summary": result.get("daily_summary", ""),
        "tips":          result.get("nutrition_tips", []),
        "targets_snapshot": {
            "calorie_target": targets.get("calorie_target", 2000),
            "protein_target": targets.get("protein_target", 150),
        },
    }



@router.post("/meal-plan/save", summary="Save (upsert) a meal plan for a date")
async def save_meal_plan(
    body: dict = Body(...),
    meal_plans_col: AsyncIOMotorCollection = Depends(get_meal_plans_collection),
    users_col: AsyncIOMotorCollection = Depends(get_users_collection),
):
    uid           = body.get("uid")
    date          = body.get("date", _today())
    cuisine_type  = body.get("cuisine_type", "international")
    meals         = body.get("meals", [])
    daily_summary = body.get("daily_summary", "")

    if not uid:
        raise HTTPException(status_code=400, detail="uid is required")
    if not meals:
        raise HTTPException(status_code=400, detail="meals list is required")

    profile = await users_col.find_one({"firebase_uid": uid}, {"_id": 0})
    targets = (profile or {}).get("targets", {})
    targets_snapshot = {
        "calorie_target": targets.get("calorie_target", 2000),
        "protein_target": targets.get("protein_target", 150),
    }

    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        "firebase_uid":     uid,
        "date":             date,
        "cuisine_type":     cuisine_type,
        "meals":            meals,
        "daily_summary":    daily_summary,
        "targets_snapshot": targets_snapshot,
        "updated_at":       now_iso,
    }

    existing = await meal_plans_col.find_one({"firebase_uid": uid, "date": date})
    if existing:
        updated = await meal_plans_col.find_one_and_update(
            {"firebase_uid": uid, "date": date},
            {"$set": doc},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
        return {"status": "updated", **updated}
    else:
        doc["created_at"] = now_iso
        result = await meal_plans_col.insert_one(doc)
        doc.pop("_id", None)
        return {"status": "created", **doc}



@router.get("/meal-plan", summary="[Legacy] AI meal suggestions for today")
async def get_meal_plan(
    uid: str = Query(..., description="Firebase UID"),
    users_col: AsyncIOMotorCollection = Depends(get_users_collection),
    logs_col:  AsyncIOMotorCollection = Depends(get_daily_logs_collection),
):
    profile = await users_col.find_one({"firebase_uid": uid}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    today = _today()
    log = await logs_col.find_one(
        {"firebase_uid": uid, "date": today}, {"_id": 0}
    ) or {}

    state = _build_profile_state(profile, log)
    result_state = nutrition_agent(state)

    return {
        "uid":                uid,
        "date":               today,
        "calorie_target":     state["calorie_target"],
        "calories_logged":    state["total_daily_calories"],
        "calories_remaining": max(0, state["calorie_target"] - state["total_daily_calories"]),
        "meal_suggestions":   result_state.get("meal_suggestions", []),
        "daily_summary":      result_state.get("nutrition_summary", ""),
        "tips":               result_state.get("nutrition_tips", []),
        "ai_generated":       result_state.get("ai_nutrition_generated", False),
    }
