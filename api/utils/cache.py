"""
Redis cache wrapper for Memorystore.

Provides typed get/set with configurable TTL for caching
repeated Gemini prompts and session context.
"""

import json
from typing import Any

from api.utils.logging import get_logger
from api.utils.rate_limit import get_redis

logger = get_logger(__name__)


async def cache_get(key: str) -> Any | None:
    """
    Retrieve a cached JSON value by key.

    Returns:
        Parsed JSON value, or None if not found or on error.
    """
    try:
        client = await get_redis()
        value = await client.get(key)
        if value is not None:
            logger.info("Cache hit", extra={"key": key})
            return json.loads(value)
    except Exception as exc:
        logger.error("Cache get error: %s", exc)
    return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> None:
    """
    Store a JSON-serialisable value in cache with TTL.

    Args:
        key: Cache key.
        value: JSON-serialisable value.
        ttl_seconds: Time-to-live in seconds (default: 5 minutes).
    """
    try:
        client = await get_redis()
        await client.setex(key, ttl_seconds, json.dumps(value, default=str))
        logger.info("Cache set", extra={"key": key, "ttl": ttl_seconds})
    except Exception as exc:
        logger.error("Cache set error: %s", exc)


async def cache_delete(key: str) -> None:
    """Remove a key from cache."""
    try:
        client = await get_redis()
        await client.delete(key)
    except Exception as exc:
        logger.error("Cache delete error: %s", exc)
