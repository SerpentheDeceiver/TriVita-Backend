"""
Pydantic models for user profile creation and storage.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class ActivityLevel(str, Enum):
    sedentary = "sedentary"
    light = "light"
    moderate = "moderate"
    active = "active"
    very_active = "very_active"


class Goal(str, Enum):
    maintain = "maintain"
    reduce = "reduce"
    increase = "increase"


# ──────────────────────────────────────────────
# Input model (request body)
# ──────────────────────────────────────────────

class UserCreateRequest(BaseModel):
    firebase_uid: str = Field(..., description="Firebase UID from client auth")
    email: str = Field(default="", description="User email address")
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=10, le=120)
    weight_kg: float = Field(..., gt=0, le=500, description="Weight in kilograms")
    height_cm: float = Field(..., gt=0, le=300, description="Height in centimetres")
    gender: Gender
    activity_level: ActivityLevel
    goal: Goal

    # Optional weight-change specifics
    target_weight_change_kg: Optional[float] = Field(
        default=0.0, ge=0, description="How many kg to gain/lose (ignored for maintain)"
    )
    timeline_weeks: Optional[int] = Field(
        default=12, ge=1, description="Target timeline in weeks"
    )

    # Sleep schedule (collected during sign-up)
    sleep_time: Optional[str] = Field(
        default="10:00 PM", description="Preferred bed time, e.g. '10:00 PM'"
    )
    wake_time: Optional[str] = Field(
        default="6:00 AM", description="Preferred wake time, e.g. '6:00 AM'"
    )
    sleep_target_hours: Optional[float] = Field(
        default=8.0, ge=4, le=12, description="Daily sleep goal in hours"
    )

    model_config = {"use_enum_values": True}


# ──────────────────────────────────────────────
# Computed targets (sub-document)
# ──────────────────────────────────────────────

class ComputedTargets(BaseModel):
    calorie_target: int
    water_target_ml: int
    protein_target_g: int
    sleep_target_hours: float
    sleep_time: str
    wake_time: str
    bmr: int
    tdee: int
    target_weight_change_kg: float = 0.0
    timeline_weeks: int = 12


# ──────────────────────────────────────────────
# Full user document (as stored in MongoDB)
# ──────────────────────────────────────────────

class UserDocument(BaseModel):
    firebase_uid: str
    email: str

    # Basic profile
    name: str
    age: int
    weight_kg: float
    height_cm: float
    gender: str
    activity_level: str
    goal: str

    # Optional weight-change specifics
    target_weight_change_kg: float = 0.0
    timeline_weeks: int = 12

    # Sleep schedule
    sleep_time: str = "10:00 PM"
    wake_time: str = "6:00 AM"

    # Computed targets
    targets: ComputedTargets

    created_at: datetime = Field(default_factory=datetime.utcnow)


# ──────────────────────────────────────────────
# API response schema
# ──────────────────────────────────────────────

class ProfileResponse(BaseModel):
    status: str          # "created" | "exists"
    firebase_uid: str
    name: str
    email: str
    targets: ComputedTargets
