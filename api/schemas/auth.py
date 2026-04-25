"""Pydantic schemas for authentication request/response validation."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request body for email/password registration."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    """Request body for token-based login (Firebase ID token)."""

    id_token: str = Field(min_length=1)


class ResetPasswordRequest(BaseModel):
    """Request body for password reset email."""

    email: EmailStr


class UserResponse(BaseModel):
    """Public user profile response."""

    id: uuid.UUID
    email: str
    display_name: str
    avatar_url: str | None = None
    total_xp: int = 0
    level: int = 1
    streak_days: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Response after successful authentication."""

    user: UserResponse
    message: str = "Authentication successful"
