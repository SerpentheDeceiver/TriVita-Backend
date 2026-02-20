"""
Centralised application settings loaded from environment variables / .env file.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class _Settings:
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/health_ai")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "health_ai")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Path to the Firebase service-account JSON file (downloaded from Firebase Console)
    # Matches the .env key: FIREBASE_CREDENTIALS_PATH
    FIREBASE_SERVICE_ACCOUNT_PATH: str = os.getenv(
        "FIREBASE_CREDENTIALS_PATH",
        os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "./firebase_service_account.json"),
    )

    # Scheduler
    SCHEDULER_INTERVAL_MINUTES: int = int(
        os.getenv("SCHEDULER_INTERVAL_MINUTES", "5")
    )

    # Reminder windows (minutes after initial send)
    REMINDER_15_MINUTES: int = 15
    REMINDER_30_MINUTES: int = 30
    EXPIRY_MINUTES: int = 45   # after this no more reminders


settings = _Settings()
