"""
Firebase Admin SDK initialisation and token verification dependency.
"""
import os
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, auth
from fastapi import Header, HTTPException, status
from dotenv import load_dotenv

load_dotenv()

_CRED_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase_service_account.json")


@lru_cache(maxsize=1)
def _init_firebase() -> None:
    """Initialise Firebase Admin SDK exactly once."""
    if not firebase_admin._apps:
        cred = credentials.Certificate(_CRED_PATH)
        firebase_admin.initialize_app(cred)


async def verify_firebase_token(
    authorization: str = Header(..., description="Bearer <firebase_id_token>"),
) -> dict:
    """
    FastAPI dependency.
    Extracts and verifies the Firebase ID token from the Authorization header.
    Returns the decoded token payload (contains 'uid', 'email', etc.).
    """
    _init_firebase()

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected: Bearer <token>",
        )

    id_token = authorization.removeprefix("Bearer ").strip()

    try:
        decoded = auth.verify_id_token(id_token)
        return decoded
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase token has expired. Please sign in again.",
        )
    except auth.InvalidIdTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase token: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {e}",
        )
