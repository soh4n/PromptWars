"""
Gamification Service — XP awards, streaks, achievement checks, leveling.
"""

import uuid
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from api.models.gamification import AchievementCriteria
from api.repositories.gamification_repository import GamificationRepository
from api.services.adaptive_engine import calculate_level
from api.utils.logging import get_logger

logger = get_logger(__name__)


async def award_xp(
    session: AsyncSession, user_id: uuid.UUID, amount: int, reason: str,
) -> dict:
    """Award XP, update level, return event data including level_up flag."""
    repo = GamificationRepository(session)
    progress = await repo.get_progress(user_id)
    if progress is None:
        return {"amount": 0, "reason": reason, "new_total": 0, "new_level": 1, "level_up": False}

    old_level = progress.level
    new_total = progress.total_xp + amount
    new_level = calculate_level(new_total)
    level_up = new_level > old_level

    await repo.update_xp(user_id, amount, new_level)

    if level_up:
        logger.info("Level up!", extra={"user_id": str(user_id), "new_level": new_level})

    return {
        "amount": amount, "reason": reason,
        "new_total": new_total, "new_level": new_level, "level_up": level_up,
    }


async def update_streak(session: AsyncSession, user_id: uuid.UUID) -> int:
    """Update daily streak. Returns current streak count."""
    repo = GamificationRepository(session)
    progress = await repo.get_progress(user_id)
    if progress is None:
        return 0

    today = date.today()

    if progress.last_active_date == today:
        return progress.streak_days

    if progress.last_active_date == today - timedelta(days=1):
        new_streak = progress.streak_days + 1
    elif progress.last_active_date == today - timedelta(days=2):
        # Grace period: 1 day missed keeps streak alive but doesn't increment
        new_streak = progress.streak_days
    else:
        new_streak = 1

    longest = max(progress.longest_streak, new_streak)
    await repo.update_streak(user_id, new_streak, longest, today)
    return new_streak


async def check_achievements(
    session: AsyncSession, user_id: uuid.UUID,
) -> list[str]:
    """Check and award any newly earned achievements. Returns list of earned names."""
    repo = GamificationRepository(session)
    progress = await repo.get_progress(user_id)
    if progress is None:
        return []

    all_achievements = await repo.get_all_achievements()
    earned_names: list[str] = []

    for achievement in all_achievements:
        already_earned = await repo.has_achievement(user_id, achievement.id)
        if already_earned:
            continue

        criteria_met = _check_criteria(achievement.criteria_type, achievement.criteria_value, progress)
        if criteria_met:
            await repo.award_achievement(user_id, achievement.id)
            if achievement.xp_reward > 0:
                await award_xp(session, user_id, achievement.xp_reward, f"achievement:{achievement.name}")
            earned_names.append(achievement.name)

    return earned_names


def _check_criteria(criteria_type: str, criteria_value: int, progress: object) -> bool:
    """Check if a user meets an achievement's criteria."""
    checks = {
        AchievementCriteria.SESSIONS_COMPLETED: lambda: progress.sessions_completed >= criteria_value,
        AchievementCriteria.STREAK_DAYS: lambda: progress.streak_days >= criteria_value,
        AchievementCriteria.TOTAL_XP: lambda: progress.total_xp >= criteria_value,
        AchievementCriteria.QUIZ_CORRECT: lambda: progress.quiz_correct_total >= criteria_value,
        AchievementCriteria.LEVEL_REACHED: lambda: progress.level >= criteria_value,
        AchievementCriteria.TOPICS_EXPLORED: lambda: progress.topics_explored >= criteria_value,
        AchievementCriteria.FIRST_LESSON: lambda: progress.sessions_completed >= 1,
    }
    check_fn = checks.get(criteria_type)
    return check_fn() if check_fn else False
