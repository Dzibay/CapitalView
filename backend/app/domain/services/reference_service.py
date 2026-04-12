"""
Справочные данные: общий кэш в Redis (все воркеры/инстансы), иначе — память процесса.

Брокеры и payload справочника (reference + assets_index) хранятся в Redis без TTL;
инвалидация — invalidate_reference_cache() (после обновления MOEX и т.п.).
"""
import asyncio
import hashlib
import json
from app.infrastructure.database.database_service import rpc_async, table_select_async
from app.core.logging import get_logger
from app.infrastructure.cache.redis_client_sync import (
    redis_sync_available,
    redis_sync_delete,
    redis_sync_get,
    redis_sync_set,
)

logger = get_logger(__name__)

# Ключи Redis (префикс — redis_client.CACHE_PREFIX, тот же у redis_client_sync)
REF_FINGERPRINT_KEY = "reference:fingerprint"
REF_BUNDLE_KEY = "reference:bundle"
REF_BROKERS_KEY = "reference:brokers"

# Локальный снимок после парсинга bundle (на воркере), синхронизируется по fingerprint с Redis
_worker_bundle: dict = {
    "fingerprint": None,
    "reference": None,
    "assets_list": None,
    "assets_by_id": None,
}

# Fallback, если REDIS_URL не задан или Redis недоступен
_memory_fallback: dict = {
    "reference": None,
    "reference_fingerprint": "",
    "assets_search_list": None,
    "assets_search_by_id": None,
    "brokers": None,
}


