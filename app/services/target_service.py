"""
Target calculation service.
Reuses existing app.services.formulas (calculate_bmr, water_target_ml, protein_target_g)
and mirrors the logic already present in profile_agent.py.
"""
from app.services.formulas import (
    calculate_bmr,
    water_target_ml as _water_ml,
    protein_target_g as _protein_g,
)
from app.models.user import ComputedTargets, UserCreateRequest

# ── Activity multipliers (Mifflin-St Jeor TDEE) ──────────────────────────────
ACTIVITY_MULTIPLIERS: dict[str, float] = {
    "sedentary":  1.2,
    "light":      1.375,
    "moderate":   1.55,
    "active":     1.725,
    "very_active": 1.9,
}

# ── Calorie adjustment for weight goals ──────────────────────────────────────
# ~7700 kcal per kg of body weight.
# Daily delta = (target_kg × 7700) / (timeline_weeks × 7)
# Clamped to ±1000 kcal/day for safety; default ±400 if no target provided.
DEFAULT_CALORIE_DELTA: dict[str, int] = {
    "reduce":   -400,
    "increase": +400,
    "maintain":    0,
}

# ── Protein multipliers (g per kg body weight) ────────────────────────────────
PROTEIN_MULTIPLIERS: dict[str, float] = {
    "reduce":   2.2,   # higher protein preserves muscle during cut
    "increase": 2.0,   # higher protein supports muscle gain
    "maintain": 1.6,
}

# ── Safety floor calories ─────────────────────────────────────────────────────
MIN_CALORIES: dict[str, int] = {
    "male":   1500,
    "female": 1200,
    "other":  1200,
}


def calculate_targets(profile: UserCreateRequest) -> ComputedTargets:
    """
    Pure function – no I/O, fully synchronous.
    Uses existing formulas.py for BMR, water, and base protein.
    """
    w  = profile.weight_kg
    h  = profile.height_cm
    a  = profile.age
    g  = profile.gender          # already str from enum
    al = profile.activity_level  # already str from enum
    gl = profile.goal            # already str from enum

    # ── BMR (Mifflin-St Jeor) via existing formula ────────────────────────────
    bmr = calculate_bmr(w, h, a, g)

    # ── TDEE ──────────────────────────────────────────────────────────────────
    multiplier = ACTIVITY_MULTIPLIERS.get(al, 1.55)
    tdee = bmr * multiplier

    # ── Calorie target ────────────────────────────────────────────────────────
    target_kg   = profile.target_weight_change_kg or 0.0
    timeline_wk = profile.timeline_weeks or 12

    if gl != "maintain" and target_kg > 0 and timeline_wk > 0:
        # 7700 kcal ≈ 1 kg body weight
        daily_delta = (target_kg * 7700) / (timeline_wk * 7)
        daily_delta = min(daily_delta, 1000)  # cap at 1000 kcal/day
        if gl == "reduce":
            daily_delta = -daily_delta
        calorie_delta = int(daily_delta)
    else:
        calorie_delta = DEFAULT_CALORIE_DELTA.get(gl, 0)

    calorie_target = int(tdee) + calorie_delta
    # Safety floor
    calorie_target = max(calorie_target, MIN_CALORIES.get(g, 1200))

    # ── Water target (weight × 35 ml) ─────────────────────────────────────────
    water = int(_water_ml(w))

    # ── Protein target ────────────────────────────────────────────────────────
    protein_mult = PROTEIN_MULTIPLIERS.get(gl, 1.6)
    protein = int(w * protein_mult)

    # ── Sleep target ──────────────────────────────────────────────────────────
    sleep_hours = profile.sleep_target_hours if profile.sleep_target_hours else 8.0
    sleep_time  = profile.sleep_time  or "10:00 PM"
    wake_time   = profile.wake_time   or "6:00 AM"

    return ComputedTargets(
        calorie_target=calorie_target,
        water_target_ml=water,
        protein_target_g=protein,
        sleep_target_hours=sleep_hours,
        sleep_time=sleep_time,
        wake_time=wake_time,
        bmr=int(bmr),
        tdee=int(tdee),
        target_weight_change_kg=target_kg,
        timeline_weeks=timeline_wk,
    )
