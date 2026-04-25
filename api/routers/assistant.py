"""
Assistant router — core learning chat, quiz generation, and answer evaluation.

Implements the full Context Pipeline on every request:
  Classify → Enrich → Construct → Infer → Validate → Respond → Audit
"""

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.session import get_db
from api.repositories.gamification_repository import GamificationRepository
from api.repositories.session_repository import SessionRepository
from api.repositories.user_repository import UserRepository
from api.schemas.assistant import (
    ChatRequest, ChatResponse, EvaluateRequest, EvaluateResponse,
    QuizRequest, QuizResponse, QuizQuestion,
)
from api.services.adaptive_engine import calculate_difficulty, get_xp_for_action
from api.services.audit_service import log_inference
from api.services.context_service import build_enriched_context
from api.services.gamification_service import award_xp, check_achievements, update_streak
from api.services.gemini_service import generate_response
from api.services.intent_service import classify_intent
from api.utils.auth import FirebaseUser, get_current_user
from api.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/assistant", tags=["Learning Assistant"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    firebase_user: Annotated[FirebaseUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatResponse:
    """
    Main learning endpoint — processes user message through the full context pipeline.

    Steps: Classify intent → Enrich context → Generate response → Award XP → Audit
    """
    start_time = time.time()

    # Get local user
    user_repo = UserRepository(db)
    user = await user_repo.get_by_firebase_uid(firebase_user.uid)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    session_repo = SessionRepository(db)

    # Get or create learning session
    if request.session_id:
        learning_session = await session_repo.get_session(request.session_id, user.id)
        if learning_session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    else:
        topic = request.topic or "General Learning"
        learning_session = await session_repo.create_session(user.id, topic)
        await update_streak(db, user.id)

    # Step 1: Classify intent
    intent_result = await classify_intent(request.message, learning_session.topic)

    # Step 2-3: Enrich context + Build prompt
    context = await build_enriched_context(
        db, user.id, learning_session.id,
        learning_session.topic, learning_session.difficulty_level,
    )

    # Step 4: Gemini inference
    gemini_response = await generate_response(
        system_prompt=context["system_prompt"],
        user_message=request.message,
        conversation_history=context["conversation_history"],
        use_cache=False,
    )

    # Step 5: Save messages
    await session_repo.add_message(learning_session.id, "user", request.message)
    await session_repo.add_message(
        learning_session.id, "assistant", gemini_response.text,
        token_count=gemini_response.output_tokens,
    )

    # Step 6: Award XP + check achievements
    xp_amount = get_xp_for_action("message", learning_session.difficulty_level)
    xp_event = await award_xp(db, user.id, xp_amount, "chat_message")
    earned = await check_achievements(db, user.id)

    # Step 7: Adapt difficulty
    new_difficulty = await calculate_difficulty(
        db, user.id, learning_session.topic, learning_session.difficulty_level,
    )

    # Audit log
    latency_ms = (time.time() - start_time) * 1000
    log_inference(str(user.id), gemini_response.model, intent_result["intent"],
                  gemini_response.input_tokens, gemini_response.output_tokens, latency_ms)

    return ChatResponse(
        message=gemini_response.text, session_id=learning_session.id,
        intent=intent_result["intent"], xp_earned=xp_amount,
        achievements_earned=earned, difficulty_level=new_difficulty,
        model_used=gemini_response.model,
    )


@router.post("/quiz", response_model=QuizResponse)
async def generate_quiz(
    request: QuizRequest,
    firebase_user: Annotated[FirebaseUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuizResponse:
    """Generate quiz questions on a topic at the user's difficulty level."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_firebase_uid(firebase_user.uid)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    session_repo = SessionRepository(db)

    if request.session_id:
        learning_session = await session_repo.get_session(request.session_id, user.id)
        if learning_session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        difficulty = learning_session.difficulty_level
    else:
        learning_session = await session_repo.create_session(user.id, request.topic)
        difficulty = 1

    quiz_prompt = f"""Generate exactly {request.num_questions} multiple-choice quiz questions about "{request.topic}" at difficulty level {difficulty}/5.

Return ONLY a valid JSON array of objects with these fields:
- "question": the question text
- "options": array of 4 answer choices
- "correct_index": 0-based index of the correct answer
- "explanation": brief explanation of the correct answer

Example format:
[{{"question": "...", "options": ["A", "B", "C", "D"], "correct_index": 0, "explanation": "..."}}]"""

    response = await generate_response(
        system_prompt="You are a quiz generator for educational assessment. Return only valid JSON.",
        user_message=quiz_prompt,
        temperature=0.7, use_cache=False,
    )

    import json
    try:
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        questions_data = json.loads(text)
        questions = [QuizQuestion(**q) for q in questions_data]
    except (json.JSONDecodeError, Exception) as exc:
        logger.error("Quiz parse error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to generate quiz. Please try again.")

    return QuizResponse(
        questions=questions, topic=request.topic,
        difficulty_level=difficulty, session_id=learning_session.id,
    )


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_answer(
    request: EvaluateRequest,
    firebase_user: Annotated[FirebaseUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EvaluateResponse:
    """Evaluate a quiz answer, update mastery, and award XP."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_firebase_uid(firebase_user.uid)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    is_correct = request.user_answer.strip().lower() == request.correct_answer.strip().lower()

    # Update mastery
    gam_repo = GamificationRepository(db)
    mastery = await gam_repo.upsert_mastery(user.id, request.topic, is_correct)

    if is_correct:
        await gam_repo.increment_stat(user.id, "quiz_correct_total")

    # Award XP
    action = "quiz_correct" if is_correct else "quiz_incorrect"
    session = await SessionRepository(db).get_session(request.session_id, user.id)
    difficulty = session.difficulty_level if session else 1
    xp_amount = get_xp_for_action(action, difficulty)
    await award_xp(db, user.id, xp_amount, action)

    earned = await check_achievements(db, user.id)

    feedback = "Correct! Great job!" if is_correct else f"Not quite. The correct answer is: {request.correct_answer}"

    return EvaluateResponse(
        is_correct=is_correct, feedback=feedback,
        xp_earned=xp_amount, new_mastery_score=mastery.mastery_score,
        achievements_earned=earned,
    )