def _reference_fingerprint_for(ref: dict) -> str:
    if not ref:
        return ""
    try:
        blob = json.dumps(ref, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()
    except Exception as e:
        logger.warning("Не удалось вычислить reference_fingerprint: %s", e)
        return ""


def _parse_rpc_dict(raw) -> dict:
    if raw is None:
        return {}
    if isinstance(raw, str):
        raw = json.loads(raw)
    return raw if isinstance(raw, dict) else {}


def _parse_jsonb_asset_list(raw) -> list:
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = json.loads(raw)
    if isinstance(raw, list):
        return raw
    return []


def _build_assets_by_id(items: list) -> dict[int, dict]:
    by_id: dict[int, dict] = {}
    for row in items:
        if not isinstance(row, dict):
            continue
        rid = row.get("id")
        if rid is None:
            continue
        try:
            by_id[int(rid)] = row
        except (TypeError, ValueError):
            continue
    return by_id


def _set_worker_bundle(ref: dict, items: list, fp: str) -> None:
    _worker_bundle["fingerprint"] = fp
    _worker_bundle["reference"] = ref
    _worker_bundle["assets_list"] = items
    _worker_bundle["assets_by_id"] = _build_assets_by_id(items)


def _clear_worker_bundle() -> None:
    _worker_bundle["fingerprint"] = None
    _worker_bundle["reference"] = None
    _worker_bundle["assets_list"] = None
    _worker_bundle["assets_by_id"] = None


def _apply_memory_assets(items: list) -> None:
    _memory_fallback["assets_search_list"] = items
    _memory_fallback["assets_search_by_id"] = _build_assets_by_id(items)


def _reset_memory_reference() -> None:
    _memory_fallback["reference"] = None
    _memory_fallback["reference_fingerprint"] = ""
    _memory_fallback["assets_search_list"] = None
    _memory_fallback["assets_search_by_id"] = None


def _sync_worker_bundle_from_redis() -> bool:
    """Подтянуть bundle с Redis в память воркера. False — нет данных или ошибка."""
    if not redis_sync_available():
        return False
    fp = redis_sync_get(REF_FINGERPRINT_KEY)
    if not fp:
        _clear_worker_bundle()
        return False
    if _worker_bundle.get("fingerprint") == fp:
        return True
    blob = redis_sync_get(REF_BUNDLE_KEY)
    if not blob:
        _clear_worker_bundle()
        return False
    try:
        obj = json.loads(blob)
    except json.JSONDecodeError:
        logger.warning("reference:bundle — битый JSON, ключи удалены")
        redis_sync_delete(REF_FINGERPRINT_KEY, REF_BUNDLE_KEY)
        _clear_worker_bundle()
        return False
    ref = obj.get("reference") or {}
    if not isinstance(ref, dict):
        ref = {}
    items = _parse_jsonb_asset_list(obj.get("assets_index"))
    _set_worker_bundle(ref, items, fp)
    return True


def get_reference_fingerprint_str() -> str:
    if redis_sync_available():
        return redis_sync_get(REF_FINGERPRINT_KEY) or ""
    return _memory_fallback.get("reference_fingerprint") or ""


def invalidate_reference_cache() -> None:
    redis_sync_delete(REF_FINGERPRINT_KEY, REF_BUNDLE_KEY, REF_BROKERS_KEY)
    _clear_worker_bundle()
    _reset_memory_reference()
    _memory_fallback["brokers"] = None
    logger.info("Кэш справочника сброшен (Redis + локально)")


def _reset_reference_after_load_failure() -> None:
    if redis_sync_available():
        redis_sync_delete(REF_FINGERPRINT_KEY, REF_BUNDLE_KEY)
    _clear_worker_bundle()
    _reset_memory_reference()


async def _load_reference_into_cache() -> None:
    raw = await rpc_async("get_reference_cache_payload", {})
    bundle = _parse_rpc_dict(raw)
    ref = bundle.get("reference") or {}
    if not isinstance(ref, dict):
        ref = {}
    items = _parse_jsonb_asset_list(bundle.get("assets_index"))
    fp = _reference_fingerprint_for(ref)

    if redis_sync_available():
        payload = json.dumps(
            {"reference": ref, "assets_index": items, "fingerprint": fp},
            default=str,
            ensure_ascii=False,
        )
        if not redis_sync_set(REF_FINGERPRINT_KEY, fp) or not redis_sync_set(REF_BUNDLE_KEY, payload):
            logger.error("Запись справочника в Redis не удалась")
            redis_sync_delete(REF_FINGERPRINT_KEY, REF_BUNDLE_KEY)
            raise RuntimeError("Redis SET reference bundle failed")
    else:
        _memory_fallback["reference"] = ref
        _memory_fallback["reference_fingerprint"] = fp
        _apply_memory_assets(items)

    _set_worker_bundle(ref, items, fp)
    logger.info("Справочник загружен (%s активов)", len(items))


def _reference_exists_in_store() -> bool:
    if redis_sync_available():
        return bool(redis_sync_get(REF_FINGERPRINT_KEY))
    return _memory_fallback.get("reference") is not None


async def _ensure_assets_search_cache() -> None:
    if redis_sync_available():
        if not redis_sync_get(REF_FINGERPRINT_KEY):
            try:
                await _load_reference_into_cache()
            except Exception as e:
                logger.error("Справочник (ensure cache): %s", e, exc_info=True)
            return
        if not _sync_worker_bundle_from_redis():
            try:
                await _load_reference_into_cache()
            except Exception as e:
                logger.error("Повторная загрузка справочника: %s", e, exc_info=True)
        return

    if _memory_fallback.get("assets_search_list") is not None:
        return
    try:
        await _load_reference_into_cache()
    except Exception as e:
        logger.error("Справочник (ensure cache): %s", e, exc_info=True)


async def search_reference_assets(query: str, limit: int = 25) -> list:
    q = (query or "").strip()
    if len(q) < 2:
        return []
    await _ensure_assets_search_cache()
    if redis_sync_available():
        items = _worker_bundle.get("assets_list") or []
    else:
        items = _memory_fallback.get("assets_search_list") or []
    cap = min(max(limit, 1), 100)
    needle = q.lower()
    matches = [
        row
        for row in items
        if isinstance(row, dict)
        and (
            needle in (row.get("name") or "").lower()
            or needle in (row.get("ticker") or "").lower()
        )
    ]
    matches.sort(key=lambda r: (r.get("name") or "").lower())
    return matches[:cap]


def _parse_asset_meta_rpc(raw) -> dict | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = json.loads(raw)
    if isinstance(raw, dict) and raw.get("id") is not None:
        return raw
    return None


async def get_reference_asset_meta(asset_id: int) -> dict | None:
    if not asset_id:
        return None
    aid = int(asset_id)
    await _ensure_assets_search_cache()
    if redis_sync_available():
        by_id = _worker_bundle.get("assets_by_id") or {}
    else:
        by_id = _memory_fallback.get("assets_search_by_id") or {}
    cached = by_id.get(aid)
    if cached is not None:
        return dict(cached)
    return _parse_asset_meta_rpc(await rpc_async("get_reference_asset_meta", {"p_asset_id": aid}))


def _parse_asset_splits_rpc(raw) -> list:
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


async def get_reference_asset_splits(asset_id: int) -> list:
    if not asset_id:
        return []
    raw = await rpc_async("get_asset_splits", {"p_asset_id": int(asset_id)})
    return _parse_asset_splits_rpc(raw)


async def get_reference_data_cached():
    if redis_sync_available():
        if not redis_sync_get(REF_FINGERPRINT_KEY):
            try:
                await _load_reference_into_cache()
            except Exception as e:
                logger.error("Не удалось загрузить справочник по требованию: %s", e, exc_info=True)
                _reset_reference_after_load_failure()
            return _worker_bundle.get("reference") or {}
        if not _sync_worker_bundle_from_redis():
            try:
                await _load_reference_into_cache()
            except Exception as e:
                logger.error("Не удалось синхронизировать справочник из Redis: %s", e, exc_info=True)
                _reset_reference_after_load_failure()
        return _worker_bundle.get("reference") or {}

    if _memory_fallback["reference"] is None:
        try:
            await _load_reference_into_cache()
        except Exception as e:
            logger.error("Не удалось загрузить справочник по требованию: %s", e, exc_info=True)
            _reset_reference_after_load_failure()
    return _memory_fallback["reference"] or {}


async def init_reference_data_async():
    if _reference_exists_in_store():
        logger.debug("Справочник уже в Redis/памяти — пропуск загрузки при старте")
        return

    try:
        logger.info("Загрузка справочника при старте сервера")
        await asyncio.wait_for(
            _load_reference_into_cache(),
            timeout=30.0,
        )
        logger.info("Справочник успешно загружен")
    except asyncio.TimeoutError:
        logger.error("Таймаут загрузки справочника при старте (более 30 с)")
        _reset_reference_after_load_failure()
    except Exception as e:
        logger.error("Не удалось загрузить справочник при старте: %s", e, exc_info=True)
        _reset_reference_after_load_failure()


async def get_brokers():
    return await table_select_async("brokers", select="id, name", order={"column": "id"})


async def get_brokers_cached():
    if redis_sync_available():
        s = redis_sync_get(REF_BROKERS_KEY)
        if s:
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                redis_sync_delete(REF_BROKERS_KEY)
        try:
            rows = await get_brokers()
        except Exception as e:
            logger.error("Не удалось загрузить список брокеров: %s", e, exc_info=True)
            return []
        redis_sync_set(REF_BROKERS_KEY, json.dumps(rows, default=str, ensure_ascii=False))
        return rows

    if _memory_fallback["brokers"] is None:
        logger.warning("Кэш брокеров пуст, загрузка по требованию")
        try:
            _memory_fallback["brokers"] = await get_brokers()
        except Exception as e:
            logger.error("Не удалось загрузить брокеров по требованию: %s", e, exc_info=True)
            _memory_fallback["brokers"] = []
    return _memory_fallback["brokers"]


async def init_brokers_async():
    if redis_sync_available() and redis_sync_get(REF_BROKERS_KEY):
        logger.debug("Брокеры уже в Redis, пропуск загрузки")
        return
    if not redis_sync_available() and _memory_fallback.get("brokers"):
        logger.debug("Брокеры уже в памяти, пропуск загрузки")
        return

    try:
        logger.info("Загрузка брокеров при старте сервера")
        rows = await asyncio.wait_for(get_brokers(), timeout=10.0) or []
        if redis_sync_available():
            redis_sync_set(REF_BROKERS_KEY, json.dumps(rows, default=str, ensure_ascii=False))
        else:
            _memory_fallback["brokers"] = rows
        logger.info("Брокеры загружены, записей: %s", len(rows))
    except asyncio.TimeoutError:
        logger.error("Таймаут загрузки брокеров при старте (более 10 с)")
        if not redis_sync_available():
            _memory_fallback["brokers"] = []
    except Exception as e:
        logger.error("Не удалось загрузить брокеров при старте: %s", e, exc_info=True)
        if not redis_sync_available():
            _memory_fallback["brokers"] = []
