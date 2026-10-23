"""
Доменный сервис для работы с соединениями пользователей с брокерами.

Токен брокера хранится зашифрованным (см. app.core.broker_secrets) и наружу не отдаётся:
в API уходит только маска. Расшифровывает токен только воркер импорта.
"""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.broker_secrets import decrypt_token, encrypt_token, mask_token, token_fingerprint
from app.domain.services.task_service import TRIGGER_MANUAL, create_import_task
from app.infrastructure.database.database_service import (
    table_select_async, table_insert_async, table_update_async, table_delete_async,
)
from app.infrastructure.database.repositories.portfolio_repository import PortfolioRepository

_portfolio_repository = PortfolioRepository()

# Статусы последней синхронизации (user_broker_connections.last_sync_status)
SYNC_STATUS_OK = "ok"
SYNC_STATUS_ERROR = "error"
SYNC_STATUS_TOKEN_INVALID = "token_invalid"

_ACTIVE_TASK_STATUSES = ["pending", "processing"]


async def _portfolio_ids_for_user(user_id_str: str) -> list:
    rows = await table_select_async(
        "portfolios",
        select="id",
        filters={"user_id": user_id_str},
        limit=10000,
    ) or []
    return [r["id"] for r in rows if r.get("id") is not None]


async def _connections_for_portfolios(pids: list, select: str) -> list:
    if not pids:
        return []
    return await table_select_async(
        "user_broker_connections",
        select=select,
        in_filters={"portfolio_id": pids},
        order={"column": "last_sync_at", "desc": True},
        limit=1000,
    ) or []


async def get_user_portfolio_connections(user_id: str):
    """Возвращает dict: { portfolio_id: {'connection_id', 'broker_id', 'has_token'} } (без самого токена)."""
    user_id_str = str(user_id) if user_id else None
    pids = await _portfolio_ids_for_user(user_id_str)
    rows = await _connections_for_portfolios(pids, "id, portfolio_id, broker_id, api_key, last_sync_at")

    by_portfolio = {}
    for r in rows:
        pid = r.get("portfolio_id")
        if pid and pid not in by_portfolio:
            by_portfolio[pid] = {
                "connection_id": r.get("id"),
                "broker_id": r.get("broker_id"),
                "has_token": bool(r.get("api_key")),
            }
    return by_portfolio


def _public_connection(row: dict, portfolio_names: dict, active_tasks: dict) -> dict:
    """Соединение в виде для API: токен заменён маской."""
    try:
        token_mask = mask_token(decrypt_token(row.get("api_key")))
        token_readable = bool(row.get("api_key"))
    except Exception:
        token_mask, token_readable = None, False
    task = active_tasks.get(row.get("portfolio_id"))
    return {
        "id": row.get("id"),
        "portfolio_id": row.get("portfolio_id"),
        "portfolio_name": portfolio_names.get(row.get("portfolio_id")),
        "broker_id": row.get("broker_id"),
        "token_mask": token_mask,
        "has_token": token_readable,
        "auto_sync": bool(row.get("auto_sync", True)),
        "last_sync_at": row.get("last_sync_at"),
        "last_sync_attempt_at": row.get("last_sync_attempt_at"),
        "last_sync_status": row.get("last_sync_status"),
        "last_sync_error": row.get("last_sync_error"),
        "last_sync_summary": row.get("last_sync_summary"),
        "created_at": row.get("created_at"),
        "active_task": (
            {"task_id": task.get("id"), "status": task.get("status"), "progress": task.get("progress")}
            if task else None
        ),
    }


