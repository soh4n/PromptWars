"""
Adaptive Engine — adjusts difficulty and content based on user performance.
"""

import math
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.gamification_repository import GamificationRepository
from api.utils.logging import get_logger

logger = get_logger(__name__)

MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 5
PROMOTE_THRESHOLD = 0.80
DEMOTE_THRESHOLD = 0.40
MIN_ANSWERS_FOR_ADJUSTMENT = 3


async def calculate_difficulty(
    session: AsyncSession, user_id: uuid.UUID, topic: str, current_difficulty: int,
) -> int:
    """Calculate difficulty level based on user mastery accuracy."""
    repo = GamificationRepository(session)
    mastery = await repo.get_mastery(user_id, topic)

    if mastery is None or mastery.questions_answered < MIN_ANSWERS_FOR_ADJUSTMENT:
        return current_difficulty

    accuracy = mastery.correct_answers / mastery.questions_answered
    new_difficulty = current_difficulty

    if accuracy >= PROMOTE_THRESHOLD:
        new_difficulty = min(current_difficulty + 1, MAX_DIFFICULTY)
    elif accuracy <= DEMOTE_THRESHOLD:
        new_difficulty = max(current_difficulty - 1, MIN_DIFFICULTY)

    if new_difficulty != current_difficulty:
        logger.info("Difficulty adjusted", extra={
            "user_id": str(user_id), "topic": topic,
            "accuracy": round(accuracy, 2),
            "old": current_difficulty, "new": new_difficulty,
        })
    return new_difficulty


def get_xp_for_action(action: str, difficulty: int = 1) -> int:
    """Calculate XP reward for an action, scaled by difficulty."""
    base_xp = {
        "message": 10, "quiz_correct": 25, "quiz_incorrect": 5,
        "session_complete": 50, "daily_login": 5, "topic_milestone": 100,
    }
    xp = base_xp.get(action, 5)
    multiplier = 1.0 + (difficulty - 1) * 0.25
    return int(xp * multiplier)


def calculate_level(total_xp: int) -> int:
    """Level = floor(sqrt(totalXP / 100)) + 1."""
    return max(1, int(math.sqrt(max(0, total_xp) / 100)) + 1)


def xp_for_level(level: int) -> int:
    """Total XP required to reach a given level."""
    return ((level - 1) ** 2) * 100


def xp_to_next_level(total_xp: int) -> tuple[int, float]:
    """Returns (xp_remaining, progress_percent) to next level."""
    current_level = calculate_level(total_xp)
    current_level_xp = xp_for_level(current_level)
    next_level_xp = xp_for_level(current_level + 1)
    xp_in_level = total_xp - current_level_xp
    xp_needed = next_level_xp - current_level_xp
    if xp_needed <= 0:
        return 0, 100.0
    progress = (xp_in_level / xp_needed) * 100
    return next_level_xp - total_xp, min(progress, 100.0)
