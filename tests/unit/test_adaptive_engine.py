"""
Unit tests for Adaptive Engine — difficulty scaling, XP calculation, leveling.

Covers:
  - XP calculation with difficulty multipliers
  - Level computation formula (sqrt-based)
  - XP-to-next-level progress tracking
  - Difficulty adjustment thresholds
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from api.services.adaptive_engine import (
    get_xp_for_action,
    calculate_level,
    xp_for_level,
    xp_to_next_level,
    calculate_difficulty,
    MIN_DIFFICULTY,
    MAX_DIFFICULTY,
    PROMOTE_THRESHOLD,
    DEMOTE_THRESHOLD,
)


class TestGetXpForAction:
    """Tests for XP calculation logic."""

    def test_message_base_xp(self):
        """Base message XP at difficulty 1 = 10."""
        assert get_xp_for_action("message", 1) == 10

    def test_message_xp_difficulty_3(self):
        """Message XP at difficulty 3 = 10 * 1.5 = 15."""
        assert get_xp_for_action("message", 3) == 15

    def test_quiz_correct_base_xp(self):
        """Quiz correct at difficulty 1 = 25."""
        assert get_xp_for_action("quiz_correct", 1) == 25

    def test_quiz_correct_difficulty_5(self):
        """Quiz correct at difficulty 5 = 25 * 2.0 = 50."""
        assert get_xp_for_action("quiz_correct", 5) == 50

    def test_quiz_incorrect_xp(self):
        """Quiz incorrect = 5 * multiplier."""
        assert get_xp_for_action("quiz_incorrect", 1) == 5
        assert get_xp_for_action("quiz_incorrect", 3) == 7  # 5 * 1.5 = 7.5 → 7

    def test_session_complete_xp(self):
        """Session complete = 50 base."""
        assert get_xp_for_action("session_complete", 1) == 50
        assert get_xp_for_action("session_complete", 5) == 100  # 50 * 2.0

    def test_daily_login_xp(self):
        """Daily login = 5 base."""
        assert get_xp_for_action("daily_login", 1) == 5

    def test_topic_milestone_xp(self):
        """Topic milestone = 100 base."""
        assert get_xp_for_action("topic_milestone", 1) == 100

    def test_unknown_action_default_xp(self):
        """Unknown action → 5 XP default."""
        assert get_xp_for_action("some_random_action", 1) == 5

    def test_difficulty_multiplier_formula(self):
        """Multiplier = 1.0 + (difficulty - 1) * 0.25."""
        # Difficulty 1 → 1.0x, 2 → 1.25x, 3 → 1.5x, 4 → 1.75x, 5 → 2.0x
        assert get_xp_for_action("message", 2) == 12  # 10 * 1.25
        assert get_xp_for_action("message", 4) == 17  # 10 * 1.75


class TestCalculateLevel:
    """Tests for level computation: Level = floor(sqrt(totalXP / 100)) + 1."""

    def test_zero_xp(self):
        """0 XP = Level 1."""
        assert calculate_level(0) == 1

    def test_99_xp(self):
        """99 XP = Level 1 (sqrt(0.99) < 1)."""
        assert calculate_level(99) == 1

    def test_100_xp(self):
        """100 XP = Level 2 (sqrt(1) = 1, + 1 = 2)."""
        assert calculate_level(100) == 2

    def test_400_xp(self):
        """400 XP = Level 3 (sqrt(4) = 2, + 1 = 3)."""
        assert calculate_level(400) == 3

    def test_2500_xp(self):
        """2500 XP = Level 6 (sqrt(25) = 5, + 1 = 6)."""
        assert calculate_level(2500) == 6

    def test_10000_xp(self):
        """10000 XP = Level 11 (sqrt(100) = 10, + 1 = 11)."""
        assert calculate_level(10000) == 11

    def test_negative_xp_clamps(self):
        """Negative XP → Level 1 (minimum)."""
        assert calculate_level(-100) == 1


class TestXpForLevel:
    """Tests for total XP required to reach a level."""

    def test_level_1(self):
        """Level 1 requires 0 XP."""
        assert xp_for_level(1) == 0

    def test_level_2(self):
        """Level 2 requires 100 XP."""
        assert xp_for_level(2) == 100

    def test_level_3(self):
        """Level 3 requires 400 XP."""
        assert xp_for_level(3) == 400

    def test_level_5(self):
        """Level 5 requires 1600 XP."""
        assert xp_for_level(5) == 1600


class TestXpToNextLevel:
    """Tests for XP remaining and progress percentage."""

    def test_at_level_start(self):
        """Exactly at level 2 start (100 XP): remaining to level 3 = 300, progress = 0%."""
        remaining, percent = xp_to_next_level(100)
        assert remaining == 300
        assert percent == 0.0

    def test_mid_level(self):
        """250 XP is halfway between level 2 (100) and level 3 (400)."""
        remaining, percent = xp_to_next_level(250)
        assert remaining == 150
        assert percent == 50.0

    def test_zero_xp(self):
        """0 XP → Level 1, progress toward level 2 = 0%."""
        remaining, percent = xp_to_next_level(0)
        assert remaining == 100
        assert percent == 0.0


class TestCalculateDifficulty:
    """Tests for adaptive difficulty adjustment based on mastery."""

    @pytest.mark.asyncio
    @patch("api.services.adaptive_engine.GamificationRepository")
    async def test_promote_on_high_accuracy(self, MockRepo):
        """>=80% accuracy → difficulty +1."""
        mastery = MagicMock()
        mastery.questions_answered = 10
        mastery.correct_answers = 9  # 90%
        MockRepo.return_value.get_mastery = AsyncMock(return_value=mastery)

        import uuid
        result = await calculate_difficulty(AsyncMock(), uuid.uuid4(), "Python", 2)
        assert result == 3

    @pytest.mark.asyncio
    @patch("api.services.adaptive_engine.GamificationRepository")
    async def test_demote_on_low_accuracy(self, MockRepo):
        """<=40% accuracy → difficulty -1."""
        mastery = MagicMock()
        mastery.questions_answered = 10
        mastery.correct_answers = 3  # 30%
        MockRepo.return_value.get_mastery = AsyncMock(return_value=mastery)

        import uuid
        result = await calculate_difficulty(AsyncMock(), uuid.uuid4(), "Math", 3)
        assert result == 2

    @pytest.mark.asyncio
    @patch("api.services.adaptive_engine.GamificationRepository")
    async def test_no_change_medium_accuracy(self, MockRepo):
        """41-79% accuracy → no change."""
        mastery = MagicMock()
        mastery.questions_answered = 10
        mastery.correct_answers = 6  # 60%
        MockRepo.return_value.get_mastery = AsyncMock(return_value=mastery)

        import uuid
        result = await calculate_difficulty(AsyncMock(), uuid.uuid4(), "Science", 3)
        assert result == 3

    @pytest.mark.asyncio
    @patch("api.services.adaptive_engine.GamificationRepository")
    async def test_no_change_insufficient_data(self, MockRepo):
        """Fewer than 3 answers → no adjustment."""
        mastery = MagicMock()
        mastery.questions_answered = 2
        mastery.correct_answers = 2
        MockRepo.return_value.get_mastery = AsyncMock(return_value=mastery)

        import uuid
        result = await calculate_difficulty(AsyncMock(), uuid.uuid4(), "Art", 2)
        assert result == 2

    @pytest.mark.asyncio
    @patch("api.services.adaptive_engine.GamificationRepository")
    async def test_no_mastery_record(self, MockRepo):
        """No mastery record → keep current difficulty."""
        MockRepo.return_value.get_mastery = AsyncMock(return_value=None)

        import uuid
        result = await calculate_difficulty(AsyncMock(), uuid.uuid4(), "Music", 3)
        assert result == 3

    @pytest.mark.asyncio
    @patch("api.services.adaptive_engine.GamificationRepository")
    async def test_clamp_at_max_difficulty(self, MockRepo):
        """Cannot exceed MAX_DIFFICULTY (5)."""
        mastery = MagicMock()
        mastery.questions_answered = 10
        mastery.correct_answers = 10
        MockRepo.return_value.get_mastery = AsyncMock(return_value=mastery)

        import uuid
        result = await calculate_difficulty(AsyncMock(), uuid.uuid4(), "Expert", MAX_DIFFICULTY)
        assert result == MAX_DIFFICULTY

    @pytest.mark.asyncio
    @patch("api.services.adaptive_engine.GamificationRepository")
    async def test_clamp_at_min_difficulty(self, MockRepo):
        """Cannot go below MIN_DIFFICULTY (1)."""
        mastery = MagicMock()
        mastery.questions_answered = 10
        mastery.correct_answers = 1  # 10%
        MockRepo.return_value.get_mastery = AsyncMock(return_value=mastery)

        import uuid
        result = await calculate_difficulty(AsyncMock(), uuid.uuid4(), "Beginner", MIN_DIFFICULTY)
        assert result == MIN_DIFFICULTY
