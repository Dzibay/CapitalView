"""
Redis client for caching.

Graceful degradation: if Redis is unavailable, all operations return None/False
and the app continues to work without caching.
"""
import redis.asyncio as aioredis
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis: Optional[aioredis.Redis] = None

CACHE_PREFIX = "cv:"


async def init_redis(url: str) -> bool:
    global _redis
    if not url:
        logger.info("REDIS_URL not configured — caching disabled")
        return False
    try:
        _redis = aioredis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=2,
            retry_on_timeout=True,
        )
        await _redis.ping()
        logger.info(f"Redis connected: {url.split('@')[-1] if '@' in url else url}")
        return True
    except Exception as e:
        logger.warning(f"Redis unavailable ({e}) — caching disabled")
        _redis = None
        return False


async def close_redis() -> None:
    global _redis
    if _redis:
        try:
            await _redis.aclose()
        except Exception:
            pass
        _redis = None
        logger.info("Redis connection closed")


def redis_available() -> bool:
    return _redis is not None


def _key(name: str) -> str:
    return f"{CACHE_PREFIX}{name}"


async def redis_get(key: str) -> Optional[str]:
    if not _redis:
        return None
    try:
        return await _redis.get(_key(key))
    except Exception as e:
        logger.debug(f"Redis GET error for {key}: {e}")
        return None


async def redis_set(key: str, value: str, ttl: int = 300) -> bool:
    if not _redis:
        return False
    try:
        await _redis.set(_key(key), value, ex=ttl)
        return True
    except Exception as e:
        logger.debug(f"Redis SET error for {key}: {e}")
        return False


async def redis_delete(*keys: str) -> int:
    if not _redis or not keys:
        return 0
    try:
        full_keys = [_key(k) for k in keys]
        return await _redis.delete(*full_keys)
    except Exception as e:
        logger.debug(f"Redis DELETE error: {e}")
        return 0


async def redis_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern (e.g. 'dashboard:*')."""
    if not _redis:
        return 0
    try:
        full_pattern = _key(pattern)
        count = 0
        async for key in _redis.scan_iter(match=full_pattern, count=200):
            await _redis.delete(key)
            count += 1
        return count
    except Exception as e:
        logger.debug(f"Redis DELETE pattern error for {pattern}: {e}")
        return 0
