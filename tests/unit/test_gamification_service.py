"""
Unit tests for Gamification Service — XP awards, streaks, achievement checks.

Covers:
  - XP awarding and level-up detection
  - Streak calculation (consecutive, grace period, reset)
  - Achievement criteria evaluation for all criteria types
"""

import uuid
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.models.gamification import AchievementCriteria
from api.services.gamification_service import (
    award_xp,
    update_streak,
    check_achievements,
    _check_criteria,
)


TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _make_progress(
    total_xp: int = 500, level: int = 3, streak: int = 5,
    longest: int = 10, last_active: date | None = None,
    sessions: int = 10, quiz_correct: int = 25, topics: int = 4,
):
    """Build a mock UserProgress."""
    progress = MagicMock()
    progress.user_id = TEST_USER_ID
    progress.total_xp = total_xp
    progress.level = level
    progress.streak_days = streak
    progress.longest_streak = longest
    progress.last_active_date = last_active or date.today()
    progress.sessions_completed = sessions
    progress.quiz_correct_total = quiz_correct
    progress.topics_explored = topics
    return progress


class TestAwardXp:
    """Tests for award_xp() function."""

    @pytest.mark.asyncio
    @patch("api.services.gamification_service.GamificationRepository")
    async def test_basic_xp_award(self, MockRepo):
        """Award XP and verify total increases."""
        progress = _make_progress(total_xp=500, level=3)
        MockRepo.return_value.get_progress = AsyncMock(return_value=progress)
        MockRepo.return_value.update_xp = AsyncMock()

        result = await award_xp(AsyncMock(), TEST_USER_ID, 25, "quiz_correct")

        assert result["amount"] == 25
        assert result["new_total"] == 525
        assert result["level_up"] is False

    @pytest.mark.asyncio
    @patch("api.services.gamification_service.GamificationRepository")
    async def test_level_up_detection(self, MockRepo):
        """XP crossing level boundary triggers level_up = True."""
        progress = _make_progress(total_xp=380, level=3)  # Level 3, needs 400 for level 3
        MockRepo.return_value.get_progress = AsyncMock(return_value=progress)
        MockRepo.return_value.update_xp = AsyncMock()

        result = await award_xp(AsyncMock(), TEST_USER_ID, 50, "session_complete")

        assert result["new_total"] == 430
        assert result["level_up"] is True
        assert result["new_level"] > 3

    @pytest.mark.asyncio
    @patch("api.services.gamification_service.GamificationRepository")
    async def test_no_level_up_same_level(self, MockRepo):
        """Small XP award within same level → level_up = False."""
        progress = _make_progress(total_xp=110, level=2)
        MockRepo.return_value.get_progress = AsyncMock(return_value=progress)
        MockRepo.return_value.update_xp = AsyncMock()

        result = await award_xp(AsyncMock(), TEST_USER_ID, 10, "message")

        assert result["level_up"] is False
        assert result["new_level"] == 2

    @pytest.mark.asyncio
    @patch("api.services.gamification_service.GamificationRepository")
    async def test_no_progress_record(self, MockRepo):
        """No UserProgress → returns zero values."""
        MockRepo.return_value.get_progress = AsyncMock(return_value=None)

        result = await award_xp(AsyncMock(), TEST_USER_ID, 10, "message")

        assert result["amount"] == 0
        assert result["new_total"] == 0
        assert result["level_up"] is False


