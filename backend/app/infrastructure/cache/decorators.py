"""
Cache decorators for Redis-backed caching.

Usage:

    @cache("dashboard:{user_id}", ttl=300)
    async def get_dashboard_data(user_id: int):
        ...

    @invalidate("dashboard:{user.id}")
    async def add_transaction_route(data, user=Depends(get_current_user)):
        ...

    # Явная инвалидация (для воркеров и т.д.)
    await invalidate_cache("dashboard:*")

Key template syntax:
    {param}       — simple parameter from function kwargs
    {param.attr}  — dict key or object attribute (e.g. user["id"] via {user.id})
    *             — wildcard for pattern-based deletion
"""
import functools
import inspect
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

import orjson

from app.infrastructure.cache.redis_client import (
    redis_get,
    redis_set,
    redis_delete,
    redis_delete_pattern,
    redis_available,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Cannot serialize {type(obj)}")


def _serialize(data: Any) -> str:
    return orjson.dumps(
        data,
        default=_json_default,
        option=orjson.OPT_NON_STR_KEYS,
    ).decode("utf-8")


def _deserialize(raw: str) -> Any:
    return orjson.loads(raw)


def _resolve_key(template: str, bound_args: dict) -> Optional[str]:
    """Resolve '{param}' and '{param.attr}' placeholders from function arguments."""
    def _replacer(match: re.Match) -> str:
        expr = match.group(1)
        parts = expr.split(".")
        value = bound_args.get(parts[0])
        for part in parts[1:]:
            if isinstance(value, dict):
                value = value.get(part)
            elif value is not None:
                value = getattr(value, part, None)
        if value is None:
            return ""
        return str(value)

    try:
        resolved = re.sub(r"\{([^}]+)\}", _replacer, template)
        if not resolved or resolved == template.replace("{", "").replace("}", ""):
            return None
        return resolved
    except Exception:
        return None


def _bind_args(func, args, kwargs) -> dict:
    """Bind positional and keyword args to parameter names."""
    try:
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        return bound.arguments
    except Exception:
        return kwargs


def cache(key: str, ttl: int = 300):
    """
    Cache the async function's return value in Redis.

    On cache hit, returns deserialized cached data without calling the function.
    On cache miss, calls the function, serializes the result, stores it in Redis.
    If Redis is unavailable, the function is called normally.
    """
    def decorator(func):
        _original = func
        if hasattr(func, "__wrapped__"):
            _original = func.__wrapped__

        @functools.wraps(_original)
        async def wrapper(*args, **kwargs):
            if not redis_available():
                return await func(*args, **kwargs)

            bound = _bind_args(_original, args, kwargs)
            cache_key = _resolve_key(key, bound)
            if not cache_key:
                return await func(*args, **kwargs)

            cached = await redis_get(cache_key)
            if cached is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return _deserialize(cached)

            result = await func(*args, **kwargs)

            if result is not None:
                try:
                    await redis_set(cache_key, _serialize(result), ttl)
                    logger.debug(f"Cache SET: {cache_key} (ttl={ttl}s)")
                except Exception as e:
                    logger.debug(f"Cache SET failed for {cache_key}: {e}")

            return result

        wrapper.__wrapped__ = _original
        return wrapper
    return decorator


def invalidate(*key_templates: str):
    """
    Invalidate cache keys after the decorated async function executes successfully.

    Supports:
        @invalidate("dashboard:{user.id}")          — single key
        @invalidate("dashboard:{user.id}", "analytics:{user.id}")  — multiple keys
        @invalidate("dashboard:*")                   — wildcard pattern
    """
    def decorator(func):
        _original = func
        if hasattr(func, "__wrapped__"):
            _original = func.__wrapped__

        @functools.wraps(_original)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            if not redis_available():
                return result

            bound = _bind_args(_original, args, kwargs)

            for tmpl in key_templates:
                try:
                    if "*" in tmpl:
                        static_part = tmpl.split("*")[0]
                        resolved_prefix = _resolve_key(static_part, bound) if "{" in static_part else static_part
                        if resolved_prefix:
                            deleted = await redis_delete_pattern(f"{resolved_prefix}*")
                            if deleted:
                                logger.debug(f"Cache INVALIDATE pattern: {resolved_prefix}* ({deleted} keys)")
                    else:
                        resolved = _resolve_key(tmpl, bound)
                        if resolved:
                            await redis_delete(resolved)
                            logger.debug(f"Cache INVALIDATE: {resolved}")
                except Exception as e:
                    logger.debug(f"Cache invalidation error for {tmpl}: {e}")

            return result

        wrapper.__wrapped__ = _original
        return wrapper
    return decorator


async def invalidate_cache(*key_templates: str, **params: Any) -> int:
    """
    Explicit cache invalidation function.

    Usage:
        await invalidate_cache("dashboard:123")
        await invalidate_cache("dashboard:*")
        await invalidate_cache("dashboard:{user_id}", user_id=123)
    """
    if not redis_available():
        return 0

    total = 0
    for tmpl in key_templates:
        resolved = tmpl
        if "{" in tmpl and params:
            resolved = _resolve_key(tmpl, params)
        if not resolved:
            continue

        try:
            if "*" in resolved:
                total += await redis_delete_pattern(resolved)
            else:
                total += await redis_delete(resolved)
        except Exception as e:
            logger.debug(f"invalidate_cache error for {resolved}: {e}")

    if total:
        logger.debug(f"invalidate_cache: cleared {total} keys")
    return total
