"""Pydantic schemas for the learning assistant endpoints."""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class IntentType(StrEnum):
    """Classified user intent types."""

    LEARN = "learn"
    QUIZ = "quiz"
    EXPLAIN = "explain"
    SUMMARIZE = "summarize"
    CLARIFY = "clarify"
    UNKNOWN = "unknown"


class ChatRequest(BaseModel):
    """Request body for the assistant chat endpoint."""

    message: str = Field(min_length=1, max_length=4000)
    session_id: uuid.UUID | None = None
    topic: str | None = None


class ChatResponse(BaseModel):
    """Response from the assistant chat endpoint."""

    message: str
    session_id: uuid.UUID
    intent: str
    xp_earned: int = 0
    achievements_earned: list[str] = []
    difficulty_level: int = 1
    model_used: str = ""


class QuizRequest(BaseModel):
    """Request body for quiz generation."""

    topic: str = Field(min_length=1, max_length=255)
    num_questions: int = Field(default=3, ge=1, le=10)
    session_id: uuid.UUID | None = None


class QuizQuestion(BaseModel):
    """A single quiz question."""

    question: str
    options: list[str]
    correct_index: int
    explanation: str


class QuizResponse(BaseModel):
    """Response containing generated quiz questions."""

    questions: list[QuizQuestion]
    topic: str
    difficulty_level: int
    session_id: uuid.UUID


class EvaluateRequest(BaseModel):
    """Request body for evaluating a quiz answer."""

    session_id: uuid.UUID
    question: str
    user_answer: str
    correct_answer: str
    topic: str


class EvaluateResponse(BaseModel):
    """Response after evaluating a quiz answer."""

    is_correct: bool
    feedback: str
    xp_earned: int = 0
    new_mastery_score: float = 0.0
    achievements_earned: list[str] = []


class SessionResponse(BaseModel):
    """Learning session summary."""

    id: uuid.UUID
    topic: str
    difficulty_level: int
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    message_count: int = 0

    model_config = {"from_attributes": True}


class TopicSuggestion(BaseModel):
    """A suggested topic with reason."""

    topic: str
    reason: str
    estimated_difficulty: int = 1