async def list_user_broker_connections(user_id) -> List[Dict[str, Any]]:
    """Подключения брокеров пользователя для раздела «Подключения» (без токенов)."""
    user_id_str = str(user_id) if user_id else None
    portfolios = await table_select_async(
        "portfolios", select="id, name", filters={"user_id": user_id_str}, limit=10000,
    ) or []
    names = {p["id"]: p.get("name") for p in portfolios}
    rows = await _connections_for_portfolios(
        list(names),
        "id, portfolio_id, broker_id, api_key, auto_sync, last_sync_at, last_sync_attempt_at, "
        "last_sync_status, last_sync_error, last_sync_summary, created_at",
    )
    if not rows:
        return []
    tasks = await table_select_async(
        "import_tasks",
        select="id, portfolio_id, status, progress, created_at",
        in_filters={"portfolio_id": [r["portfolio_id"] for r in rows], "status": _ACTIVE_TASK_STATUSES},
        order={"column": "created_at", "desc": True},
        limit=1000,
    ) or []
    active = {}
    for t in tasks:
        active.setdefault(t["portfolio_id"], t)
    return [_public_connection(r, names, active) for r in rows]


async def get_user_connection(user_id, connection_id: int) -> Optional[dict]:
    """Строка соединения, если оно принадлежит пользователю (внутреннее использование: с токеном)."""
    rows = await table_select_async(
        "user_broker_connections", select="*", filters={"id": connection_id}, limit=1,
    )
    if not rows:
        return None
    conn = rows[0]
    portfolio = await _portfolio_repository.get_by_id(conn["portfolio_id"])
    if not portfolio or str(portfolio.get("user_id")) != str(user_id):
        return None
    return conn


async def get_connection_for_portfolio(portfolio_id: int, broker_id: Optional[int] = None) -> Optional[dict]:
    filters = {"portfolio_id": portfolio_id}
    if broker_id is not None:
        filters["broker_id"] = int(broker_id)
    rows = await table_select_async(
        "user_broker_connections",
        select="*",
        filters=filters,
        order={"column": "last_sync_at", "desc": True},
        limit=1,
    )
    return rows[0] if rows else None


async def get_connection_token(portfolio_id: int, broker_id: Optional[int] = None) -> Optional[str]:
    """Расшифрованный токен подключения портфеля (только для воркера импорта).

    BrokerTokenUnavailable — если токен сохранён, но не расшифровывается (сменился ключ).
    """
    conn = await get_connection_for_portfolio(portfolio_id, broker_id)
    if not conn:
        return None
    return decrypt_token(conn.get("api_key"))


async def _find_connection_by_token(pids: list, broker_id: int, broker_token: str) -> Optional[dict]:
    # Пустой фильтр table_select_async пропускает — без отпечатка искать нельзя
    if not pids or not token_fingerprint(broker_token):
        return None
    rows = await table_select_async(
        "user_broker_connections",
        select="id, portfolio_id, broker_id",
        filters={"broker_id": broker_id, "api_key_hash": token_fingerprint(broker_token)},
        in_filters={"portfolio_id": pids},
        limit=1,
    )
    if not rows:
        # Токены, сохранённые до шифрования (до миграции init_db)
        rows = await table_select_async(
            "user_broker_connections",
            select="id, portfolio_id, broker_id",
            filters={"broker_id": broker_id, "api_key": broker_token},
            in_filters={"portfolio_id": pids},
            limit=1,
        )
    return rows[0] if rows else None


async def check_broker_token_exists(user_id: str, broker_id: int, broker_token: str) -> dict:
    """Проверяет, используется ли уже указанный токен брокера у пользователя."""
    user_id_str = str(user_id) if user_id else None
    pids = await _portfolio_ids_for_user(user_id_str)

    existing_connection = await _find_connection_by_token(pids, broker_id, broker_token)
    if existing_connection:
        portfolio_id = existing_connection.get("portfolio_id")
        portfolio = await _portfolio_repository.get_by_id(portfolio_id)

        if not portfolio:
            await table_delete_async("user_broker_connections", filters={"id": existing_connection["id"]})
            return {"exists": False, "portfolio_id": None, "portfolio_name": None}

        return {
            "exists": True,
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.get("name")
        }

    active_tasks = []
    if pids and token_fingerprint(broker_token):
        active_tasks = await table_select_async(
            "import_tasks",
            select="portfolio_id, portfolio_name, status",
            filters={"broker_id": broker_id, "broker_token_hash": token_fingerprint(broker_token)},
            in_filters={"portfolio_id": pids, "status": _ACTIVE_TASK_STATUSES},
            limit=1,
        ) or []

    if active_tasks:
        task = active_tasks[0]
        return {
            "exists": True,
            "portfolio_id": task.get("portfolio_id"),
            "portfolio_name": task.get("portfolio_name"),
            "task_status": task.get("status")
        }

    return {"exists": False, "portfolio_id": None, "portfolio_name": None}


