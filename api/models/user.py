"""
User model — maps to Firebase Auth users with local profile data.

Each user is created on first successful login via upsert on firebase_uid.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base


class User(Base):
    """Registered user linked to a Firebase Auth account."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    firebase_uid: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    progress: Mapped["UserProgress"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="user", uselist=False, lazy="selectin"
    )
    sessions: Mapped[list["LearningSession"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="user", lazy="selectin"
    )
