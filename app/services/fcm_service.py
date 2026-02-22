# FCM service for sending data-only push notifications.

import logging
from dataclasses import dataclass
from typing import Optional

import firebase_admin
from firebase_admin import credentials, messaging
from firebase_admin import _apps as firebase_apps

from app.core.config import settings

logger = logging.getLogger(__name__)

def _ensure_firebase_app() -> None:
    """Initialise firebase-admin once; safe to call multiple times."""
    if not firebase_apps:
        try:
            cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialised.")
        except Exception as exc:
            logger.error("Firebase Admin init failed: %s", exc)
            raise

@dataclass
class FCMResult:
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None

def send_data_message(
    fcm_token: str,
    data: dict[str, str],
    *,
    android_priority: str = "high",
) -> FCMResult:
    """Send a data-only FCM message to a single device token."""
    _ensure_firebase_app()

    # FCM requires all data values to be strings
    str_data = {k: str(v) for k, v in data.items()}

    message = messaging.Message(
        data=str_data,
        token=fcm_token,
        android=messaging.AndroidConfig(
            priority=android_priority,
            ttl=3600,  # 1 hour TTL
        ),
    )

    try:
        message_id = messaging.send(message)
        logger.info("FCM sent OK: %s → %s", str_data.get("notification_type"), message_id)
        return FCMResult(success=True, message_id=message_id)
    except messaging.UnregisteredError:
        logger.warning("FCM token unregistered: %s", fcm_token[:20])
        return FCMResult(success=False, error="token_unregistered")
    except messaging.SenderIdMismatchError:
        return FCMResult(success=False, error="sender_id_mismatch")
    except Exception as exc:
        err_msg = str(exc)
        # "not a valid FCM registration token" is an InvalidArgumentError;
        # treat it the same as an unregistered/expired token so the scheduler
        # knows to clear it from the DB rather than retrying indefinitely.
        if "registration token" in err_msg.lower() or "invalid" in err_msg.lower():
            logger.warning("FCM token invalid (will be cleared): %s… — %s", fcm_token[:20], err_msg)
            return FCMResult(success=False, error="token_unregistered")
        logger.error("FCM send error: %s", exc)
        return FCMResult(success=False, error=err_msg)


def send_batch(
    token_data_pairs: list[tuple[str, dict[str, str]]],
) -> list[FCMResult]:
    """Send data-only FCM messages to multiple tokens."""
    _ensure_firebase_app()

    if not token_data_pairs:
        return []

    messages = [
        messaging.Message(
            data={k: str(v) for k, v in data.items()},
            token=token,
            android=messaging.AndroidConfig(priority="high", ttl=3600),
        )
        for token, data in token_data_pairs
    ]

    try:
        batch_response = messaging.send_each(messages)
        results = []
        for resp in batch_response.responses:
            if resp.success:
                results.append(FCMResult(success=True, message_id=resp.message_id))
            else:
                results.append(FCMResult(success=False, error=str(resp.exception)))
        logger.info(
            "FCM batch: %d/%d sent successfully",
            batch_response.success_count,
            len(messages),
        )
        return results
    except Exception as exc:
        logger.error("FCM batch error: %s", exc)
        return [FCMResult(success=False, error=str(exc))] * len(token_data_pairs)