async def check_portfolio_broker_conflict(user_id: str, broker_id: int, portfolio_id: int) -> dict | None:
    """Проверяет, не привязан ли портфель к другому брокеру."""
    user_id_str = str(user_id) if user_id else None

    connections = await get_user_portfolio_connections(user_id_str)
    if not connections:
        return None

    conn = connections.get(portfolio_id)
    if conn and conn["broker_id"] != broker_id:
        return {
            "portfolio_id": portfolio_id,
            "connected_broker_id": conn["broker_id"],
        }

    portfolio = await _portfolio_repository.get_by_id(portfolio_id)
    if portfolio:
        parent_id = portfolio.get("parent_portfolio_id")
        visited = {portfolio_id}
        while parent_id and parent_id not in visited:
            visited.add(parent_id)
            parent_conn = connections.get(parent_id)
            if parent_conn and parent_conn["broker_id"] != broker_id:
                return {
                    "portfolio_id": parent_id,
                    "connected_broker_id": parent_conn["broker_id"],
                }
            parent = await _portfolio_repository.get_by_id(parent_id)
            parent_id = parent.get("parent_portfolio_id") if parent else None

    return None


def _token_columns(api_key: Optional[str]) -> dict:
    return {"api_key": encrypt_token(api_key), "api_key_hash": token_fingerprint(api_key)}


async def upsert_broker_connection(
    user_id,
    broker_id: int,
    portfolio_id: int,
    api_key: Optional[str] = None,
    sync_summary: Optional[dict] = None,
):
    """Создаёт или обновляет соединение с брокером после успешного импорта.

    api_key пустой — токен не меняется (синхронизация по уже сохранённому токену).
    """
    user_id_str = str(user_id) if user_id else None

    portfolio = await _portfolio_repository.get_by_id(portfolio_id)
    if not portfolio or str(portfolio.get("user_id")) != user_id_str:
        raise ValueError("Портфель не найден или не принадлежит пользователю")

    now = datetime.utcnow().replace(microsecond=0)
    conn_data = {
        "broker_id": broker_id,
        "portfolio_id": portfolio_id,
        "last_sync_at": now,
        "last_sync_attempt_at": now,
        "last_sync_status": SYNC_STATUS_OK,
        "last_sync_error": None,
    }
    if sync_summary is not None:
        conn_data["last_sync_summary"] = sync_summary
    if (api_key or "").strip():
        conn_data.update(_token_columns(api_key))

    existing_conn = await table_select_async(
        "user_broker_connections",
        select="id",
        filters={"broker_id": broker_id, "portfolio_id": portfolio_id}
    )

    if existing_conn:
        await table_update_async("user_broker_connections", conn_data, filters={"id": existing_conn[0]["id"]})
        return existing_conn[0]["id"]
    if "api_key" not in conn_data:
        # Синхронизация по сохранённому токену, а пользователь тем временем отключил брокера —
        # подключение без токена не воссоздаём
        return None
    result = await table_insert_async("user_broker_connections", conn_data)
    return result[0]["id"] if result else None


async def record_sync_failure(portfolio_id: int, broker_id: int, status: str, error: str) -> None:
    """Отмечает неудачную синхронизацию у подключения (если оно есть)."""
    await table_update_async(
        "user_broker_connections",
        {
            "last_sync_status": status,
            "last_sync_error": error,
            "last_sync_attempt_at": datetime.utcnow().replace(microsecond=0),
        },
        filters={"portfolio_id": portfolio_id, "broker_id": int(broker_id)},
    )


