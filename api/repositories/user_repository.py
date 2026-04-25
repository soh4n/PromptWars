"""
User repository — database access layer for user operations.

Enforces row-level scoping: users can only access their own data.
No raw SQL in routers — all queries go through this layer.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.gamification import UserProgress
from api.models.user import User
from api.utils.logging import get_logger

logger = get_logger(__name__)


class UserRepository:
    """Database operations for User entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_firebase_uid(self, firebase_uid: str) -> User | None:
        """
        Find a user by their Firebase UID.

        Args:
            firebase_uid: The Firebase Authentication UID.

        Returns:
            User if found, None otherwise.
        """
        stmt = select(User).where(User.firebase_uid == firebase_uid)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Get a user by their internal UUID."""
        stmt = select(User).where(User.id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get a user by email address."""
        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_from_firebase(
        self,
        firebase_uid: str,
        email: str,
        display_name: str,
        avatar_url: str | None = None,
    ) -> User:
        """
        Create or update a user from Firebase Auth data.

        On first login, creates the user and initialises their UserProgress.
        On subsequent logins, updates display_name and avatar_url.

        Args:
            firebase_uid: Firebase UID.
            email: User's email.
            display_name: Display name from Firebase.
            avatar_url: Profile picture URL.

        Returns:
            The created or updated User.
        """
        user = await self.get_by_firebase_uid(firebase_uid)

        if user is None:
            user = User(
                firebase_uid=firebase_uid,
                email=email,
                display_name=display_name,
                avatar_url=avatar_url,
            )
            self._session.add(user)
            await self._session.flush()

            # Initialise gamification progress
            progress = UserProgress(user_id=user.id)
            self._session.add(progress)
            await self._session.flush()

            logger.info(
                "New user created",
                extra={"user_id": str(user.id), "email": email},
            )
        else:
            user.display_name = display_name
            if avatar_url:
                user.avatar_url = avatar_url
            await self._session.flush()

        return user
