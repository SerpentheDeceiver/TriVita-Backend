# Profile management routes: Create and retrieve user profiles.
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongo import get_users_collection
from app.models.user import ProfileResponse, UserCreateRequest, UserDocument
from app.services.target_service import calculate_targets

router = APIRouter(tags=["Profile"])


@router.post(
    "/create",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or retrieve a user profile",
)
async def create_profile(
    body: UserCreateRequest,
    db: AsyncIOMotorCollection = Depends(get_users_collection),
) -> ProfileResponse:
    """
    Creates a new profile or returns the existing one.
    firebase_uid and email must be included in the request body.
    """
    firebase_uid: str = body.firebase_uid
    email: str = body.email

    existing = await db.find_one({"firebase_uid": firebase_uid})
    if existing:
        targets_dict = existing.get("targets", {})
        from app.models.user import ComputedTargets
        targets = ComputedTargets(**targets_dict)
        return ProfileResponse(
            status="exists",
            firebase_uid=firebase_uid,
            name=existing.get("name", ""),
            email=existing.get("email", email),
            targets=targets,
        )

    targets = calculate_targets(body)

    doc = UserDocument(
        firebase_uid=firebase_uid,
        email=email,
        name=body.name,
        age=body.age,
        weight_kg=body.weight_kg,
        height_cm=body.height_cm,
        gender=body.gender,
        activity_level=body.activity_level,
        goal=body.goal,
        target_weight_change_kg=body.target_weight_change_kg or 0.0,
        timeline_weeks=body.timeline_weeks or 12,
        sleep_time=body.sleep_time or "10:00 PM",
        wake_time=body.wake_time or "6:00 AM",
        targets=targets,
        created_at=datetime.utcnow(),
    )

    try:
        await db.insert_one(doc.model_dump())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save profile: {e}",
        )

    return ProfileResponse(
        status="created",
        firebase_uid=firebase_uid,
        name=body.name,
        email=email,
        targets=targets,
    )


@router.get(
    "/{uid}",
    summary="Get full profile by firebase_uid",
)
async def get_profile(
    uid: str,
    db: AsyncIOMotorCollection = Depends(get_users_collection),
):
    """Return the full user document for the given firebase_uid."""
    doc = await db.find_one({"firebase_uid": uid}, {"_id": 0})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please complete setup first.",
        )
    return doc
