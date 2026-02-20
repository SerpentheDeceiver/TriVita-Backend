"""
Analytics Agent – loads 7-day data from tests/weekly_logs/dayN/daily_log.json,
performs real statistical analysis and ML-based wellness prediction.
"""
import json
import os
import statistics
import numpy as np
from pathlib import Path
from sklearn.linear_model import LinearRegression


WEEKLY_LOGS_DIR = Path(__file__).parent.parent.parent.parent / "tests" / "weekly_logs"
SLEEP_TARGET = 8.0
HYDRATION_TARGET_ML = 2500.0
CALORIE_TARGET = 2000.0


def _load_logs() -> list[dict]:
    logs = []
    for day in range(1, 8):
        p = WEEKLY_LOGS_DIR / f"day{day}" / "daily_log.json"
        if p.exists():
            with open(p) as f:
                logs.append(json.load(f))
    return sorted(logs, key=lambda x: x.get("health_date", ""))


def _trend(series: list[float]) -> str:
    """Compare last-3 vs first-3 average."""
    if len(series) < 6:
        return "stable"
    prev3 = statistics.mean(series[:3])
    last3 = statistics.mean(series[-3:])
    if last3 > prev3 + 0.5:
        return "improving"
    if last3 < prev3 - 0.5:
        return "declining"
    return "stable"


def _regression_predict(y_values: list[float], steps: int = 7) -> tuple[list[float], float]:
    """Fit LinearRegression on day-index → value, return next `steps` predictions + slope."""
    n = len(y_values)
    X = np.arange(n).reshape(-1, 1)
    y = np.array(y_values)
    model = LinearRegression()
    model.fit(X, y)
    future = np.arange(n, n + steps).reshape(-1, 1)
    preds = model.predict(future)
    return [round(float(v), 2) for v in preds], float(model.coef_[0])


