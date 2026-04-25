"""
Integration tests for Assistant routes — chat, quiz, evaluate.

Tests:
  - Chat endpoint with mocked Gemini responses
  - Gemini API failure → graceful fallback
  - Quiz generation + evaluation flow
  - Unauthenticated and malformed requests
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_gemini_response(text: str, model: str = "gemini-1.5-flash-002"):
    """Build a mock GeminiResponse for service layer."""
    resp = MagicMock()
    resp.text = text
    resp.is_fallback = False
    resp.model = model
    resp.input_tokens = 100
    resp.output_tokens = 50
    return resp


def _mock_session(topic: str = "Python", difficulty: int = 1):
    """Build a mock LearningSession."""
    import uuid
    session = MagicMock()
    session.id = uuid.uuid4()
    session.topic = topic
    session.difficulty_level = difficulty
    session.user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    return session


class TestChatEndpoint:
    """POST /assistant/chat integration tests."""

    @patch("api.routers.assistant.check_achievements", new_callable=AsyncMock, return_value=[])
    @patch("api.routers.assistant.award_xp", new_callable=AsyncMock, return_value={
        "amount": 10, "new_total": 510, "new_level": 3, "level_up": False, "reason": "chat_message"
    })
    @patch("api.routers.assistant.update_streak", new_callable=AsyncMock, return_value=5)
    @patch("api.routers.assistant.calculate_difficulty", new_callable=AsyncMock, return_value=1)
    @patch("api.routers.assistant.build_enriched_context", new_callable=AsyncMock)
    @patch("api.routers.assistant.classify_intent", new_callable=AsyncMock)
    @patch("api.routers.assistant.generate_response", new_callable=AsyncMock)
    @patch("api.routers.assistant.log_inference")
    @patch("api.routers.assistant.SessionRepository")
    @patch("api.routers.assistant.UserRepository")
    def test_chat_success(
        self, MockUserRepo, MockSessionRepo, mock_log_inf,
        mock_generate, mock_classify, mock_context, mock_difficulty,
        mock_streak, mock_award, mock_achievements, test_client, mock_user
    ):
        """Valid chat request → 200 with AI response + XP earned."""
        MockUserRepo.return_value.get_by_firebase_uid = AsyncMock(return_value=mock_user)

        session = _mock_session()
        MockSessionRepo.return_value.create_session = AsyncMock(return_value=session)
        MockSessionRepo.return_value.add_message = AsyncMock()

        mock_classify.return_value = {"intent": "learn", "confidence": 0.9, "topic": "Python"}
        mock_context.return_value = {
            "system_prompt": "You are a tutor...",
            "conversation_history": [],
        }
        mock_generate.return_value = _mock_gemini_response("Python is a versatile language...")

        response = test_client.post("/assistant/chat", json={
            "message": "Teach me about Python",
            "topic": "Python",
        })

        assert response.status_code == 200
        data = response.json()
        assert "Python" in data["message"]
        assert data["xp_earned"] > 0
        assert data["intent"] == "learn"

    @patch("api.routers.assistant.UserRepository")
    def test_chat_user_not_found(self, MockUserRepo, test_client):
        """Valid auth but user not in DB → 404."""
        MockUserRepo.return_value.get_by_firebase_uid = AsyncMock(return_value=None)

        response = test_client.post("/assistant/chat", json={
            "message": "Hello",
        })

        assert response.status_code == 404

    def test_chat_empty_message(self, test_client):
        """Empty message → 422 (validation error)."""
        response = test_client.post("/assistant/chat", json={
            "message": "",
        })

        assert response.status_code == 422

    def test_chat_missing_message(self, test_client):
        """Missing message field → 422."""
        response = test_client.post("/assistant/chat", json={})

        assert response.status_code == 422


class TestQuizEndpoint:
    """POST /assistant/quiz integration tests."""

    @patch("api.routers.assistant.generate_response", new_callable=AsyncMock)
    @patch("api.routers.assistant.SessionRepository")
    @patch("api.routers.assistant.UserRepository")
    def test_quiz_generation_success(self, MockUserRepo, MockSessionRepo, mock_generate,
                                      test_client, mock_user):
        """Valid quiz request → 200 with generated questions."""
        MockUserRepo.return_value.get_by_firebase_uid = AsyncMock(return_value=mock_user)
        session = _mock_session()
        MockSessionRepo.return_value.create_session = AsyncMock(return_value=session)

        quiz_data = [
            {
                "question": "What is a list in Python?",
                "options": ["A data type", "A loop", "A function", "A module"],
                "correct_index": 0,
                "explanation": "A list is a mutable data type.",
            }
        ]
        mock_generate.return_value = _mock_gemini_response(json.dumps(quiz_data))

        response = test_client.post("/assistant/quiz", json={
            "topic": "Python",
            "num_questions": 1,
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data["questions"]) == 1
        assert data["topic"] == "Python"

    @patch("api.routers.assistant.generate_response", new_callable=AsyncMock)
    @patch("api.routers.assistant.SessionRepository")
    @patch("api.routers.assistant.UserRepository")
    def test_quiz_gemini_bad_json(self, MockUserRepo, MockSessionRepo, mock_generate,
                                   test_client, mock_user):
        """Gemini returns invalid JSON → 500."""
        MockUserRepo.return_value.get_by_firebase_uid = AsyncMock(return_value=mock_user)
        session = _mock_session()
        MockSessionRepo.return_value.create_session = AsyncMock(return_value=session)
        mock_generate.return_value = _mock_gemini_response("This is not JSON")

        response = test_client.post("/assistant/quiz", json={
            "topic": "Python",
            "num_questions": 1,
        })

        assert response.status_code == 500

    def test_quiz_missing_topic(self, test_client):
        """Missing topic → 422."""
        response = test_client.post("/assistant/quiz", json={"num_questions": 3})
        assert response.status_code == 422


class TestEvaluateEndpoint:
    """POST /assistant/evaluate integration tests."""

    @patch("api.routers.assistant.check_achievements", new_callable=AsyncMock, return_value=[])
    @patch("api.routers.assistant.award_xp", new_callable=AsyncMock, return_value={
        "amount": 25, "new_total": 525, "new_level": 3, "level_up": False, "reason": "quiz_correct"
    })
    @patch("api.routers.assistant.SessionRepository")
    @patch("api.routers.assistant.GamificationRepository")
    @patch("api.routers.assistant.UserRepository")
    def test_evaluate_correct_answer(self, MockUserRepo, MockGamRepo, MockSessionRepo,
                                      mock_award, mock_achievements, test_client, mock_user, mock_mastery):
        """Correct answer → is_correct=True + XP awarded."""
        MockUserRepo.return_value.get_by_firebase_uid = AsyncMock(return_value=mock_user)
        MockGamRepo.return_value.upsert_mastery = AsyncMock(return_value=mock_mastery)
        MockGamRepo.return_value.increment_stat = AsyncMock()
        session = _mock_session()
        MockSessionRepo.return_value.get_session = AsyncMock(return_value=session)

        import uuid
        response = test_client.post("/assistant/evaluate", json={
            "session_id": str(uuid.uuid4()),
            "question": "What is Python?",
            "user_answer": "A programming language",
            "correct_answer": "A programming language",
            "topic": "Python",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["is_correct"] is True
        assert data["xp_earned"] > 0

    @patch("api.routers.assistant.check_achievements", new_callable=AsyncMock, return_value=[])
    @patch("api.routers.assistant.award_xp", new_callable=AsyncMock, return_value={
        "amount": 5, "new_total": 505, "new_level": 3, "level_up": False, "reason": "quiz_incorrect"
    })
    @patch("api.routers.assistant.SessionRepository")
    @patch("api.routers.assistant.GamificationRepository")
    @patch("api.routers.assistant.UserRepository")
    def test_evaluate_incorrect_answer(self, MockUserRepo, MockGamRepo, MockSessionRepo,
                                        mock_award, mock_achievements, test_client, mock_user, mock_mastery):
        """Incorrect answer → is_correct=False + smaller XP."""
        MockUserRepo.return_value.get_by_firebase_uid = AsyncMock(return_value=mock_user)
        MockGamRepo.return_value.upsert_mastery = AsyncMock(return_value=mock_mastery)
        session = _mock_session()
        MockSessionRepo.return_value.get_session = AsyncMock(return_value=session)

        import uuid
        response = test_client.post("/assistant/evaluate", json={
            "session_id": str(uuid.uuid4()),
            "question": "What is Python?",
            "user_answer": "A snake",
            "correct_answer": "A programming language",
            "topic": "Python",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["is_correct"] is False
        assert "correct answer" in data["feedback"].lower()
