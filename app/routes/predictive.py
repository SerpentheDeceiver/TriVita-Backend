# Predictive Analysis route: Machine learning models for health trends.
from __future__ import annotations

import math
import re
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from app.mcp import get_mcp_client

router = APIRouter(prefix="/predictive", tags=["Predictive Analysis"])

# Constants
SLEEP_TARGET_H  = 8.0
CALORIE_PER_KG  = 7700.0    # kcal needed to change body weight by 1 kg


# Helpers

def _parse_to_frac_hour(t: Optional[str]) -> Optional[float]:
    """'10:30 PM' | '22:30' | None  →  fractional 24-hr hour (22.5)."""
    if not t:
        return None
    t = t.strip()
    m = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)", t, re.I)
    if m:
        h, mi, p = int(m.group(1)), int(m.group(2)), m.group(3).upper()
        if p == "PM" and h != 12:
            h += 12
        if p == "AM" and h == 12:
            h = 0
        return h + mi / 60
    m = re.match(r"(\d{1,2}):(\d{2})$", t)
    if m:
        return int(m.group(1)) + int(m.group(2)) / 60
    return None


def _frac_to_hhmm(frac: float) -> str:
    """22.5 → '10:30 PM'."""
    frac = frac % 24
    h = int(frac)
    mi = int(round((frac - h) * 60))
    period = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{mi:02d} {period}"


def _safe_std(vals: List[float]) -> float:
    return statistics.stdev(vals) if len(vals) >= 2 else 0.0


# A. Sleep Risk Classification (Logistic Regression)

def _sleep_risk_model(
    sleep_hours: List[float],
    sleep_target: float,
) -> Dict[str, Any]:
    """
    Train LR on synthetic sleep-science data, then predict on user features.
    Features: [avg_3d, std_dev, cum_deficit]
    """
    if not sleep_hours:
        return {
            "risk_probability": 0.0,
            "risk_label": "No Data",
            "risk_level": "unknown",
            "features": {},
            "message": "Log at least 1 day of sleep to see risk.",
        }

    # Build cumulative deficit
    deficits = [h - sleep_target for h in sleep_hours]
    cum_deficit = sum(deficits)
    recent = sleep_hours[-3:] if len(sleep_hours) >= 3 else sleep_hours
    avg_3d  = statistics.mean(recent)
    std_dev = _safe_std(sleep_hours)

    user_feat = np.array([[avg_3d, std_dev, cum_deficit]])

    # Synthetic training set: 40 labelled examples grounded in sleep medicine
    rng = np.random.default_rng(42)
    safe_avg    = rng.normal(7.8, 0.5, 20).clip(6.5, 10)
    safe_std    = rng.uniform(0, 0.8, 20)
    safe_def    = rng.normal(0, 2, 20)
    risky_avg   = rng.normal(5.8, 1.0, 20).clip(2, 7.4)
    risky_std   = rng.uniform(0.5, 2.5, 20)
    risky_def   = rng.normal(-6, 3, 20)

    X_train = np.vstack([
        np.column_stack([safe_avg,  safe_std,  safe_def]),
        np.column_stack([risky_avg, risky_std, risky_def]),
    ])
    y_train = np.array([0] * 20 + [1] * 20)

    scaler = StandardScaler()
    X_s    = scaler.fit_transform(X_train)
    x_user = scaler.transform(user_feat)

    lr = LogisticRegression(max_iter=500, random_state=42)
    lr.fit(X_s, y_train)
    prob = float(lr.predict_proba(x_user)[0][1])  # probability of risk=1

    # Label
    if prob < 0.35:
        label, level = "Low", "low"
    elif prob < 0.65:
        label, level = "Moderate", "moderate"
    else:
        label, level = "High", "high"

    return {
        "risk_probability": round(prob, 3),
        "risk_percent":     round(prob * 100, 1),
        "risk_label":       label,
        "risk_level":       level,
        "features": {
            "avg_sleep_3d":  round(avg_3d, 2),
            "std_dev":       round(std_dev, 2),
            "cum_deficit":   round(cum_deficit, 2),
        },
    }


# B. Sleep Pattern Clustering (K-Means)

_SLEEP_CLUSTER_NAMES = {
    0: "Consistent Sleeper",
    1: "Early Sleeper",
    2: "Sleep Deprived",
    3: "Irregular Sleeper",
}
_SLEEP_CLUSTER_HEX = {
    0: "#22C55E",   # green
    1: "#8B5CF6",   # purple
    2: "#EF4444",   # red
    3: "#F59E0B",   # amber
}


