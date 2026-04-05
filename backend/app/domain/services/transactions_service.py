"""
Доменный сервис для работы с транзакциями.
"""
from app.infrastructure.database.database_service import rpc_async


async def get_transactions(user_id, portfolio_id=None, asset_name=None, start_date=None, end_date=None, limit=1000):
    """Получает транзакции пользователя с фильтрацией в SQL."""
    params = {
        "p_user_id": user_id,
        "p_limit": limit or 1000
    }
    if portfolio_id:
        params["p_portfolio_id"] = portfolio_id
    if asset_name:
        params["p_asset_name"] = asset_name
    if start_date:
        params["p_start_date"] = start_date
    if end_date:
        params["p_end_date"] = end_date

    return await rpc_async("get_transactions", params) or []


async def delete_transactions_batch(transaction_ids: list[int]):
    """Удаляет несколько транзакций батчем и пересчитывает связанные данные."""
    if not transaction_ids:
        return {"success": False, "error": "Список ID транзакций пуст", "deleted_count": 0}

    delete_result = await rpc_async("delete_transactions_batch", {"p_transaction_ids": transaction_ids})

    if not delete_result or delete_result.get("success") is False:
        error_msg = delete_result.get("error", "Неизвестная ошибка") if delete_result else "Ошибка при удалении транзакций"
        raise Exception(f"Ошибка при batch удалении транзакций: {error_msg}")

    return delete_result