async def replace_connection_token(user_id, connection_id: int, api_key: str) -> Optional[dict]:
    """Новый токен для подключения (старый отозван или истёк)."""
    conn = await get_user_connection(user_id, connection_id)
    if not conn:
        return None
    data = _token_columns(api_key)
    data.update({"last_sync_status": None, "last_sync_error": None})
    await table_update_async("user_broker_connections", data, filters={"id": connection_id})
    return conn


async def set_connection_auto_sync(user_id, connection_id: int, enabled: bool) -> Optional[dict]:
    conn = await get_user_connection(user_id, connection_id)
    if not conn:
        return None
    await table_update_async(
        "user_broker_connections", {"auto_sync": bool(enabled)}, filters={"id": connection_id},
    )
    return conn


async def delete_connection(user_id, connection_id: int) -> Optional[dict]:
    """Отключает брокера: токен удаляется, данные портфеля остаются."""
    conn = await get_user_connection(user_id, connection_id)
    if not conn:
        return None
    await table_delete_async("user_broker_connections", filters={"id": connection_id})
    # Задача из очереди иначе подключила бы брокера заново
    await table_update_async(
        "import_tasks",
        {"status": "cancelled", "broker_token": None, "completed_at": datetime.utcnow().replace(microsecond=0)},
        filters={"portfolio_id": conn["portfolio_id"], "status": "pending"},
    )
    return conn


async def validate_broker_token(broker_id: int, token: str) -> List[Dict[str, Any]]:
    """Проверяет токен у брокера, ничего не импортируя. Возвращает счета, которые будут загружены.

    Ошибки брокера пробрасываются как есть — их разбирает classify_broker_error.
    """
    from app.constants import BrokerID

    token = (token or "").strip()
    if int(broker_id) == BrokerID.TINKOFF:
        from app.infrastructure.external.brokers.tinkoff import list_tinkoff_accounts
        return await asyncio.to_thread(list_tinkoff_accounts, token)
    if int(broker_id) == BrokerID.BKS:
        from app.infrastructure.external.brokers.bks import list_bks_accounts
        return await asyncio.to_thread(list_bks_accounts, token)
    raise ValueError(f"Импорт для брокера {broker_id} не поддерживается")


async def enqueue_connection_syncs(
    user_id,
    portfolio_ids: Optional[List[int]] = None,
    trigger: str = TRIGGER_MANUAL,
    include_token_invalid: bool = False,
) -> List[Dict[str, Any]]:
    """Ставит синхронизацию подключённых портфелей по сохранённым токенам.

    Токен в задачу не копируется — воркер берёт его из подключения.
    Подключения, у которых брокер отклонил токен, пропускаются (skipped='token_invalid'):
    без нового токена задача заведомо упадёт.
    """
    connections = await list_user_broker_connections(user_id)
    wanted = {int(p) for p in portfolio_ids} if portfolio_ids is not None else None
    results = []
    for conn in connections:
        pid = conn["portfolio_id"]
        if wanted is not None and pid not in wanted:
            continue
        entry = {"portfolio_id": pid, "portfolio_name": conn.get("portfolio_name"), "connection_id": conn["id"]}
        if not conn["has_token"]:
            results.append({**entry, "skipped": "no_token"})
            continue
        if conn.get("last_sync_status") == SYNC_STATUS_TOKEN_INVALID and not include_token_invalid:
            results.append({**entry, "skipped": SYNC_STATUS_TOKEN_INVALID})
            continue
        task = await create_import_task(
            user_id=user_id,
            broker_id=int(conn["broker_id"]),
            broker_token=None,
            portfolio_id=pid,
            priority=1 if trigger == TRIGGER_MANUAL else 0,
            trigger=trigger,
        )
        if not task:
            results.append({**entry, "skipped": "error"})
            continue
        results.append({
            **entry,
            "task_id": task["id"],
            "status": task.get("status"),
            "already_active": bool(task.get("already_active")),
        })
    return results
