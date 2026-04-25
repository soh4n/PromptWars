"""Gamification router — profile, achievements, leaderboard, mastery."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.session import get_db
from api.repositories.gamification_repository import GamificationRepository
from api.repositories.user_repository import UserRepository
from api.schemas.gamification import (
    AchievementResponse, LeaderboardEntry, LeaderboardResponse,
    MasteryResponse, ProgressResponse,
)
from api.services.adaptive_engine import xp_to_next_level
from api.utils.auth import FirebaseUser, get_current_user

router = APIRouter(prefix="/gamification", tags=["Gamification"])


@router.get("/profile", response_model=ProgressResponse)
async def get_profile(
    firebase_user: Annotated[FirebaseUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProgressResponse:
    """Get the current user's gamification profile."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_firebase_uid(firebase_user.uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    repo = GamificationRepository(db)
    progress = await repo.get_progress(user.id)
    if not progress:
        return ProgressResponse()

    remaining, percent = xp_to_next_level(progress.total_xp)
    return ProgressResponse(
        total_xp=progress.total_xp, level=progress.level,
        streak_days=progress.streak_days, longest_streak=progress.longest_streak,
        sessions_completed=progress.sessions_completed,
        quiz_correct_total=progress.quiz_correct_total,
        topics_explored=progress.topics_explored,
        xp_to_next_level=remaining, level_progress_percent=round(percent, 1),
    )


@router.get("/achievements", response_model=list[AchievementResponse])
async def get_achievements(
    firebase_user: Annotated[FirebaseUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AchievementResponse]:
    """Get all achievements with earned status for the current user."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_firebase_uid(firebase_user.uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    repo = GamificationRepository(db)
    all_achievements = await repo.get_all_achievements()
    user_achievements = await repo.get_user_achievements(user.id)
    earned_map = {ua.achievement_id: ua.earned_at for ua in user_achievements}

    return [
        AchievementResponse(
            id=a.id, name=a.name, description=a.description,
            icon=a.icon, xp_reward=a.xp_reward,
            is_earned=a.id in earned_map,
            earned_at=earned_map.get(a.id),
        )
        for a in all_achievements if not a.is_hidden or a.id in earned_map
    ]


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    firebase_user: Annotated[FirebaseUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
) -> LeaderboardResponse:
    """Get the global XP leaderboard."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_firebase_uid(firebase_user.uid)

    repo = GamificationRepository(db)
    entries_data = await repo.get_leaderboard(limit)
    entries = [LeaderboardEntry(**e) for e in entries_data]

    user_rank = await repo.get_user_rank(user.id) if user else None

    return LeaderboardResponse(entries=entries, current_user_rank=user_rank)


@router.get("/mastery", response_model=list[MasteryResponse])
async def get_mastery(
    firebase_user: Annotated[FirebaseUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MasteryResponse]:
    """Get per-topic mastery scores for the radar chart."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_firebase_uid(firebase_user.uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    repo = GamificationRepository(db)
    masteries = await repo.get_all_mastery(user.id)

    return [
        MasteryResponse(
            topic=m.topic, mastery_score=m.mastery_score,
            questions_answered=m.questions_answered,
            correct_answers=m.correct_answers,
        )
        for m in masteries
    ]
