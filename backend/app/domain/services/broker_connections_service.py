"""
Доменный сервис для работы с соединениями пользователей с брокерами.
Перенесено из app/services/broker_connections_service.py

Примечание: Использует прямые вызовы к БД для работы с таблицами user_broker_connections и import_tasks,
так как это служебные таблицы, не являющиеся основными доменными сущностями.
"""
from app.infrastructure.database.database_service import table_select, table_insert, table_update, table_delete
from datetime import datetime
from app.infrastructure.database.repositories.portfolio_repository import PortfolioRepository

# Создаем экземпляр репозитория для использования
_portfolio_repository = PortfolioRepository()


def get_user_portfolio_connections(user_id: str):
    """
    Возвращает dict: { portfolio_id: {'broker_id': ..., 'api_key': ...} }
    Берёт самую свежую запись по last_sync_at для каждого портфеля.
    """
    rows = table_select(
        "user_broker_connections",
        select="portfolio_id, broker_id, api_key, last_sync_at",
        filters={"user_id": user_id},
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
    
    # Проверяем в user_broker_connections (уже импортированные портфели)
    existing_connection = table_select(
        "user_broker_connections",
        select="portfolio_id, broker_id, api_key",
        filters={"user_id": user_id_str, "broker_id": broker_id, "api_key": broker_token},
        limit=1
    )
    
    if existing_connection:
        portfolio_id = existing_connection[0].get("portfolio_id")
        # Получаем название портфеля и проверяем, существует ли портфель
        portfolio = _portfolio_repository.get_by_id_sync(portfolio_id)
        
        # Если портфель не существует, удаляем запись из user_broker_connections
        # (это может произойти, если портфель был удален, но запись осталась)
        if not portfolio:
            table_delete(
                "user_broker_connections",
                filters={"user_id": user_id_str, "broker_id": broker_id, "api_key": broker_token}
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
    pending_tasks = table_select(
        "import_tasks",
        select="portfolio_id, portfolio_name, status",
        filters={
            "user_id": user_id_str,
            "broker_id": str(broker_id),
            "broker_token": broker_token
        },
        limit=1
    )
    
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


def upsert_broker_connection(user_id, broker_id: int, portfolio_id: int, api_key: str):
    """
    Создаёт или обновляет соединение пользователя с брокером для портфеля.
    
    Args:
        user_id: ID пользователя (UUID - str или UUID объект)
        broker_id: ID брокера
        portfolio_id: ID портфеля
        api_key: API ключ брокера
    """
    # Преобразуем user_id в строку, если это UUID объект
    user_id_str = str(user_id) if user_id else None
    
    conn_data = {
        "user_id": user_id_str,
        "broker_id": broker_id,
        "portfolio_id": portfolio_id,
        "api_key": api_key,
        "last_sync_at": datetime.utcnow().isoformat(),
    }
    
    existing_conn = table_select(
        "user_broker_connections",
        select="id",
        filters={"user_id": user_id_str, "broker_id": broker_id, "portfolio_id": portfolio_id}
    )
    
    if existing_conn:
        table_update("user_broker_connections", conn_data, filters={"id": existing_conn[0]["id"]})
        return existing_conn[0]["id"]
    else:
        result = table_insert("user_broker_connections", conn_data)
        return result[0]["id"] if result else None