def _sleep_cluster_model(
    logs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Cluster each logged day by (bed_time_frac, sleep_hours)."""
    points = []
    for log in logs:
        sleep = log.get("sleep") or {}
        hrs   = sleep.get("hours")
        bed   = _parse_to_frac_hour(sleep.get("bed_time"))
        if hrs is None or bed is None:
            continue
        points.append({
            "date":        log.get("date", "?"),
            "sleep_hours": round(float(hrs), 2),
            "bed_time_frac": round(float(bed), 3),
            "bed_time_label": _frac_to_hhmm(float(bed)),
        })

    if len(points) < 2:
        return {
            "scatter_points":  points,
            "cluster_labels":  _SLEEP_CLUSTER_NAMES,
            "cluster_colors":  _SLEEP_CLUSTER_HEX,
            "cluster_counts":  {},
            "message": "Log at least 2 days with bed & wake times to see clusters.",
        }

    k = min(4, len(points))
    X = np.array([[p["bed_time_frac"], p["sleep_hours"]] for p in points])
    km = KMeans(n_clusters=k, random_state=42, n_init="auto")
    labels = km.fit_predict(X)

    # Assign semantic names by cluster centre characteristics
    # Centre closest to (22.5, 8.0) → Consistent;  lowest hours → Sleep Deprived;
    # earliest bed-time → Early Sleeper; highest bed-time std → Irregular
    centres   = km.cluster_centers_                    # shape (k, 2)
    bed_c     = centres[:, 0]
    hrs_c     = centres[:, 1]

    # Sort clusters by increasing hours so lowest → deprived, highest → consistent
    order     = np.argsort(hrs_c)                      # ascending by avg hours
    name_map  = {}
    colour_map = {}
    semantic  = ["Sleep Deprived", "Irregular Sleeper", "Early Sleeper", "Consistent Sleeper"]
    hex_list  = ["#EF4444", "#F59E0B", "#8B5CF6", "#22C55E"]
    for new_idx, old_idx in enumerate(order):
        name_map[int(old_idx)]   = semantic[new_idx]
        colour_map[int(old_idx)] = hex_list[new_idx]

    counts: Dict[str, int] = {}
    for p, lbl in zip(points, labels):
        p["cluster"]       = int(lbl)
        p["cluster_name"]  = name_map[int(lbl)]
        p["cluster_color"] = colour_map[int(lbl)]
        counts[name_map[int(lbl)]] = counts.get(name_map[int(lbl)], 0) + 1

    return {
        "scatter_points":  points,
        "cluster_labels":  name_map,
        "cluster_colors":  colour_map,
        "cluster_counts":  counts,
    }


# C. Hydration Behaviour Clustering (K-Means)

def _hydration_cluster_model(
    logs: List[Dict[str, Any]],
    water_target: float,
) -> Dict[str, Any]:
    """
    Features per day: [avg_intake_hour, total_ml_normalised, delay_variance]
    Cluster → Early / Late / Under / Consistent hydrator.
    """
    day_feats = []
    for log in logs:
        hyd     = log.get("hydration") or {}
        total   = float(hyd.get("total_ml") or 0)
        entries = hyd.get("entries") or []
        times   = []
        for e in entries:
            for k in ("logged_time", "estimated_time"):
                fh = _parse_to_frac_hour(e.get(k))
                if fh is not None:
                    times.append(fh)
                    break

        if total < 50:
            continue   # no meaningful hydration logged this day

        avg_hour   = statistics.mean(times) if times else 12.0
        delay_var  = statistics.stdev(times) if len(times) >= 2 else 0.0
        day_feats.append({
            "date":           log.get("date", "?"),
            "total_ml":       round(total),
            "avg_hour":       round(avg_hour, 2),
            "delay_variance": round(delay_var, 2),
            "avg_hour_label": _frac_to_hhmm(avg_hour),
        })

    if len(day_feats) < 2:
        return {
            "daily_points":  day_feats,
            "cluster_counts": {},
            "message": "Log at least 2 days of hydration to see behaviour clusters.",
        }

    k = min(4, len(day_feats))
    X = np.array([[d["avg_hour"], d["total_ml"] / water_target, d["delay_variance"]]
                  for d in day_feats])
    km = KMeans(n_clusters=k, random_state=42, n_init="auto")
    labels = km.fit_predict(X)

    centres   = km.cluster_centers_    # (avg_hour, normalised_ml, delay_var)
    avg_h_c   = centres[:, 0]
    ml_c      = centres[:, 1]

    # Semantic assignment: low ml → under-hydrator;
    #   high ml + early hour → early hydrator;
    #   high ml + late hour  → late hydrator; else consistent
    name_map   = {}
    colour_map = {}
    hex_map    = {"Under-hydrator": "#EF4444", "Early Hydrator": "#22C55E",
                  "Late Hydrator":  "#F59E0B", "Consistent Hydrator": "#3B82F6"}
    ml_order   = np.argsort(ml_c)   # ascending
    under_idx  = int(ml_order[0])
    name_map[under_idx]   = "Under-hydrator"
    colour_map[under_idx] = hex_map["Under-hydrator"]
    remaining = [i for i in range(k) if i != under_idx]
    for i in remaining:
        if avg_h_c[i] < 12:
            n = "Early Hydrator"
        elif avg_h_c[i] > 16:
            n = "Late Hydrator"
        else:
            n = "Consistent Hydrator"
        name_map[i]   = n
        colour_map[i] = hex_map.get(n, "#94A3B8")

    counts: Dict[str, int] = {}
    for d, lbl in zip(day_feats, labels):
        name = name_map.get(int(lbl), "Consistent Hydrator")
        d["cluster"]       = int(lbl)
        d["cluster_name"]  = name
        d["cluster_color"] = colour_map.get(int(lbl), "#94A3B8")
        counts[name] = counts.get(name, 0) + 1

    return {
        "daily_points":  day_feats,
        "cluster_counts": counts,
        "cluster_colors": colour_map,
    }


# D. Weight-Change Projection (Calorie Deficit Regression)

def _weight_projection_model(
    logs: List[Dict[str, Any]],
    calorie_target: float,
    current_weight: float,
) -> Dict[str, Any]:
    """
    Estimate weekly weight change from calorie deficit.
    weekly_delta_kg = avg_daily_deficit * 7 / 7700
    Returns projection for next 7 days.
    """
    cal_actuals = []
    for log in logs:
        nut = log.get("nutrition") or {}
        tot = nut.get("totals") or {}
        c   = tot.get("calories")
        if c is not None and float(c) > 0:
            cal_actuals.append(float(c))

    if not cal_actuals:
        return {
            "projection_points": [],
            "weekly_change_kg":  0.0,
            "current_weight":    current_weight,
            "avg_calorie_deficit": 0.0,
            "trend":             "stable",
            "message": "Log nutrition data to see weight projection.",
        }

    avg_cal    = statistics.mean(cal_actuals)
    avg_deficit = calorie_target - avg_cal   # +ve = deficit (losing weight)
    weekly_kg  = round(avg_deficit * 7 / CALORIE_PER_KG, 3)

    # Project daily weight for next 7 days using linear trend
    daily_change = weekly_kg / 7
    projection   = []
    from datetime import date as dt_date, timedelta as td
    today = dt_date.today()
    w     = current_weight
    for i in range(1, 8):
        w = round(w + daily_change, 2)
        projection.append({
            "day":    (today + td(days=i)).strftime("%b %d"),
            "weight": w,
        })

    trend = "stable"
    if weekly_kg > 0.1:
        trend = "gaining"
    elif weekly_kg < -0.1:
        trend = "losing"

    return {
        "projection_points":   projection,
        "weekly_change_kg":    weekly_kg,
        "current_weight":      current_weight,
        "avg_daily_calories":  round(avg_cal, 1),
        "avg_calorie_deficit": round(avg_deficit, 1),
        "trend":               trend,
    }


# Main endpoint

@router.get("/analysis")
async def get_predictive_analysis(uid: str = Query(...)):
    """
    Run all 4 ML models on the user's real MongoDB history.
    Returns a structured payload consumed by the Flutter predictive page.
    """
    try:
        mcp = await get_mcp_client()
        await mcp.ensure_connected()

        # Fetch last 30 days of logs
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        cursor = mcp._db["daily_logs"].find(
            {"firebase_uid": uid, "date": {"$gte": start_date}},
            {"sleep": 1, "hydration": 1, "nutrition": 1, "date": 1, "_id": 0},
        ).sort("date", 1)
        logs: List[Dict] = await cursor.to_list(length=30)

        # Fetch profile for targets
        profile         = await mcp.get_user_profile(uid)
        sleep_target    = float(profile.get("sleep_target") or SLEEP_TARGET_H)
        water_target    = float(profile.get("hydration_target") or 2500)
        calorie_target  = float(profile.get("calorie_target") or 2000)
        current_weight  = float(profile.get("weight") or 70)

        # Extract sleep series
        sleep_hours = [
            float(log["sleep"]["hours"])
            for log in logs
            if log.get("sleep") and log["sleep"].get("hours") is not None
        ]

        # Run models
        sleep_risk   = _sleep_risk_model(sleep_hours, sleep_target)
        sleep_clust  = _sleep_cluster_model(logs)
        hydra_clust  = _hydration_cluster_model(logs, water_target)
        weight_proj  = _weight_projection_model(logs, calorie_target, current_weight)

        return {
            "days_analyzed":        len(logs),
            "sleep_risk":           sleep_risk,
            "sleep_clusters":       sleep_clust,
            "hydration_clusters":   hydra_clust,
            "weight_projection":    weight_proj,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
