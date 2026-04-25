"""
Gemini Service — all Vertex AI / Gemini API interactions.

Centralises model calls with safety settings, token tracking,
and structured audit logging. Never called directly from routers;
always through intent_service or adaptive_engine.
"""

import hashlib
import json
import time

import vertexai
from vertexai.generative_models import (
    GenerationConfig,
    GenerativeModel,
    HarmBlockThreshold,
    HarmCategory,
)

from api.config import settings
from api.utils.cache import cache_get, cache_set
from api.utils.logging import get_logger

logger = get_logger(__name__)

# ── Safety settings applied on EVERY call ─────────────────────────
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

_initialised = False


def _ensure_init() -> None:
    """Lazily initialise Vertex AI SDK."""
    global _initialised
    if not _initialised:
        vertexai.init(
            project=settings.gcp_project_id,
            location=settings.gcp_region,
        )
        _initialised = True
        logger.info("Vertex AI SDK initialised")


class GeminiResponse:
    """Structured wrapper around a Gemini API response."""

    def __init__(
        self,
        text: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        is_fallback: bool = False,
        error_code: str | None = None,
    ) -> None:
        self.text = text
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.is_fallback = is_fallback
        self.error_code = error_code

    @classmethod
    def fallback(cls, reason: str) -> "GeminiResponse":
        """Create a graceful fallback response."""
        fallback_messages = {
            "SAFETY_BLOCK": "I'm unable to respond to that request. Please try rephrasing your question.",
            "UPSTREAM_UNAVAILABLE": "The AI service is temporarily unavailable. Please try again in a moment.",
            "TOKEN_LIMIT": "That request is too complex. Please try breaking it into smaller parts.",
        }
        return cls(
            text=fallback_messages.get(reason, "Something went wrong. Please try again."),
            model="fallback",
            is_fallback=True,
            error_code=reason,
        )


async def generate_response(
    system_prompt: str,
    user_message: str,
    *,
    conversation_history: list[dict] | None = None,
    model_name: str | None = None,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
    use_cache: bool = True,
) -> GeminiResponse:
    """
    Generate a response from Gemini with full safety, caching, and audit logging.

    Args:
        system_prompt: System instruction for the model.
        user_message: The user's current message.
        conversation_history: Prior turns as [{"role": "user"/"model", "parts": [...]}].
        model_name: Override model selection (defaults to Flash).
        temperature: Override temperature (defaults to config).
        max_output_tokens: Override max tokens (defaults to config).
        use_cache: Whether to check Redis cache for identical prompts.

    Returns:
        GeminiResponse with text, token counts, and fallback info.
    """
    _ensure_init()

    model_name = model_name or settings.gemini_model_flash
    temperature = temperature if temperature is not None else settings.gemini_temperature
    max_output_tokens = max_output_tokens or settings.gemini_max_output_tokens

    # ── Cache check for identical prompts ─────────────────────────
    if use_cache:
        cache_key = _build_cache_key(system_prompt, user_message, model_name)
        cached = await cache_get(cache_key)
        if cached is not None:
            return GeminiResponse(
                text=cached["text"],
                model=model_name,
                input_tokens=cached.get("input_tokens", 0),
                output_tokens=cached.get("output_tokens", 0),
            )

    # ── Build conversation contents ───────────────────────────────
    contents = []
    if conversation_history:
        contents.extend(conversation_history)
    contents.append({"role": "user", "parts": [user_message]})

    # ── Call Gemini ────────────────────────────────────────────────
    start_time = time.time()

    try:
        model = GenerativeModel(model_name, system_instruction=system_prompt)
        config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        response = await model.generate_content_async(
            contents,
            generation_config=config,
            safety_settings=SAFETY_SETTINGS,
            stream=False,
        )
    except Exception as exc:
        logger.error("Gemini API call failed", extra={"model": model_name, "error": str(exc)})
        return GeminiResponse.fallback("UPSTREAM_UNAVAILABLE")

    latency_ms = (time.time() - start_time) * 1000

    # ── Handle safety blocks ──────────────────────────────────────
    if not response.candidates:
        logger.warning(
            "Gemini returned no candidates — safety block likely",
            extra={"model": model_name},
        )
        return GeminiResponse.fallback("SAFETY_BLOCK")

    # ── Extract usage metadata ────────────────────────────────────
    usage = response.usage_metadata
    input_tokens = usage.prompt_token_count if usage else 0
    output_tokens = usage.candidates_token_count if usage else 0

    logger.info(
        "Gemini inference complete",
        extra={
            "model": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": round(latency_ms, 2),
            "finish_reason": response.candidates[0].finish_reason.name,
        },
    )

    # ── Token budget warning ──────────────────────────────────────
    if input_tokens > 50_000:
        logger.warning(
            "Token budget warning — high input token count",
            extra={"input_tokens": input_tokens},
        )

    result_text = response.text

    # ── Cache the result ──────────────────────────────────────────
    if use_cache:
        await cache_set(
            cache_key,
            {"text": result_text, "input_tokens": input_tokens, "output_tokens": output_tokens},
            ttl_seconds=settings.redis_ttl_seconds,
        )

    return GeminiResponse(
        text=result_text,
        model=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _build_cache_key(system_prompt: str, user_message: str, model: str) -> str:
    """Build a deterministic cache key from prompt components."""
    content = f"{model}:{system_prompt}:{user_message}"
    return f"gemini_cache:{hashlib.sha256(content.encode()).hexdigest()}"
