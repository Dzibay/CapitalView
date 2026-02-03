"""
Сервис для работы с соединениями пользователей с брокерами.
Централизует логику работы с user_broker_connections.
"""
from app.services.supabase_service import table_select, table_insert, table_update
from datetime import datetime


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


def upsert_broker_connection(user_id, broker_id: int, portfolio_id: int, api_key: str):
    """
    Создаёт или обновляет соединение пользователя с брокером для портфеля.
    
    Args:
        user_id: ID пользователя (UUID - str или UUID объект)
        broker_id: ID брокера
        portfolio_id: ID портфеля
        api_key: API ключ брокера
    """
    """
    Создаёт или обновляет соединение пользователя с брокером для портфеля.
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

