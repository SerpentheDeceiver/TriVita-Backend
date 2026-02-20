"""
Pydantic models for daily health log endpoints.
Covers sleep, hydration, and nutrition log requests/responses.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────

class SleepEntryMode(str, Enum):
    time         = "time"          # bed_time + wake_time provided
    hours        = "hours"         # only total hours provided
    notification = "notification"  # preset hours (from app notification)


class SleepSource(str, Enum):
    manual       = "manual"
    notification = "notification"
    profile      = "profile"


# ── Sleep ────────────────────────────────────────────────────────────────────

class SleepLogRequest(BaseModel):
    """
    At least one of (bed_time, wake_time, hours) must be present.
    - time mode    : provide bed_time + wake_time  (hours auto-computed)
    - hours mode   : provide hours only
    - bed+hours    : wake_time auto-computed
    - wake+hours   : bed_time auto-computed
    - notification : entry_mode='notification', hours provided
    """
    entry_mode : SleepEntryMode = SleepEntryMode.hours
    source     : SleepSource    = SleepSource.manual
    bed_time   : Optional[str]  = Field(None, description="HH:MM 24-hr or HH:MM AM/PM")
    wake_time  : Optional[str]  = Field(None, description="HH:MM 24-hr or HH:MM AM/PM")
    hours      : Optional[float] = Field(None, ge=0.5, le=24)


# ── Hydration ────────────────────────────────────────────────────────────────

class HydrationLogRequest(BaseModel):
    amount_ml      : int           = Field(..., gt=0, le=5000, description="ml of water consumed")
    estimated_time : Optional[str] = Field(None, description="HH:MM 24-hr — predefined slot / scheduled time")


# ── Nutrition ────────────────────────────────────────────────────────────────

class FoodItem(BaseModel):
    name    : str
    cal     : float = Field(..., ge=0)
    protein : float = Field(0.0, ge=0)
    carbs   : float = Field(0.0, ge=0)
    fat     : float = Field(0.0, ge=0)


class NutritionLogRequest(BaseModel):
    meal_type      : str            = Field(..., description="breakfast|mid_morning|lunch|afternoon_break|dinner|post_dinner|other")
    estimated_time : Optional[str]  = Field(None, description="HH:MM 24-hr — predefined meal / scheduled time")
    items          : list[FoodItem] = Field(..., min_length=1)


# ── Daily log fetch response shape ──────────────────────────────────────────

class DailyLogResponse(BaseModel):
    firebase_uid : str
    date         : str
    sleep        : Optional[dict] = None
    hydration    : Optional[dict] = None
    nutrition    : Optional[dict] = None
    scores       : Optional[dict] = None
    updated_at   : Optional[datetime] = None
