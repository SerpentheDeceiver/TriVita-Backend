"""
Centralised application settings loaded from environment variables / .env file.
All settings are required in production — missing values will raise at startup.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    """Read env var or abort with a clear error message."""
    value = os.getenv(key, "").strip()
    if not value:
        print(
            f"\n❌  MISSING REQUIRED ENV VAR: '{key}'\n"
            f"    Set this in your Render environment variables or .env file.\n",
            file=sys.stderr,
        )
        sys.exit(1)
    return value


class _Settings:
    # ── Required in production ────────────────────────────────────────────────
    MONGO_URI: str      = _require("MONGO_URI")
    MONGO_DB_NAME: str  = os.getenv("MONGO_DB_NAME", "health_ai")
    GROQ_API_KEY: str   = _require("GROQ_API_KEY")

    # Path to Firebase service-account JSON
    # On Render: upload as a Secret File at /etc/secrets/firebase_service_account.json
    FIREBASE_SERVICE_ACCOUNT_PATH: str = _require("FIREBASE_CREDENTIALS_PATH")

    # ── Scheduler ─────────────────────────────────────────────────────────────
    SCHEDULER_INTERVAL_MINUTES: int = int(
        os.getenv("SCHEDULER_INTERVAL_MINUTES", "5")
    )

    # Reminder windows (minutes after initial send)
    REMINDER_15_MINUTES: int = 15
    REMINDER_30_MINUTES: int = 30
    EXPIRY_MINUTES: int      = 45   # after this, no more reminders


settings = _Settings()