class TestUpdateStreak:
    """Tests for daily streak logic."""

    @pytest.mark.asyncio
    @patch("api.services.gamification_service.GamificationRepository")
    async def test_consecutive_day_increments(self, MockRepo):
        """Active yesterday → streak +1."""
        progress = _make_progress(
            streak=5, longest=10,
            last_active=date.today() - timedelta(days=1),
        )
        MockRepo.return_value.get_progress = AsyncMock(return_value=progress)
        MockRepo.return_value.update_streak = AsyncMock()

        result = await update_streak(AsyncMock(), TEST_USER_ID)

        assert result == 6

    @pytest.mark.asyncio
    @patch("api.services.gamification_service.GamificationRepository")
    async def test_same_day_no_change(self, MockRepo):
        """Already active today → streak unchanged."""
        progress = _make_progress(streak=5, last_active=date.today())
        MockRepo.return_value.get_progress = AsyncMock(return_value=progress)

        result = await update_streak(AsyncMock(), TEST_USER_ID)

        assert result == 5

    @pytest.mark.asyncio
    @patch("api.services.gamification_service.GamificationRepository")
    async def test_grace_period_one_day_missed(self, MockRepo):
        """Missed 1 day (grace period) → streak maintained but not incremented."""
        progress = _make_progress(
            streak=7, longest=10,
            last_active=date.today() - timedelta(days=2),
        )
        MockRepo.return_value.get_progress = AsyncMock(return_value=progress)
        MockRepo.return_value.update_streak = AsyncMock()

        result = await update_streak(AsyncMock(), TEST_USER_ID)

        assert result == 7  # Grace: maintains but doesn't increment

    @pytest.mark.asyncio
    @patch("api.services.gamification_service.GamificationRepository")
    async def test_streak_reset_after_two_days_missed(self, MockRepo):
        """Missed 2+ days → streak resets to 1."""
        progress = _make_progress(
            streak=15, longest=20,
            last_active=date.today() - timedelta(days=3),
        )
        MockRepo.return_value.get_progress = AsyncMock(return_value=progress)
        MockRepo.return_value.update_streak = AsyncMock()

        result = await update_streak(AsyncMock(), TEST_USER_ID)

        assert result == 1

    @pytest.mark.asyncio
    @patch("api.services.gamification_service.GamificationRepository")
    async def test_no_progress_returns_zero(self, MockRepo):
        """No UserProgress → streak = 0."""
        MockRepo.return_value.get_progress = AsyncMock(return_value=None)

        result = await update_streak(AsyncMock(), TEST_USER_ID)

        assert result == 0

    @pytest.mark.asyncio
    @patch("api.services.gamification_service.GamificationRepository")
    async def test_longest_streak_updated(self, MockRepo):
        """New streak exceeds longest → longest updated."""
        progress = _make_progress(
            streak=10, longest=10,
            last_active=date.today() - timedelta(days=1),
        )
        MockRepo.return_value.get_progress = AsyncMock(return_value=progress)
        MockRepo.return_value.update_streak = AsyncMock()

        await update_streak(AsyncMock(), TEST_USER_ID)

        call_args = MockRepo.return_value.update_streak.call_args
        assert call_args[0][2] == 11  # longest = max(10, 11) = 11


class TestCheckCriteria:
    """Tests for _check_criteria() — individual achievement criteria evaluation."""

    def test_sessions_completed_met(self):
        """Sessions completed >= threshold → True."""
        progress = _make_progress(sessions=10)
        assert _check_criteria(AchievementCriteria.SESSIONS_COMPLETED, 10, progress) is True

    def test_sessions_completed_not_met(self):
        """Sessions completed < threshold → False."""
        progress = _make_progress(sessions=5)
        assert _check_criteria(AchievementCriteria.SESSIONS_COMPLETED, 10, progress) is False

    def test_streak_days_met(self):
        """Streak days >= threshold → True."""
        progress = _make_progress(streak=7)
        assert _check_criteria(AchievementCriteria.STREAK_DAYS, 7, progress) is True

    def test_total_xp_met(self):
        """Total XP >= threshold → True."""
        progress = _make_progress(total_xp=1000)
        assert _check_criteria(AchievementCriteria.TOTAL_XP, 500, progress) is True

    def test_quiz_correct_met(self):
        """Quiz correct >= threshold → True."""
        progress = _make_progress(quiz_correct=50)
        assert _check_criteria(AchievementCriteria.QUIZ_CORRECT, 25, progress) is True

    def test_level_reached_met(self):
        """Level >= threshold → True."""
        progress = _make_progress(level=5)
        assert _check_criteria(AchievementCriteria.LEVEL_REACHED, 5, progress) is True

    def test_topics_explored_met(self):
        """Topics explored >= threshold → True."""
        progress = _make_progress(topics=10)
        assert _check_criteria(AchievementCriteria.TOPICS_EXPLORED, 5, progress) is True

    def test_first_lesson_met(self):
        """First lesson = sessions_completed >= 1 → True."""
        progress = _make_progress(sessions=1)
        assert _check_criteria(AchievementCriteria.FIRST_LESSON, 1, progress) is True

    def test_first_lesson_not_met(self):
        """No sessions → first lesson not met."""
        progress = _make_progress(sessions=0)
        assert _check_criteria(AchievementCriteria.FIRST_LESSON, 1, progress) is False

    def test_unknown_criteria_returns_false(self):
        """Unknown criteria type → False."""
        progress = _make_progress()
        assert _check_criteria("nonexistent_criteria", 1, progress) is False
