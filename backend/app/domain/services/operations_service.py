"""
Доменный сервис для работы с денежными операциями.
Перенесено из app/services/operations_service.py
"""
from app.infrastructure.database.supabase_service import rpc


def get_operations(user_id, portfolio_id=None, start_date=None, end_date=None, limit=1000):
    """
    Получает операции пользователя с опциональной фильтрацией.
    
    Args:
        user_id: ID пользователя
        portfolio_id: Фильтр по ID портфеля (опционально)
        start_date: Начальная дата периода (опционально)
        end_date: Конечная дата периода (опционально)
        limit: Лимит записей (по умолчанию 1000)
    
    Returns:
        Список операций с примененными фильтрами
    """
    params = {
        "p_user_id": user_id,
        "p_portfolio_id": portfolio_id,
        "p_start_date": start_date,
        "p_end_date": end_date,
        "p_limit": limit
    }
    
    # Убираем None значения из параметров
    params = {k: v for k, v in params.items() if v is not None}
    
    operations = rpc("get_cash_operations", params) or []
    return operations
