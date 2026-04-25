"""
Unit tests for Intent Service — intent classification logic.

Tests classification parsing, confidence gating, fallback behavior,
and handling of 10+ representative inputs.
"""

import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from api.schemas.assistant import IntentType


# ── Helper to mock Gemini response ────────────────────────────────

def _make_response(intent: str, confidence: float, topic: str | None = None, is_fallback: bool = False):
    """Build a mock GeminiResponse."""
    resp = MagicMock()
    resp.is_fallback = is_fallback
    resp.text = json.dumps({"intent": intent, "confidence": confidence, "topic": topic})
    return resp


class TestClassifyIntent:
    """Tests for classify_intent() function."""

    @pytest.mark.asyncio
    @patch("api.services.intent_service.generate_response", new_callable=AsyncMock)
    async def test_learn_intent_high_confidence(self, mock_gen):
        """User clearly wants to learn a topic → learn intent."""
        mock_gen.return_value = _make_response("learn", 0.95, "Python")

        from api.services.intent_service import classify_intent
        result = await classify_intent("Teach me about Python programming")

        assert result["intent"] == "learn"
        assert result["confidence"] == 0.95
        assert result["topic"] == "Python"

    @pytest.mark.asyncio
    @patch("api.services.intent_service.generate_response", new_callable=AsyncMock)
    async def test_quiz_intent(self, mock_gen):
        """User requests a quiz → quiz intent."""
        mock_gen.return_value = _make_response("quiz", 0.9, "Mathematics")

        from api.services.intent_service import classify_intent
        result = await classify_intent("Quiz me on math")

        assert result["intent"] == "quiz"
        assert result["confidence"] == 0.9

    @pytest.mark.asyncio
    @patch("api.services.intent_service.generate_response", new_callable=AsyncMock)
    async def test_explain_intent(self, mock_gen):
        """User wants simpler explanation → explain intent."""
        mock_gen.return_value = _make_response("explain", 0.88, "Recursion")

        from api.services.intent_service import classify_intent
        result = await classify_intent("Can you explain that in simpler terms?")

        assert result["intent"] == "explain"

    @pytest.mark.asyncio
    @patch("api.services.intent_service.generate_response", new_callable=AsyncMock)
    async def test_summarize_intent(self, mock_gen):
        """User requests summary → summarize intent."""
        mock_gen.return_value = _make_response("summarize", 0.92)

        from api.services.intent_service import classify_intent
        result = await classify_intent("Summarize what we've covered")

        assert result["intent"] == "summarize"

    @pytest.mark.asyncio
    @patch("api.services.intent_service.generate_response", new_callable=AsyncMock)
    async def test_clarify_intent(self, mock_gen):
        """User is confused → clarify intent."""
        mock_gen.return_value = _make_response("clarify", 0.85)

        from api.services.intent_service import classify_intent
        result = await classify_intent("I don't understand, what does that mean?")

        assert result["intent"] == "clarify"

    @pytest.mark.asyncio
    @patch("api.services.intent_service.generate_response", new_callable=AsyncMock)
    async def test_low_confidence_routes_to_clarify(self, mock_gen):
        """Low confidence (<0.6) should route to clarify intent."""
        mock_gen.return_value = _make_response("learn", 0.4, "Unknown")

        from api.services.intent_service import classify_intent
        result = await classify_intent("hmm okay")

        assert result["intent"] == IntentType.CLARIFY
        assert result["confidence"] == 0.4

    @pytest.mark.asyncio
    @patch("api.services.intent_service.generate_response", new_callable=AsyncMock)
    async def test_confidence_boundary_at_0_6(self, mock_gen):
        """Exactly 0.6 confidence should NOT trigger clarify gating."""
        mock_gen.return_value = _make_response("learn", 0.6, "React")

        from api.services.intent_service import classify_intent
        result = await classify_intent("Tell me about React hooks")

        assert result["intent"] == "learn"
        assert result["confidence"] == 0.6

    @pytest.mark.asyncio
    @patch("api.services.intent_service.generate_response", new_callable=AsyncMock)
    async def test_fallback_on_gemini_failure(self, mock_gen):
        """Gemini API failure → fallback to learn intent with low confidence."""
        mock_gen.return_value = _make_response("", 0, is_fallback=True)

        from api.services.intent_service import classify_intent
        result = await classify_intent("Tell me about calculus", "Math")

        assert result["intent"] == IntentType.LEARN
        assert result["confidence"] == 0.5
        assert result["topic"] == "Math"

    @pytest.mark.asyncio
    @patch("api.services.intent_service.generate_response", new_callable=AsyncMock)
    async def test_malformed_json_fallback(self, mock_gen):
        """Invalid JSON response from Gemini → graceful fallback."""
        resp = MagicMock()
        resp.is_fallback = False
        resp.text = "This is not JSON at all"
        mock_gen.return_value = resp

        from api.services.intent_service import classify_intent
        result = await classify_intent("hello")

        assert result["intent"] == IntentType.LEARN
        assert result["confidence"] == 0.5

    @pytest.mark.asyncio
    @patch("api.services.intent_service.generate_response", new_callable=AsyncMock)
    async def test_markdown_code_block_json(self, mock_gen):
        """Gemini wraps JSON in markdown code block → should parse correctly."""
        resp = MagicMock()
        resp.is_fallback = False
        resp.text = '```json\n{"intent": "quiz", "confidence": 0.9, "topic": "History"}\n```'
        mock_gen.return_value = resp

        from api.services.intent_service import classify_intent
        result = await classify_intent("Test me on history")

        assert result["intent"] == "quiz"
        assert result["topic"] == "History"

    @pytest.mark.asyncio
    @patch("api.services.intent_service.generate_response", new_callable=AsyncMock)
    async def test_session_topic_context_passed(self, mock_gen):
        """Session topic should be appended to classification prompt."""
        mock_gen.return_value = _make_response("learn", 0.9, "Python")

        from api.services.intent_service import classify_intent
        await classify_intent("Tell me more", session_topic="Python")

        call_args = mock_gen.call_args
        assert "Python" in call_args.kwargs.get("system_prompt", "")

    @pytest.mark.asyncio
    @patch("api.services.intent_service.generate_response", new_callable=AsyncMock)
    async def test_unknown_intent(self, mock_gen):
        """Unknown intent string from Gemini → passes through as unknown."""
        mock_gen.return_value = _make_response("unknown", 0.7)

        from api.services.intent_service import classify_intent
        result = await classify_intent("asdfghjkl")

        assert result["intent"] == "unknown"
