"""
Доменный сервис для работы с соединениями пользователей с брокерами.
"""
from app.infrastructure.database.database_service import (
    table_select_async, table_insert_async, table_update_async, table_delete_async,
)
from datetime import datetime
from app.infrastructure.database.repositories.portfolio_repository import PortfolioRepository

_portfolio_repository = PortfolioRepository()


async def _portfolio_ids_for_user(user_id_str: str) -> list:
    rows = await table_select_async(
        "portfolios",
        select="id",
        filters={"user_id": user_id_str},
        limit=10000,
    ) or []
    return [r["id"] for r in rows if r.get("id") is not None]


async def get_user_portfolio_connections(user_id: str):
    """Возвращает dict: { portfolio_id: {'broker_id': ..., 'api_key': ...} }"""
    user_id_str = str(user_id) if user_id else None
    pids = await _portfolio_ids_for_user(user_id_str)
    if not pids:
        return {}

    rows = await table_select_async(
        "user_broker_connections",
        select="portfolio_id, broker_id, api_key, last_sync_at",
        in_filters={"portfolio_id": pids},
        order={"column": "last_sync_at", "desc": True},
        limit=1000
    ) or []

    by_portfolio = {}
    for r in rows:
        pid = r.get("portfolio_id")
        if pid and pid not in by_portfolio:
            by_portfolio[pid] = {
                "broker_id": r.get("broker_id"),
                "api_key": r.get("api_key"),
            }
    return by_portfolio


async def check_broker_token_exists(user_id: str, broker_id: int, broker_token: str) -> dict:
    """Проверяет, используется ли уже указанный токен брокера у пользователя."""
    user_id_str = str(user_id) if user_id else None

    pids = await _portfolio_ids_for_user(user_id_str)
    if pids:
        existing_connection = await table_select_async(
            "user_broker_connections",
            select="portfolio_id, broker_id, api_key",
            filters={"broker_id": broker_id, "api_key": broker_token},
            in_filters={"portfolio_id": pids},
            limit=1
        )
    else:
        existing_connection = None

    if existing_connection:
        portfolio_id = existing_connection[0].get("portfolio_id")
        portfolio = await _portfolio_repository.get_by_id(portfolio_id)

        if not portfolio:
            await table_delete_async(
                "user_broker_connections",
                filters={"broker_id": broker_id, "api_key": broker_token, "portfolio_id": portfolio_id}
            )
            return {"exists": False, "portfolio_id": None, "portfolio_name": None}

        return {
            "exists": True,
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.get("name")
        }

    if pids:
        pending_tasks = await table_select_async(
            "import_tasks",
            select="portfolio_id, portfolio_name, status",
            filters={"broker_id": broker_id, "broker_token": broker_token},
            in_filters={"portfolio_id": pids},
            limit=10
        )
    else:
        pending_tasks = None

    active_tasks = [
        task for task in (pending_tasks or [])
        if task.get("status") in ["pending", "processing"]
    ]

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


async def upsert_broker_connection(user_id, broker_id: int, portfolio_id: int, api_key: str):
    """Создаёт или обновляет соединение с брокером для портфеля."""
    user_id_str = str(user_id) if user_id else None

    portfolio = await _portfolio_repository.get_by_id(portfolio_id)
    if not portfolio or str(portfolio.get("user_id")) != user_id_str:
        raise ValueError("Портфель не найден или не принадлежит пользователю")

    conn_data = {
        "broker_id": broker_id,
        "portfolio_id": portfolio_id,
        "api_key": api_key,
        "last_sync_at": datetime.utcnow().isoformat(),
    }

    existing_conn = await table_select_async(
        "user_broker_connections",
        select="id",
        filters={"broker_id": broker_id, "portfolio_id": portfolio_id}
    )

    if existing_conn:
        await table_update_async("user_broker_connections", conn_data, filters={"id": existing_conn[0]["id"]})
        return existing_conn[0]["id"]
    else:
        result = await table_insert_async("user_broker_connections", conn_data)
        return result[0]["id"] if result else None
