"""
Gamification repository — database access for XP, achievements, mastery, leaderboard.

All write operations are scoped to the authenticated user.
Leaderboard queries return limited public data only.
"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.gamification import (
    Achievement,
    TopicMastery,
    UserAchievement,
    UserProgress,
)
from api.models.user import User
from api.utils.logging import get_logger

logger = get_logger(__name__)


class GamificationRepository:
    """Database operations for gamification entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── User Progress ─────────────────────────────────────────────

    async def get_progress(self, user_id: uuid.UUID) -> UserProgress | None:
        """Get a user's gamification progress."""
        stmt = select(UserProgress).where(UserProgress.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_xp(
        self,
        user_id: uuid.UUID,
        xp_amount: int,
        new_level: int,
    ) -> None:
        """Add XP and update level for a user."""
        stmt = (
            update(UserProgress)
            .where(UserProgress.user_id == user_id)
            .values(
                total_xp=UserProgress.total_xp + xp_amount,
                level=new_level,
            )
        )
        await self._session.execute(stmt)

    async def update_streak(
        self,
        user_id: uuid.UUID,
        streak_days: int,
        longest_streak: int,
        last_active_date: object,
    ) -> None:
        """Update streak data for a user."""
        stmt = (
            update(UserProgress)
            .where(UserProgress.user_id == user_id)
            .values(
                streak_days=streak_days,
                longest_streak=longest_streak,
                last_active_date=last_active_date,
            )
        )
        await self._session.execute(stmt)

    async def increment_stat(
        self,
        user_id: uuid.UUID,
        field: str,
        amount: int = 1,
    ) -> None:
        """Increment a numeric stat field on UserProgress."""
        allowed_fields = {
            "sessions_completed",
            "quiz_correct_total",
            "topics_explored",
        }
        if field not in allowed_fields:
            raise ValueError(f"Cannot increment field: {field}")

        column = getattr(UserProgress, field)
        stmt = (
            update(UserProgress)
            .where(UserProgress.user_id == user_id)
            .values({field: column + amount})
        )
        await self._session.execute(stmt)

    # ── Achievements ──────────────────────────────────────────────

    async def get_all_achievements(self) -> list[Achievement]:
        """Get all achievement definitions."""
        stmt = select(Achievement).order_by(Achievement.criteria_value)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_achievements(
        self, user_id: uuid.UUID
    ) -> list[UserAchievement]:
        """Get all achievements earned by a user."""
        stmt = select(UserAchievement).where(
            UserAchievement.user_id == user_id
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def award_achievement(
        self,
        user_id: uuid.UUID,
        achievement_id: uuid.UUID,
    ) -> UserAchievement:
        """Award an achievement to a user."""
        user_achievement = UserAchievement(
            user_id=user_id,
            achievement_id=achievement_id,
        )
        self._session.add(user_achievement)
        await self._session.flush()
        logger.info(
            "Achievement awarded",
            extra={
                "user_id": str(user_id),
                "achievement_id": str(achievement_id),
            },
        )
        return user_achievement

    async def has_achievement(
        self,
        user_id: uuid.UUID,
        achievement_id: uuid.UUID,
    ) -> bool:
        """Check if a user already has an achievement."""
        stmt = select(UserAchievement).where(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == achievement_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    # ── Topic Mastery ─────────────────────────────────────────────

    async def get_mastery(
        self, user_id: uuid.UUID, topic: str
    ) -> TopicMastery | None:
        """Get mastery score for a specific topic."""
        stmt = select(TopicMastery).where(
            TopicMastery.user_id == user_id,
            TopicMastery.topic == topic,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_mastery(self, user_id: uuid.UUID) -> list[TopicMastery]:
        """Get all topic mastery records for a user (radar chart data)."""
        stmt = (
            select(TopicMastery)
            .where(TopicMastery.user_id == user_id)
            .order_by(TopicMastery.mastery_score.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_mastery(
        self,
        user_id: uuid.UUID,
        topic: str,
        is_correct: bool,
    ) -> TopicMastery:
        """Update or create topic mastery based on a quiz answer."""
        mastery = await self.get_mastery(user_id, topic)

        if mastery is None:
            mastery = TopicMastery(
                user_id=user_id,
                topic=topic,
                questions_answered=1,
                correct_answers=1 if is_correct else 0,
                mastery_score=100.0 if is_correct else 0.0,
            )
            self._session.add(mastery)
        else:
            mastery.questions_answered += 1
            if is_correct:
                mastery.correct_answers += 1
            mastery.mastery_score = (
                mastery.correct_answers / mastery.questions_answered
            ) * 100

        await self._session.flush()
        return mastery

    # ── Leaderboard ───────────────────────────────────────────────

    async def get_leaderboard(self, limit: int = 50) -> list[dict]:
        """
        Get the top users by XP for the leaderboard.

        Returns minimal public data only (no email).
        """
        stmt = (
            select(
                User.id,
                User.display_name,
                User.avatar_url,
                UserProgress.total_xp,
                UserProgress.level,
            )
            .join(UserProgress, User.id == UserProgress.user_id)
            .order_by(UserProgress.total_xp.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        return [
            {
                "rank": idx + 1,
                "user_id": row.id,
                "display_name": row.display_name,
                "avatar_url": row.avatar_url,
                "total_xp": row.total_xp,
                "level": row.level,
            }
            for idx, row in enumerate(rows)
        ]

    async def get_user_rank(self, user_id: uuid.UUID) -> int | None:
        """Get a user's rank in the global leaderboard."""
        progress = await self.get_progress(user_id)
        if progress is None:
            return None

        from sqlalchemy import func as sqla_func

        stmt = select(sqla_func.count()).select_from(UserProgress).where(
            UserProgress.total_xp > progress.total_xp
        )
        result = await self._session.execute(stmt)
        higher_count = result.scalar_one()
        return higher_count + 1
