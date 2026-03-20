"""
Доменный сервис для работы с соединениями пользователей с брокерами.
Перенесено из app/services/broker_connections_service.py

Примечание: Использует прямые вызовы к БД для работы с таблицами user_broker_connections и import_tasks,
так как это служебные таблицы, не являющиеся основными доменными сущностями.

Владелец подключения задаётся через portfolios.user_id (колонка user_broker_connections.user_id удалена).
"""
from app.infrastructure.database.database_service import table_select, table_insert, table_update, table_delete
from datetime import datetime
from app.infrastructure.database.repositories.portfolio_repository import PortfolioRepository

# Создаем экземпляр репозитория для использования
_portfolio_repository = PortfolioRepository()


def _portfolio_ids_for_user(user_id_str: str) -> list:
    rows = table_select(
        "portfolios",
        select="id",
        filters={"user_id": user_id_str},
        limit=10000,
    ) or []
    return [r["id"] for r in rows if r.get("id") is not None]


def get_user_portfolio_connections(user_id: str):
    """
    Возвращает dict: { portfolio_id: {'broker_id': ..., 'api_key': ...} }
    Берёт самую свежую запись по last_sync_at для каждого портфеля.
    """
    user_id_str = str(user_id) if user_id else None
    pids = _portfolio_ids_for_user(user_id_str)
    if not pids:
        return {}

    rows = table_select(
        "user_broker_connections",
        select="portfolio_id, broker_id, api_key, last_sync_at",
        in_filters={"portfolio_id": pids},
        order={"column": "last_sync_at", "desc": True},
        limit=1000
    ) or []

    # rows уже отсортированы по last_sync_at DESC — первое попадание и есть самое свежее
    by_portfolio = {}
    for r in rows:
        pid = r.get("portfolio_id")
        if pid and pid not in by_portfolio:
            by_portfolio[pid] = {
                "broker_id": r.get("broker_id"),
                "api_key": r.get("api_key"),
            }
    return by_portfolio


def check_broker_token_exists(user_id: str, broker_id: int, broker_token: str) -> dict:
    """
    Проверяет, используется ли уже указанный токен брокера у пользователя.

    Args:
        user_id: ID пользователя (UUID - str)
        broker_id: ID брокера
        broker_token: Токен брокера для проверки

    Returns:
        dict с ключами:
            - exists: bool - существует ли токен
            - portfolio_id: int | None - ID портфеля, где используется токен
            - portfolio_name: str | None - название портфеля
    """
    user_id_str = str(user_id) if user_id else None

    pids = _portfolio_ids_for_user(user_id_str)
    if pids:
        existing_connection = table_select(
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
        # Получаем название портфеля и проверяем, существует ли портфель
        portfolio = _portfolio_repository.get_by_id_sync(portfolio_id)

        # Если портфель не существует, удаляем запись из user_broker_connections
        # (это может произойти, если портфель был удален, но запись осталась)
        if not portfolio:
            table_delete(
                "user_broker_connections",
                filters={"broker_id": broker_id, "api_key": broker_token, "portfolio_id": portfolio_id}
            )
            # Портфель не существует, токен не используется
            return {
                "exists": False,
                "portfolio_id": None,
                "portfolio_name": None
            }

        portfolio_name = portfolio.get("name")

        return {
            "exists": True,
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio_name
        }

    # Также проверяем в import_tasks (задачи, которые еще не выполнены)
    if pids:
        pending_tasks = table_select(
            "import_tasks",
            select="portfolio_id, portfolio_name, status",
            filters={
                "broker_id": str(broker_id),
                "broker_token": broker_token
            },
            in_filters={"portfolio_id": pids},
            limit=10
        )
    else:
        pending_tasks = None

    # Фильтруем только активные задачи (pending или processing)
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

    return {
        "exists": False,
        "portfolio_id": None,
        "portfolio_name": None
    }


def check_portfolio_broker_conflict(user_id: str, broker_id: int, portfolio_id: int) -> dict | None:
    """
    Проверяет, не привязан ли портфель (или его родитель) к другому брокеру.
    Возвращает None если конфликта нет, иначе dict с информацией о конфликте.
    """
    user_id_str = str(user_id) if user_id else None

    # Получаем все привязки пользователя
    connections = get_user_portfolio_connections(user_id_str)
    if not connections:
        return None

    # Проверяем сам портфель
    conn = connections.get(portfolio_id)
    if conn and conn["broker_id"] != broker_id:
        return {
            "portfolio_id": portfolio_id,
            "connected_broker_id": conn["broker_id"],
        }

    # Проверяем всех предков портфеля (если он дочерний)
    portfolio = _portfolio_repository.get_by_id_sync(portfolio_id)
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
            parent = _portfolio_repository.get_by_id_sync(parent_id)
            parent_id = parent.get("parent_portfolio_id") if parent else None

    return None


def upsert_broker_connection(user_id, broker_id: int, portfolio_id: int, api_key: str):
    """
    Создаёт или обновляет соединение пользователя с брокером для портфеля.

    Args:
        user_id: ID пользователя (UUID - str или UUID объект)
        broker_id: ID брокера
        portfolio_id: ID портфеля
        api_key: API ключ брокера
    """
    user_id_str = str(user_id) if user_id else None

    portfolio = _portfolio_repository.get_by_id_sync(portfolio_id)
    if not portfolio or str(portfolio.get("user_id")) != user_id_str:
        raise ValueError("Портфель не найден или не принадлежит пользователю")

    conn_data = {
        "broker_id": broker_id,
        "portfolio_id": portfolio_id,
        "api_key": api_key,
        "last_sync_at": datetime.utcnow().isoformat(),
    }

    existing_conn = table_select(
        "user_broker_connections",
        select="id",
        filters={"broker_id": broker_id, "portfolio_id": portfolio_id}
    )

    if existing_conn:
        table_update("user_broker_connections", conn_data, filters={"id": existing_conn[0]["id"]})
        return existing_conn[0]["id"]
    else:
        result = table_insert("user_broker_connections", conn_data)
        return result[0]["id"] if result else None
