# Analytics routes: Fetch metrics and trends from historical data.
from fastapi import APIRouter, Query, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorCollection
from datetime import date as dt_date, timedelta
import statistics, calendar
from app.db.mongo import get_daily_logs_collection, get_users_collection

router = APIRouter()


def _week_date_range(week: int | None) -> tuple[str, str, str, str]:
    """Returns (start_iso, end_iso, week_label, date_range_display)."""
    today = dt_date.today()
    year, month = today.year, today.month
    month_name   = today.strftime("%b")
    last_day     = calendar.monthrange(year, month)[1]

    if week is None:
        start   = today - timedelta(days=6)
        label   = "Rolling 7 Days"
        display = f"{start.strftime('%b %d')} – {today.strftime('%b %d, %Y')}"
        return start.isoformat(), today.isoformat(), label, display

    bounds = {1: (1, 7), 2: (8, 14), 3: (15, 21), 4: (22, last_day)}
    d1, d2  = bounds[week]
    start   = dt_date(year, month, d1)
    end     = dt_date(year, month, min(d2, last_day))
    label   = f"Week {week}"
    display = f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"
    return start.isoformat(), end.isoformat(), label, display


def _trend(series: list[float]) -> str:
    n = len(series)
    if n < 4:
        return "stable"
    half = n // 2
    prev = statistics.mean(series[:half])
    last = statistics.mean(series[half:])
    if last > prev + 0.5:
        return "improving"
    if last < prev - 0.5:
        return "declining"
    return "stable"


def _parse_to_frac_hour(t: str | None) -> float:
    """Parse HH:MM or ISO datetime → fractional hour (e.g. 23.5)."""
    if not t:
        return 0.0
    try:
        part = t.split("T")[1] if "T" in t else t
        h, m = part[:5].split(":")
        return int(h) + int(m) / 60
    except Exception:
        return 0.0


def _parse_to_hour_int(t: str | None) -> int | None:
    """Parse HH:MM or ISO datetime → integer hour."""
    if not t:
        return None
    try:
        part = t.split("T")[1] if "T" in t else t
        return int(part[:2])
    except Exception:
        return None


def _day_label(d: str) -> str:
    try:
        return dt_date.fromisoformat(d).strftime("%a")
    except Exception:
        return "?"


