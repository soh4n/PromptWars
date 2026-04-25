"""Sessions router — CRUD for learning sessions."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.session import get_db
from api.repositories.session_repository import SessionRepository
from api.repositories.user_repository import UserRepository
from api.schemas.assistant import SessionResponse
from api.utils.auth import FirebaseUser, get_current_user

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    firebase_user: Annotated[FirebaseUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 20, offset: int = 0,
) -> list[SessionResponse]:
    """List user's learning sessions, newest first."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_firebase_uid(firebase_user.uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    session_repo = SessionRepository(db)
    sessions = await session_repo.list_sessions(user.id, limit, offset)

    result = []
    for s in sessions:
        count = await session_repo.get_message_count(s.id)
        result.append(SessionResponse(
            id=s.id, topic=s.topic, difficulty_level=s.difficulty_level,
            status=s.status, started_at=s.started_at, ended_at=s.ended_at,
            message_count=count,
        ))
    return result


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_session(
    session_id: str,
    firebase_user: Annotated[FirebaseUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """End/archive a learning session."""
    import uuid
    user_repo = UserRepository(db)
    user = await user_repo.get_by_firebase_uid(firebase_user.uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    session_repo = SessionRepository(db)
    await session_repo.end_session(uuid.UUID(session_id), user.id)
