"""
Session repository — database access for learning sessions and messages.

All queries are scoped to the authenticated user's ID.
"""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.learning_session import (
    LearningSession,
    SessionMessage,
    SessionStatus,
)
from api.utils.logging import get_logger

logger = get_logger(__name__)


class SessionRepository:
    """Database operations for LearningSession and SessionMessage."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_session(
        self,
        user_id: uuid.UUID,
        topic: str,
        difficulty_level: int = 1,
    ) -> LearningSession:
        """Create a new learning session."""
        learning_session = LearningSession(
            user_id=user_id,
            topic=topic,
            difficulty_level=difficulty_level,
        )
        self._session.add(learning_session)
        await self._session.flush()
        logger.info(
            "Learning session created",
            extra={"session_id": str(learning_session.id), "topic": topic},
        )
        return learning_session

    async def get_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> LearningSession | None:
        """Get a session by ID, scoped to the user."""
        stmt = select(LearningSession).where(
            LearningSession.id == session_id,
            LearningSession.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[LearningSession]:
        """List learning sessions for a user, newest first."""
        stmt = (
            select(LearningSession)
            .where(LearningSession.user_id == user_id)
            .order_by(LearningSession.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def end_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Mark a session as completed."""
        stmt = (
            update(LearningSession)
            .where(
                LearningSession.id == session_id,
                LearningSession.user_id == user_id,
            )
            .values(
                status=SessionStatus.COMPLETED,
                ended_at=func.now(),
            )
        )
        await self._session.execute(stmt)

    async def add_message(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        token_count: int = 0,
    ) -> SessionMessage:
        """Add a message to a learning session."""
        message = SessionMessage(
            session_id=session_id,
            role=role,
            content=content,
            token_count=token_count,
        )
        self._session.add(message)
        await self._session.flush()
        return message

    async def get_recent_messages(
        self,
        session_id: uuid.UUID,
        limit: int = 10,
    ) -> list[SessionMessage]:
        """Get the most recent messages in a session for context."""
        stmt = (
            select(SessionMessage)
            .where(SessionMessage.session_id == session_id)
            .order_by(SessionMessage.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        messages = list(result.scalars().all())
        messages.reverse()  # Return in chronological order
        return messages

    async def get_message_count(self, session_id: uuid.UUID) -> int:
        """Get total message count for a session."""
        stmt = (
            select(func.count())
            .select_from(SessionMessage)
            .where(SessionMessage.session_id == session_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