@router.get("/analytics/weekly")
async def weekly_analytics(
    uid:       str                   = Query(...),
    week:      int | None            = Query(None, ge=1, le=4),
    logs_col:  AsyncIOMotorCollection = Depends(get_daily_logs_collection),
    users_col: AsyncIOMotorCollection = Depends(get_users_collection),
):
    start_iso, end_iso, week_label, date_range = _week_date_range(week)

    # ── fetch from MongoDB ───────────────────────────────────────────────────
    logs = await logs_col.find(
        {"firebase_uid": uid, "date": {"$gte": start_iso, "$lte": end_iso}},
        {"_id": 0},
    ).sort("date", 1).to_list(length=31)

    if not logs:
        raise HTTPException(status_code=404, detail="No log data found for this period")

    n = len(logs)

    # ── User targets from profile ────────────────────────────────────────────
    user    = await users_col.find_one({"firebase_uid": uid})
    targets = (user or {}).get("targets", {})
    sleep_target      = float(targets.get("sleep_target_hours", 8.0))
    hydration_target  = int(targets.get("water_target_ml", 2500))
    calorie_target    = int(targets.get("calorie_target", 2000))

    days       = [log["date"] for log in logs]
    day_labels = [_day_label(d) for d in days]

    # ── Sleep ────────────────────────────────────────────────────────────────
    sleep_daily: list[dict] = []
    for log in logs:
        s      = log.get("sleep") or {}
        hours  = float(s.get("hours") or 0)
        score  = int((log.get("scores") or {}).get("sleep") or 0)
        sleep_daily.append({
            "date":          log["date"],
            "hours":         hours,
            "score":         score,
            "deficit_hours": round(hours - sleep_target, 2),
            "bed_hour":      _parse_to_frac_hour(s.get("bed_time")),
            "wake_hour":     _parse_to_frac_hour(s.get("wake_time")),
        })

    sleep_h    = [d["hours"] for d in sleep_daily]
    sleep_sc   = [float(d["score"]) for d in sleep_daily]
    cum_def: list[float] = []
    running = 0.0
    for d in sleep_daily:
        running += d["deficit_hours"]
        cum_def.append(round(running, 2))

    sleep_section = {
        "daily":               sleep_daily,
        "avg_hours":           round(statistics.mean(sleep_h),  2) if sleep_h  else 0,
        "avg_score":           round(statistics.mean(sleep_sc), 1) if sleep_sc else 0,
        "target_hours":        sleep_target,
        "goal_met_days":       sum(1 for h in sleep_h if h >= sleep_target),
        "trend":               _trend(sleep_sc),
        "cumulative_deficit":  cum_def,
        "total_deficit_hours": round(running, 2),
    }

    # ── Hydration ────────────────────────────────────────────────────────────
    tb_labels = ["6am", "8am", "10am", "12pm", "2pm", "4pm", "6pm", "8pm"]
    tb_totals = [0.0] * 8
    hyd_daily: list[dict] = []

    for log in logs:
        h        = log.get("hydration") or {}
        total_ml = int(h.get("total_ml") or 0)
        score    = int((log.get("scores") or {}).get("hydration") or 0)
        for entry in h.get("entries") or []:
            raw   = entry.get("logged_time") or entry.get("timestamp") or ""
            hour  = _parse_to_hour_int(raw)
            if hour is not None:
                idx = max(0, min(7, (hour - 6) // 2))
                tb_totals[idx] += entry.get("amount_ml", 0)
        hyd_daily.append({
            "date":     log["date"],
            "total_ml": total_ml,
            "score":    score,
            "goal_met": total_ml >= hydration_target,
            "gap_ml":   total_ml - hydration_target,
        })

    hyd_ml  = [d["total_ml"] for d in hyd_daily]
    hyd_sc  = [float(d["score"]) for d in hyd_daily]
    avg_tb  = [round(v / n, 0) for v in tb_totals]

    hydration_section = {
        "daily":               hyd_daily,
        "avg_ml":              round(statistics.mean(hyd_ml),  0) if hyd_ml  else 0,
        "avg_score":           round(statistics.mean(hyd_sc),  1) if hyd_sc  else 0,
        "target_ml":           hydration_target,
        "goal_met_days":       sum(1 for d in hyd_daily if d["goal_met"]),
        "completion_rate_pct": round(sum(1 for d in hyd_daily if d["goal_met"]) / n * 100, 1),
        "trend":               _trend(hyd_sc),
        "avg_time_blocks":     avg_tb,
        "time_block_labels":   tb_labels,
    }

    # ── Nutrition ────────────────────────────────────────────────────────────
    meal_totals: dict[str, float] = {}
    nutr_daily: list[dict] = []

    for log in logs:
        nu   = log.get("nutrition") or {}
        tots = nu.get("totals") or {}
        cal  = float(tots.get("calories") or 0)
        sc   = int((log.get("scores") or {}).get("nutrition") or 0)
        for entry in nu.get("entries") or []:
            mt = entry.get("meal_type", "other")
            meal_totals[mt] = meal_totals.get(mt, 0) + float(entry.get("meal_calories") or 0)
        nutr_daily.append({
            "date":        log["date"],
            "calories":    cal,
            "protein":     float(tots.get("protein") or 0),
            "carbs":       float(tots.get("carbs") or 0),
            "fat":         float(tots.get("fat") or 0),
            "score":       sc,
            "calorie_gap": cal - calorie_target,
        })

    cal_list  = [d["calories"] for d in nutr_daily]
    nutr_sc   = [float(d["score"]) for d in nutr_daily]
    avg_pro   = round(statistics.mean([d["protein"] for d in nutr_daily]), 1) if nutr_daily else 0
    avg_car   = round(statistics.mean([d["carbs"]   for d in nutr_daily]), 1) if nutr_daily else 0
    avg_fat_v = round(statistics.mean([d["fat"]     for d in nutr_daily]), 1) if nutr_daily else 0
    mac_tot   = avg_pro + avg_car + avg_fat_v

    def _pct(v: float) -> float:
        return round(v / mac_tot * 100, 1) if mac_tot else 0

    avg_meal  = {k: round(v / n, 0) for k, v in meal_totals.items()}

    nutrition_section = {
        "daily":           nutr_daily,
        "avg_calories":    round(statistics.mean(cal_list),  0) if cal_list  else 0,
        "avg_score":       round(statistics.mean(nutr_sc),   1) if nutr_sc   else 0,
        "calorie_target":  calorie_target,
        "avg_macro": {
            "protein_g":  avg_pro,   "protein_pct":  _pct(avg_pro),
            "carbs_g":    avg_car,   "carbs_pct":    _pct(avg_car),
            "fat_g":      avg_fat_v, "fat_pct":      _pct(avg_fat_v),
        },
        "avg_meal_calories": avg_meal,
        "trend": _trend(nutr_sc),
    }

    # ── Wellness ─────────────────────────────────────────────────────────────
    well_sc = [float((log.get("scores") or {}).get("wellness") or 0) for log in logs]

    return {
        "week_label": week_label,
        "date_range": date_range,
        "days":       days,
        "day_labels": day_labels,
        "n_days":     n,
        "sleep":      sleep_section,
        "hydration":  hydration_section,
        "nutrition":  nutrition_section,
        "wellness": {
            "scores": well_sc,
            "avg":    round(statistics.mean(well_sc), 1) if well_sc else 0,
            "trend":  _trend(well_sc),
        },
    }
