"""
Firebase Auth token verification and FastAPI dependency.

Verifies Bearer tokens on every request (except allowlisted paths).
On first login, upserts the user into the local database.
"""

import base64
import json
import logging
from typing import Annotated

import firebase_admin
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth, credentials

from api.config import settings

logger = logging.getLogger(__name__)

# ── Firebase Admin SDK initialisation ────────────────────────────
_firebase_app: firebase_admin.App | None = None


def get_firebase_app() -> firebase_admin.App:
    """
    Lazily initialise the Firebase Admin SDK.

    Credentials are loaded from a base64-encoded JSON env var
    injected by Secret Manager at Cloud Run runtime.
    """
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    if settings.firebase_credentials_base64:
        cred_json = base64.b64decode(settings.firebase_credentials_base64)
        cred_dict = json.loads(cred_json)
        cred = credentials.Certificate(cred_dict)
    else:
        # Fall back to Application Default Credentials (local dev)
        cred = credentials.ApplicationDefault()

    _firebase_app = firebase_admin.initialize_app(cred)
    logger.info("Firebase Admin SDK initialised")
    return _firebase_app


# ── Security scheme ──────────────────────────────────────────────
bearer_scheme = HTTPBearer(auto_error=False)


class FirebaseUser:
    """Verified Firebase user data extracted from the ID token."""

    def __init__(self, uid: str, email: str, name: str, picture: str | None) -> None:
        self.uid = uid
        self.email = email
        self.name = name
        self.picture = picture


async def get_current_user(
    request: Request,
    token: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
) -> FirebaseUser:
    """
    FastAPI dependency that verifies the Firebase ID token.

    Raises:
        HTTPException 401: If the token is missing or invalid.
    """
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        get_firebase_app()
        decoded = firebase_auth.verify_id_token(token.credentials)
    except firebase_admin.exceptions.FirebaseError as exc:
        logger.warning("Firebase token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except Exception as exc:
        logger.error("Unexpected auth error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return FirebaseUser(
        uid=decoded["uid"],
        email=decoded.get("email", ""),
        name=decoded.get("name", decoded.get("email", "User")),
        picture=decoded.get("picture"),
    )
