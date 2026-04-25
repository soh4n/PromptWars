"""Pydantic schemas for gamification endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class ProgressResponse(BaseModel):
    """User's gamification profile."""

    total_xp: int = 0
    level: int = 1
    streak_days: int = 0
    longest_streak: int = 0
    sessions_completed: int = 0
    quiz_correct_total: int = 0
    topics_explored: int = 0
    xp_to_next_level: int = 0
    level_progress_percent: float = 0.0


class AchievementResponse(BaseModel):
    """Achievement with earned status."""

    id: uuid.UUID
    name: str
    description: str
    icon: str
    xp_reward: int
    is_earned: bool = False
    earned_at: datetime | None = None


class LeaderboardEntry(BaseModel):
    """Single entry in the leaderboard."""

    rank: int
    user_id: uuid.UUID
    display_name: str
    avatar_url: str | None = None
    total_xp: int
    level: int


class LeaderboardResponse(BaseModel):
    """Full leaderboard response."""

    entries: list[LeaderboardEntry]
    current_user_rank: int | None = None


class MasteryResponse(BaseModel):
    """Per-topic mastery for radar chart."""

    topic: str
    mastery_score: float
    questions_answered: int
    correct_answers: int


class XPEvent(BaseModel):
    """XP award event for real-time notifications."""

    amount: int
    reason: str
    new_total: int
    new_level: int
    level_up: bool = False
