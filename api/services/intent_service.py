"""
Intent Service — classifies user input before routing to the appropriate handler.

Implements the Context Pipeline:
  1. Intent Classification (Gemini Flash)
  2. Context Enrichment (DB + Redis)
  3. Prompt Construction
  4. Gemini Inference
  5. Response Validation
  6. Structured Output
  7. Audit Log
"""

import json

from api.config import settings
from api.schemas.assistant import IntentType
from api.services.gemini_service import generate_response
from api.utils.logging import get_logger

logger = get_logger(__name__)

INTENT_CLASSIFICATION_PROMPT = """You are an intent classifier for an educational learning assistant.

Classify the user's message into EXACTLY ONE of these categories:
- "learn": User wants to learn about a topic or asks an educational question
- "quiz": User wants to be quizzed or tested on their knowledge
- "explain": User wants a simpler or different explanation of something
- "summarize": User wants a summary of what they've learned
- "clarify": User is confused or asking a follow-up question
- "unknown": Cannot determine intent

Respond with ONLY a JSON object: {"intent": "<type>", "confidence": <0.0-1.0>, "topic": "<extracted topic or null>"}

Do not include any other text."""


async def classify_intent(
    user_message: str,
    session_topic: str | None = None,
) -> dict:
    """
    Classify user input into a structured intent using Gemini Flash.

    Uses the fast Flash model for low-latency classification.
    Applies confidence gating: returns CLARIFY if confidence < 0.6.

    Args:
        user_message: Raw text from the user.
        session_topic: Current session topic for context.

    Returns:
        Dict with 'intent', 'confidence', and 'topic' keys.
    """
    context = f"\nCurrent session topic: {session_topic}" if session_topic else ""
    prompt = INTENT_CLASSIFICATION_PROMPT + context

    response = await generate_response(
        system_prompt=prompt,
        user_message=user_message,
        model_name=settings.gemini_model_flash,
        temperature=0.1,
        max_output_tokens=100,
        use_cache=False,  # Intent depends on context, don't cache
    )

    if response.is_fallback:
        return {
            "intent": IntentType.LEARN,
            "confidence": 0.5,
            "topic": session_topic,
        }

    try:
        # Extract JSON from response (handle markdown code blocks)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(text)

        intent = result.get("intent", "unknown")
        confidence = float(result.get("confidence", 0.0))
        topic = result.get("topic", session_topic)

        # Confidence gating: if uncertain, ask for clarification
        if confidence < 0.6:
            logger.info(
                "Low confidence intent — routing to clarify",
                extra={"intent": intent, "confidence": confidence},
            )
            intent = IntentType.CLARIFY

        logger.info(
            "Intent classified",
            extra={"intent": intent, "confidence": confidence, "topic": topic},
        )

        return {
            "intent": intent,
            "confidence": confidence,
            "topic": topic,
        }
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.warning("Intent classification parse error: %s", exc)
        return {
            "intent": IntentType.LEARN,
            "confidence": 0.5,
            "topic": session_topic,
        }
