"""
WealthBot Redis Cache
=====================
Async Redis connection pool and caching utilities.
"""

import json
import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger("wealthbot.cache")


# =============================================================================
# Redis Connection Pool (Singleton)
# =============================================================================


class RedisPool:
    """Manages async Redis connection lifecycle."""

    def __init__(self) -> None:
        self._redis: Any = None

    async def connect(self) -> None:
        """Initialise the async Redis connection pool."""
        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(
                settings.redis_url, 
                decode_responses=True,
                socket_connect_timeout=5,
            )
            await self._redis.ping()
            logger.info("Redis connected: %s", settings.redis_url)
        except Exception:
            logger.warning("Redis unavailable — caching disabled.")
            self._redis = None

    async def close(self) -> None:
        """Close the Redis connection pool."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    @property
    def available(self) -> bool:
        """Check if Redis is connected."""
        return self._redis is not None

    async def get(self, key: str) -> str | None:
        """Get a value from Redis."""
        if not self.available:
            return None
        try:
            return await self._redis.get(key)
        except Exception:
            logger.warning("Redis GET failed for key=%s", key)
            return None

    async def set(self, key: str, value: str, ttl: int) -> None:
        """Set a value in Redis with a TTL (seconds)."""
        if not self.available:
            return
        try:
            await self._redis.set(key, value, ex=ttl)
        except Exception:
            logger.warning("Redis SET failed for key=%s", key)

    async def delete(self, key: str) -> None:
        """Delete a key from Redis."""
        if not self.available:
            return
        try:
            await self._redis.delete(key)
        except Exception:
            logger.warning("Redis DELETE failed for key=%s", key)


redis_pool = RedisPool()


# =============================================================================
# Prediction Cache Helpers
# =============================================================================


async def get_cached_prediction(user_id: str) -> dict[str, Any] | None:
    """Retrieve a cached safe-to-spend prediction for a user."""
    raw = await redis_pool.get(f"sts:{user_id}")
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


async def set_cached_prediction(user_id: str, data: dict[str, Any]) -> None:
    """Cache a safe-to-spend prediction for a user."""
    await redis_pool.set(
        f"sts:{user_id}",
        json.dumps(data),
        ttl=settings.prediction_cache_ttl,
    )
