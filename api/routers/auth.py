"""
Auth router — registration, login, password reset.

All routes except registration and password reset require a valid Firebase ID token.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from firebase_admin import auth as firebase_auth
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.session import get_db
from api.repositories.gamification_repository import GamificationRepository
from api.repositories.user_repository import UserRepository
from api.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
)
from api.services.audit_service import log_auth_event
from api.services.gamification_service import update_streak
from api.utils.auth import FirebaseUser, get_current_user, get_firebase_app
from api.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """
    Register a new user with email and password via Firebase Admin SDK.

    Creates the Firebase Auth user and the local DB record.
    """
    get_firebase_app()
    try:
        firebase_user = firebase_auth.create_user(
            email=request.email,
            password=request.password,
            display_name=request.display_name,
        )
    except firebase_auth.EmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from exc
    except Exception as exc:
        logger.error("Firebase user creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again.",
        ) from exc

    repo = UserRepository(db)
    user = await repo.upsert_from_firebase(
        firebase_uid=firebase_user.uid,
        email=request.email,
        display_name=request.display_name,
    )

    log_auth_event("register", str(user.id), request.email)

    return AuthResponse(
        user=UserResponse(
            id=user.id, email=user.email,
            display_name=user.display_name, avatar_url=user.avatar_url,
            created_at=user.created_at,
        ),
        message="Registration successful",
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """
    Login with a Firebase ID token.

    Verifies the token, upserts the user, and updates their daily streak.
    """
    get_firebase_app()
    try:
        decoded = firebase_auth.verify_id_token(request.id_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from exc

    repo = UserRepository(db)
    user = await repo.upsert_from_firebase(
        firebase_uid=decoded["uid"],
        email=decoded.get("email", ""),
        display_name=decoded.get("name", decoded.get("email", "User")),
        avatar_url=decoded.get("picture"),
    )

    # Update daily streak
    await update_streak(db, user.id)

    # Get gamification stats
    gam_repo = GamificationRepository(db)
    progress = await gam_repo.get_progress(user.id)

    log_auth_event("login", str(user.id), user.email)

    return AuthResponse(
        user=UserResponse(
            id=user.id, email=user.email,
            display_name=user.display_name, avatar_url=user.avatar_url,
            total_xp=progress.total_xp if progress else 0,
            level=progress.level if progress else 1,
            streak_days=progress.streak_days if progress else 0,
            created_at=user.created_at,
        ),
    )


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(request: ResetPasswordRequest) -> dict:
    """Send a password reset email via Firebase."""
    get_firebase_app()
    try:
        link = firebase_auth.generate_password_reset_link(request.email)
        logger.info("Password reset link generated", extra={"email": request.email})
    except Exception as exc:
        logger.warning("Password reset failed: %s", exc)
        # Don't reveal whether the email exists
        pass

    return {"message": "If an account exists with this email, a reset link has been sent."}


@router.get("/me", response_model=UserResponse)
async def get_me(
    firebase_user: Annotated[FirebaseUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Get the current authenticated user's profile."""
    repo = UserRepository(db)
    user = await repo.get_by_firebase_uid(firebase_user.uid)

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    gam_repo = GamificationRepository(db)
    progress = await gam_repo.get_progress(user.id)

    return UserResponse(
        id=user.id, email=user.email,
        display_name=user.display_name, avatar_url=user.avatar_url,
        total_xp=progress.total_xp if progress else 0,
        level=progress.level if progress else 1,
        streak_days=progress.streak_days if progress else 0,
        created_at=user.created_at,
    )