def analytics_agent(state: dict) -> dict:
    logs = _load_logs()
    if not logs:
        state["analytics"] = {"error": "No daily_log.json files found in weekly_logs/"}
        return state

    n = len(logs)

    # ── Raw series ───────────────────────────────────────────────────────────
    sleep_hours   = [log.get("sleep", {}).get("hours", 0.0) for log in logs]
    sleep_scores  = [log.get("scores", {}).get("sleep", 0) for log in logs]
    hydration_ml  = [log.get("hydration", {}).get("total_ml", 0) for log in logs]
    hydration_sc  = [log.get("scores", {}).get("hydration", 0) for log in logs]
    calories      = [log.get("nutrition", {}).get("totals", {}).get("calories", 0) for log in logs]
    nutrition_sc  = [log.get("scores", {}).get("nutrition", 0) for log in logs]
    wellness_sc   = [log.get("scores", {}).get("wellness", 0) for log in logs]
    dates         = [log.get("health_date", f"day{i+1}") for i, log in enumerate(logs)]

    # ── Sleep analytics ──────────────────────────────────────────────────────
    sleep_deficit = [h - SLEEP_TARGET for h in sleep_hours]  # +ve = over target
    cumulative_deficit = []
    running = 0.0
    for d in sleep_deficit:
        running += d
        cumulative_deficit.append(round(running, 2))

    sleep_preds, sleep_slope = _regression_predict(sleep_scores)

    sleep_analytics = {
        "avg_hours":          round(statistics.mean(sleep_hours), 2),
        "avg_score":          round(statistics.mean(sleep_scores), 1),
        "goal_met_days":      sum(1 for h in sleep_hours if h >= SLEEP_TARGET),
        "goal_pct":           round(sum(1 for h in sleep_hours if h >= SLEEP_TARGET) / n * 100, 1),
        "trend":              _trend(sleep_scores),
        "daily_hours":        sleep_hours,
        "daily_scores":       sleep_scores,
        "daily_deficit":      [round(d, 2) for d in sleep_deficit],
        "cumulative_deficit": cumulative_deficit,
        "next_7_day_score_prediction": sleep_preds,
    }

    # ── Hydration analytics ──────────────────────────────────────────────────
    hydration_gap = [ml - HYDRATION_TARGET_ML for ml in hydration_ml]
    goal_met_days_h = sum(1 for ml in hydration_ml if ml >= HYDRATION_TARGET_ML)
    hyd_preds, _ = _regression_predict(hydration_sc)

    # Time-of-day blocks (avg ml per 2-hour window: 6am..10pm)
    block_totals = [0.0] * 8
    for log in logs:
        for entry in log.get("hydration", {}).get("entries", []):
            ts = entry.get("timestamp", "")
            try:
                hour = int(ts[11:13])
            except Exception:
                hour = 12
            idx = max(0, min(7, (hour - 6) // 2))
            block_totals[idx] += entry.get("amount_ml", 0)

    avg_time_blocks = [round(v / n, 1) for v in block_totals]

    hydration_analytics = {
        "avg_ml":            round(statistics.mean(hydration_ml), 1),
        "avg_score":         round(statistics.mean(hydration_sc), 1),
        "goal_met_days":     goal_met_days_h,
        "completion_rate":   round(goal_met_days_h / n * 100, 1),
        "days_missed":       n - goal_met_days_h,
        "trend":             _trend(hydration_sc),
        "daily_ml":          hydration_ml,
        "daily_scores":      hydration_sc,
        "daily_gap_ml":      [round(g, 0) for g in hydration_gap],
        "avg_time_blocks_ml": avg_time_blocks,
        "time_block_labels": ["6am", "8am", "10am", "12pm", "2pm", "4pm", "6pm", "8pm"],
        "next_7_day_score_prediction": hyd_preds,
    }

    # ── Nutrition analytics ──────────────────────────────────────────────────
    proteins = [log.get("nutrition", {}).get("totals", {}).get("protein", 0) for log in logs]
    carbs    = [log.get("nutrition", {}).get("totals", {}).get("carbs", 0) for log in logs]
    fats     = [log.get("nutrition", {}).get("totals", {}).get("fat", 0) for log in logs]

    avg_protein = round(statistics.mean(proteins), 1)
    avg_carbs   = round(statistics.mean(carbs), 1)
    avg_fat     = round(statistics.mean(fats), 1)
    macro_total = avg_protein + avg_carbs + avg_fat

    def _pct(v):
        return round(v / macro_total * 100, 1) if macro_total else 0

    # Meal timing totals
    meal_totals: dict[str, float] = {"breakfast": 0.0, "lunch": 0.0, "snack": 0.0, "dinner": 0.0}
    for log in logs:
        for entry in log.get("nutrition", {}).get("entries", []):
            mt = entry.get("meal_type", "snack")
            meal_totals[mt] = meal_totals.get(mt, 0) + entry.get("meal_calories", 0)
    avg_meal_cals = {k: round(v / n, 1) for k, v in meal_totals.items()}

    nut_preds, nut_slope = _regression_predict(nutrition_sc)

    nutrition_analytics = {
        "avg_calories":   round(statistics.mean(calories), 1),
        "avg_score":      round(statistics.mean(nutrition_sc), 1),
        "calorie_target": CALORIE_TARGET,
        "trend":          _trend(nutrition_sc),
        "daily_calories": calories,
        "daily_scores":   nutrition_sc,
        "calorie_gaps":   [c - CALORIE_TARGET for c in calories],
        "avg_macro": {
            "protein_g":  avg_protein, "protein_pct":  _pct(avg_protein),
            "carbs_g":    avg_carbs,   "carbs_pct":    _pct(avg_carbs),
            "fat_g":      avg_fat,     "fat_pct":      _pct(avg_fat),
        },
        "avg_meal_calories": avg_meal_cals,
        "next_7_day_score_prediction": nut_preds,
    }

    # ── Wellness regression (historical target) ──────────────────────────────
    well_preds, well_slope = _regression_predict(wellness_sc)

    wellness_analytics = {
        "scores":  wellness_sc,
        "avg":     round(statistics.mean(wellness_sc), 1),
        "trend":   _trend(wellness_sc),
        "next_7_day_prediction": well_preds,
    }

    # ── Aggregate averages (legacy compat) ────────────────────────────────────
    averages = {
        "avg_sleep":      round(statistics.mean(sleep_hours), 2),
        "avg_hydration":  round(statistics.mean(hydration_ml), 1),
        "avg_calories":   round(statistics.mean(calories), 1),
        "avg_wellness":   round(statistics.mean(wellness_sc), 1),
    }

    state["analytics"] = {
        "dates":       dates,
        "averages":    averages,
        "trend":       _trend(wellness_sc),
        "sleep":       sleep_analytics,
        "hydration":   hydration_analytics,
        "nutrition":   nutrition_analytics,
        "wellness":    wellness_analytics,
        "next_7_day_prediction": well_preds,
    }

    return state
