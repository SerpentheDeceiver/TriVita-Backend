"""
MongoDB async connection using Motor driver.
Single client instance for connection pooling.
"""
import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from dotenv import load_dotenv

load_dotenv()

MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/health_ai")
DB_NAME: str = os.getenv("MONGO_DB_NAME", "health_ai")

# Module-level singleton client (created once, reused across requests)
_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URI)
    return _client


async def get_users_collection() -> AsyncIOMotorCollection:
    """
    FastAPI dependency – yields the users collection and
    ensures a unique index on firebase_uid exists.
    """
    client = get_client()
    db = client[DB_NAME]
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
    db = client[DB_NAME]
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
    db = client[DB_NAME]
    collection = db["meal_plans"]
    # Compound unique index: one saved plan per user per day
    await collection.create_index(
        [("firebase_uid", 1), ("date", 1)], unique=True
    )
    return collection
