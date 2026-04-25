"""Structured audit logging service for Cloud Logging."""

from api.utils.logging import get_logger

logger = get_logger("audit")


def log_inference(
    user_id: str, model: str, intent: str,
    input_tokens: int, output_tokens: int, latency_ms: float,
) -> None:
    """Log a Gemini inference call for audit."""
    logger.info("gemini_inference", extra={
        "audit_type": "inference", "user_id": user_id, "model": model,
        "intent": intent, "input_tokens": input_tokens,
        "output_tokens": output_tokens, "latency_ms": round(latency_ms, 2),
    })


def log_auth_event(event: str, user_id: str, email: str) -> None:
    """Log an authentication event."""
    logger.info("auth_event", extra={
        "audit_type": "auth", "event": event,
        "user_id": user_id, "email": email,
    })


def log_gamification_event(event: str, user_id: str, **kwargs: object) -> None:
    """Log a gamification event (XP award, level up, achievement)."""
    logger.info("gamification_event", extra={
        "audit_type": "gamification", "event": event,
        "user_id": user_id, **kwargs,
    })
