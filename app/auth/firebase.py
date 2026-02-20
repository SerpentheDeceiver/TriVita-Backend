"""
Firebase Admin SDK initialisation and token verification dependency.
Production-safe: validates credential file exists before initialising,
initialises only once via lru_cache, raises clear errors if config is missing.
"""
import os
import sys
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, auth
from fastapi import Header, HTTPException, status
from dotenv import load_dotenv

load_dotenv()


@lru_cache(maxsize=1)
def _init_firebase() -> None:
    """
    Initialise Firebase Admin SDK exactly once.
    Reads the credentials path from FIREBASE_CREDENTIALS_PATH env var.
    Raises RuntimeError with a clear message if the file is missing.
    """
    if firebase_admin._apps:
        return  # Already initialised — nothing to do

    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "").strip()
    if not cred_path:
        raise RuntimeError(
            "FIREBASE_CREDENTIALS_PATH environment variable is not set. "
            "On Render, upload firebase_service_account.json as a Secret File "
            "at /etc/secrets/firebase_service_account.json and set "
            "FIREBASE_CREDENTIALS_PATH=/etc/secrets/firebase_service_account.json"
        )

    if not os.path.isfile(cred_path):
        raise RuntimeError(
            f"Firebase credentials file not found at '{cred_path}'. "
            "Check that the Secret File is correctly uploaded and the path in "
            "FIREBASE_CREDENTIALS_PATH matches exactly."
        )

    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)


async def verify_firebase_token(
    authorization: str = Header(..., description="Bearer <firebase_id_token>"),
) -> dict:
    """
    FastAPI dependency.
    Extracts and verifies the Firebase ID token from the Authorization header.
    Returns the decoded token payload (contains 'uid', 'email', etc.).
    """
    try:
        _init_firebase()
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

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
