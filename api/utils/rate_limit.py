"""
Redis-backed per-user rate limiter middleware.

Two-layer rate limiting:
  - General API: 60 req/min per authenticated user
  - Inference endpoint: 10 req/min per user
"""

import time

import redis.asyncio as aioredis
from fastapi import HTTPException, Request, status

from api.config import settings
from api.utils.logging import get_logger

logger = get_logger(__name__)

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get or create the async Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _redis_client


async def check_rate_limit(
    request: Request,
    user_id: str,
    *,
    is_inference: bool = False,
) -> None:
    """
    Check and enforce per-user rate limits using Redis sliding window.

    Args:
        request: The incoming FastAPI request.
        user_id: Authenticated user's ID.
        is_inference: If True, applies the stricter inference limit.

    Raises:
        HTTPException 429: If rate limit exceeded.
    """
    limit = (
        settings.inference_rate_limit_per_minute
        if is_inference
        else settings.api_rate_limit_per_minute
    )
    prefix = "inference" if is_inference else "api"
    key = f"rate_limit:{prefix}:{user_id}"

    try:
        client = await get_redis()
        now = time.time()
        window_start = now - 60

        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, 120)
        results = await pipe.execute()

        request_count = results[2]

        if request_count > limit:
            logger.warning(
                "Rate limit exceeded",
                extra={"user_id": user_id, "endpoint": prefix, "count": request_count},
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": "60"},
            )
    except HTTPException:
        raise
    except Exception as exc:
        # If Redis is down, log and allow the request through (graceful degradation)
        logger.error("Rate limiter Redis error: %s", exc)
