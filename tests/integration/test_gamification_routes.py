"""
Integration tests for Gamification routes — profile, achievements, leaderboard, mastery.

Tests:
  - GET /gamification/profile → returns progress
  - GET /gamification/achievements → returns earned/locked list
  - GET /gamification/leaderboard → ranked entries
  - GET /gamification/mastery → per-topic scores
  - Unauthenticated access (handled by conftest override)
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_achievement(name: str = "First Lesson", is_hidden: bool = False):
    """Build a mock Achievement."""
    a = MagicMock()
    a.id = uuid.uuid4()
    a.name = name
    a.description = f"Complete your {name.lower()}"
    a.icon = "star"
    a.xp_reward = 50
    a.is_hidden = is_hidden
    return a


def _make_user_achievement(achievement_id):
    """Build a mock UserAchievement."""
    ua = MagicMock()
    ua.achievement_id = achievement_id
    ua.earned_at = datetime(2025, 6, 15)
    return ua


class TestGetProfile:
    """GET /gamification/profile integration tests."""

    @patch("api.routers.gamification.GamificationRepository")
    @patch("api.routers.gamification.UserRepository")
    def test_profile_success(self, MockUserRepo, MockGamRepo, test_client, mock_user, mock_progress):
        """Authenticated user → 200 with full progress data."""
        MockUserRepo.return_value.get_by_firebase_uid = AsyncMock(return_value=mock_user)
        MockGamRepo.return_value.get_progress = AsyncMock(return_value=mock_progress)

        response = test_client.get("/gamification/profile")

        assert response.status_code == 200
        data = response.json()
        assert data["total_xp"] == 500
        assert data["level"] == 3
        assert data["streak_days"] == 5
        assert data["sessions_completed"] == 10

    @patch("api.routers.gamification.GamificationRepository")
    @patch("api.routers.gamification.UserRepository")
    def test_profile_no_progress(self, MockUserRepo, MockGamRepo, test_client, mock_user):
        """New user with no progress → returns defaults."""
        MockUserRepo.return_value.get_by_firebase_uid = AsyncMock(return_value=mock_user)
        MockGamRepo.return_value.get_progress = AsyncMock(return_value=None)

        response = test_client.get("/gamification/profile")

        assert response.status_code == 200
        data = response.json()
        assert data["total_xp"] == 0
        assert data["level"] == 1

    @patch("api.routers.gamification.UserRepository")
    def test_profile_user_not_found(self, MockUserRepo, test_client):
        """Auth valid but no user → 404."""
        MockUserRepo.return_value.get_by_firebase_uid = AsyncMock(return_value=None)

        response = test_client.get("/gamification/profile")

        assert response.status_code == 404


class TestGetAchievements:
    """GET /gamification/achievements integration tests."""

    @patch("api.routers.gamification.GamificationRepository")
    @patch("api.routers.gamification.UserRepository")
    def test_achievements_with_earned(self, MockUserRepo, MockGamRepo, test_client, mock_user):
        """Returns achievements with earned status marked."""
        a1 = _make_achievement("First Lesson")
        a2 = _make_achievement("Quiz Master")
        ua1 = _make_user_achievement(a1.id)

        MockUserRepo.return_value.get_by_firebase_uid = AsyncMock(return_value=mock_user)
        MockGamRepo.return_value.get_all_achievements = AsyncMock(return_value=[a1, a2])
        MockGamRepo.return_value.get_user_achievements = AsyncMock(return_value=[ua1])

        response = test_client.get("/gamification/achievements")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        earned_names = [a["name"] for a in data if a["is_earned"]]
        assert "First Lesson" in earned_names

    @patch("api.routers.gamification.GamificationRepository")
    @patch("api.routers.gamification.UserRepository")
    def test_hidden_achievements_filtered(self, MockUserRepo, MockGamRepo, test_client, mock_user):
        """Hidden achievements not yet earned are excluded."""
        visible = _make_achievement("Visible", is_hidden=False)
        hidden = _make_achievement("Secret", is_hidden=True)

        MockUserRepo.return_value.get_by_firebase_uid = AsyncMock(return_value=mock_user)
        MockGamRepo.return_value.get_all_achievements = AsyncMock(return_value=[visible, hidden])
        MockGamRepo.return_value.get_user_achievements = AsyncMock(return_value=[])

        response = test_client.get("/gamification/achievements")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Visible"


class TestGetLeaderboard:
    """GET /gamification/leaderboard integration tests."""

    @patch("api.routers.gamification.GamificationRepository")
    @patch("api.routers.gamification.UserRepository")
    def test_leaderboard_success(self, MockUserRepo, MockGamRepo, test_client, mock_user):
        """Returns ranked leaderboard entries."""
        entries = [
            {"rank": 1, "display_name": "TopLearner", "total_xp": 5000, "level": 8, "avatar_url": None},
            {"rank": 2, "display_name": "Test User", "total_xp": 500, "level": 3, "avatar_url": None},
        ]
        MockUserRepo.return_value.get_by_firebase_uid = AsyncMock(return_value=mock_user)
        MockGamRepo.return_value.get_leaderboard = AsyncMock(return_value=entries)
        MockGamRepo.return_value.get_user_rank = AsyncMock(return_value=2)

        response = test_client.get("/gamification/leaderboard")

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 2
        assert data["current_user_rank"] == 2
        assert data["entries"][0]["rank"] == 1

    @patch("api.routers.gamification.GamificationRepository")
    @patch("api.routers.gamification.UserRepository")
    def test_leaderboard_empty(self, MockUserRepo, MockGamRepo, test_client, mock_user):
        """No users → empty leaderboard."""
        MockUserRepo.return_value.get_by_firebase_uid = AsyncMock(return_value=mock_user)
        MockGamRepo.return_value.get_leaderboard = AsyncMock(return_value=[])
        MockGamRepo.return_value.get_user_rank = AsyncMock(return_value=None)

        response = test_client.get("/gamification/leaderboard")

        assert response.status_code == 200
        assert response.json()["entries"] == []


class TestGetMastery:
    """GET /gamification/mastery integration tests."""

    @patch("api.routers.gamification.GamificationRepository")
    @patch("api.routers.gamification.UserRepository")
    def test_mastery_success(self, MockUserRepo, MockGamRepo, test_client, mock_user, mock_mastery):
        """Returns per-topic mastery scores."""
        MockUserRepo.return_value.get_by_firebase_uid = AsyncMock(return_value=mock_user)
        MockGamRepo.return_value.get_all_mastery = AsyncMock(return_value=[mock_mastery])

        response = test_client.get("/gamification/mastery")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["topic"] == "Python"
        assert data[0]["mastery_score"] == 75.0

    @patch("api.routers.gamification.GamificationRepository")
    @patch("api.routers.gamification.UserRepository")
    def test_mastery_empty(self, MockUserRepo, MockGamRepo, test_client, mock_user):
        """No mastery data → empty list."""
        MockUserRepo.return_value.get_by_firebase_uid = AsyncMock(return_value=mock_user)
        MockGamRepo.return_value.get_all_mastery = AsyncMock(return_value=[])

        response = test_client.get("/gamification/mastery")

        assert response.status_code == 200
        assert response.json() == []
