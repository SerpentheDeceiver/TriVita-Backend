"""One-off script: clear a stale FCM token from MongoDB.

Usage:
    python clear_fcm_token.py

Reads MONGO_URI from the project .env file (same Atlas URI the app uses).
Falls back to mongodb://localhost:27017 if MONGO_URI is not set.
"""
import asyncio
import os
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient

# Load .env from the Backend root (one level up if run from scripts/)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # python-dotenv not installed — env vars must already be set

UID  = "K9Nekn5YPkX40YKv3RFt8rrHv6t1"
URI  = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB   = os.getenv("MONGO_DB_NAME", "health_ai")


async def main():
    print(f"Connecting to: {URI[:40]}...")
    client = AsyncIOMotorClient(URI)
    db = client[DB]
    result = await db["users"].update_one(
        {"firebase_uid": UID},
        {"$unset": {"fcm_token": ""}},
    )
    print(f"matched={result.matched_count}  modified={result.modified_count}")
    if result.matched_count == 0:
        print("User not found — check UID or DB name")
    else:
        print("FCM token cleared. Scheduler will stop retrying.")
    client.close()


asyncio.run(main())
