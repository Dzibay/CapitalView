"""
Блокирующий Redis-клиент (redis.Redis) — синхронный домен (reference_service, rpc).

Общий префикс ключей с redis_client — см. redis_client.CACHE_PREFIX.
"""
from typing import Optional

import redis

from app.core.logging import get_logger
from app.infrastructure.cache.redis_client import CACHE_PREFIX

logger = get_logger(__name__)

_redis_client_sync: Optional[redis.Redis] = None


def _key(name: str) -> str:
    return f"{CACHE_PREFIX}{name}"


def init_redis_sync(url: str) -> bool:
    global _redis_client_sync
    _redis_client_sync = None
    if not url or not url.strip():
        logger.info("REDIS_URL пуст — sync-кэш справочника только в памяти процесса")
        return False
    try:
        client = redis.from_url(
            url.strip(),
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        client.ping()
        _redis_client_sync = client
        logger.info("redis_client_sync: подключён (общий кэш справочника)")
        return True
    except Exception as e:
        logger.warning("redis_client_sync недоступен (%s) — справочник в памяти воркера", e)
        _redis_client_sync = None
        return False


def close_redis_sync() -> None:
    global _redis_client_sync
    if _redis_client_sync is not None:
        try:
            _redis_client_sync.close()
        except Exception:
            pass
        _redis_client_sync = None


def redis_sync_available() -> bool:
    return _redis_client_sync is not None


def redis_sync_get(key: str) -> Optional[str]:
    if not _redis_client_sync:
        return None
    try:
        return _redis_client_sync.get(_key(key))
    except Exception as e:
        logger.debug("redis_client_sync GET %s: %s", key, e)
        return None


def redis_sync_set(key: str, value: str, ex: Optional[int] = None) -> bool:
    if not _redis_client_sync:
        return False
    try:
        if ex is not None:
            _redis_client_sync.set(_key(key), value, ex=ex)
        else:
            _redis_client_sync.set(_key(key), value)
        return True
    except Exception as e:
        logger.debug("redis_client_sync SET %s: %s", key, e)
        return False


def redis_sync_delete(*keys: str) -> int:
    if not _redis_client_sync or not keys:
        return 0
    try:
        return int(_redis_client_sync.delete(*[_key(k) for k in keys]))
    except Exception as e:
        logger.debug("redis_client_sync DELETE: %s", e)
        return 0
