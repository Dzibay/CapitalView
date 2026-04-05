"""
Доменный сервис для работы с транзакциями.
"""
from app.infrastructure.database.repositories.transaction_repository import TransactionRepository

_transaction_repository = TransactionRepository()


async def get_transactions(user_id, portfolio_id=None, asset_name=None, start_date=None, end_date=None, limit=1000):
    """Получает транзакции пользователя с фильтрацией в SQL."""
    return await _transaction_repository.get_transactions(
        user_id, portfolio_id, asset_name, start_date, end_date, limit,
    )


async def delete_transactions_batch(transaction_ids: list[int]):
    """Удаляет несколько транзакций батчем и пересчитывает связанные данные."""
    if not transaction_ids:
        return {"success": False, "error": "Список ID транзакций пуст", "deleted_count": 0}

    delete_result = await _transaction_repository.delete_transactions_batch(transaction_ids)

    if not delete_result or delete_result.get("success") is False:
        error_msg = delete_result.get("error", "Неизвестная ошибка") if delete_result else "Ошибка при удалении транзакций"
        raise Exception(f"Ошибка при batch удалении транзакций: {error_msg}")

    return delete_result
