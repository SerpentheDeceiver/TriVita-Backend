"""One-off script: clear a stale FCM token from MongoDB."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

UID = "K9Nekn5YPkX40YKv3RFt8rrHv6t1"

async def main():
    client = AsyncIOMotorClient("mongodb://10.212.187.87:27017")
    db = client["health_ai"]
    result = await db["users"].update_one(
        {"firebase_uid": UID},
        {"$unset": {"fcm_token": ""}},
    )
    print(f"matched={result.matched_count}  modified={result.modified_count}")
    if result.matched_count == 0:
        print("User not found — check UID or DB name")
    else:
        print("FCM token cleared. Scheduler will stop retrying.")

asyncio.run(main())
