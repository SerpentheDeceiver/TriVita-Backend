# MongoDB async connection using Motor driver.
# URI is taken from the MONGO_URI environment variable.
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from app.core.config import settings

# Module-level singleton client (created once, reused across all requests)
_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URI)
    return _client


async def get_users_collection() -> AsyncIOMotorCollection:
    """
    FastAPI dependency – yields the users collection and
    ensures a unique index on firebase_uid exists.
    """
    client = get_client()
    db = client[settings.MONGO_DB_NAME]
    collection = db["users"]
    # Idempotent: only creates the index if it doesn't exist
    await collection.create_index("firebase_uid", unique=True)
    return collection


async def get_daily_logs_collection() -> AsyncIOMotorCollection:
    """
    FastAPI dependency – yields the daily_logs collection and
    ensures a unique compound index on (firebase_uid, date).
    """
    client = get_client()
    db = client[settings.MONGO_DB_NAME]
    collection = db["daily_logs"]
    # Compound unique index: one document per user per day
    await collection.create_index(
        [("firebase_uid", 1), ("date", 1)], unique=True
    )
    return collection


async def get_meal_plans_collection() -> AsyncIOMotorCollection:
    """
    FastAPI dependency – yields the meal_plans collection and
    ensures a unique compound index on (firebase_uid, date).
    """
    client = get_client()
    db = client[settings.MONGO_DB_NAME]
    collection = db["meal_plans"]
    # Compound unique index: one saved plan per user per day
    await collection.create_index(
        [("firebase_uid", 1), ("date", 1)], unique=True
    )
    return collection
