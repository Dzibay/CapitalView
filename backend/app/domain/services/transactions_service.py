"""
Доменный сервис для работы с транзакциями.
Оптимизировано: фильтрация в SQL, кэширование operations_type, меньше round-trip.
"""
from typing import Optional
from datetime import datetime
from app.infrastructure.database.database_service import rpc, table_select
from app.utils.date import normalize_date_to_string
from app.core.logging import get_logger
from app.infrastructure.database.repositories.transaction_repository import TransactionRepository
from app.infrastructure.database.repositories.portfolio_asset_repository import PortfolioAssetRepository
from app.infrastructure.database.repositories.asset_repository import AssetRepository
from app.infrastructure.database.repositories.operation_repository import OperationRepository

logger = get_logger(__name__)

_transaction_repository = TransactionRepository()
_portfolio_asset_repository = PortfolioAssetRepository()
_asset_repository = AssetRepository()
_operation_repository = OperationRepository()

# Кэш для operations_type (статическая таблица ~10 строк)
_operations_type_map: dict = None


def _get_operations_type_map() -> dict:
    global _operations_type_map
    if _operations_type_map is None:
        op_types = table_select("operations_type", select="id, name") or []
        _operations_type_map = {o["name"].lower(): o["id"] for o in op_types if o.get("name")}
    return _operations_type_map


def get_transactions(user_id, portfolio_id=None, asset_name=None, start_date=None, end_date=None, limit=1000):
    """
    Получает транзакции пользователя с фильтрацией в SQL (не в Python).
    """
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

    transactions = rpc("get_user_transactions", params) or []
    return transactions


def create_transaction(
    *,
    user_id: int,
    portfolio_asset_id: int,
    asset_id: int,
    transaction_type: int,   # 1 = buy, 2 = sell, 3 = redemption
    quantity: float,
    price: float,
    transaction_date: str,
    create_deposit_operation: bool = False
):
    """
    Единственный разрешённый способ создания транзакций.
    Использует apply_operations_batch (создаёт транзакции, cash_operations, цены, missed payouts в БД).
    FIFO + realized_pnl считаются в БД.
    """
    transaction_date_str = normalize_date_to_string(transaction_date, include_time=True) or ""
    payment = float(price * quantity)

    op_type_names = {1: "Buy", 2: "Sell", 3: "Redemption"}
    op_name = op_type_names.get(transaction_type, "Buy")
    op_type_map = _get_operations_type_map()
    operation_type_id = op_type_map.get(op_name.lower())
    if not operation_type_id:
        raise Exception(f"Тип операции '{op_name}' не найден в operations_type")

    pa_data = _portfolio_asset_repository.get_by_id_sync(portfolio_asset_id)
    if not pa_data:
        raise Exception(f"Портфельный актив {portfolio_asset_id} не найден")
    portfolio_id = pa_data.get("portfolio_id")

    op_payload = [{
        "user_id": str(user_id),
        "portfolio_id": portfolio_id,
        "operation_type": operation_type_id,
        "operation_date": transaction_date_str,
        "portfolio_asset_id": portfolio_asset_id,
        "quantity": float(quantity),
        "price": float(price),
        "payment": payment,
        "amount": payment,
    }]
    result = rpc("apply_operations_batch", {"p_operations": op_payload})

    if not result or result.get("inserted_count", 0) == 0:
        failed = result.get("failed_operations", [])
        error_msg = failed[0].get("error", "Unknown error") if failed else "apply_operations_batch failed"
        raise Exception(f"Ошибка создания транзакции: {error_msg}")

    tx_ids = result.get("transaction_ids", [])
    if not tx_ids or len(tx_ids) == 0:
        raise Exception("Транзакция не была создана")
    tx_id = tx_ids[0]

    # Цены и check_missed_payouts теперь обрабатываются внутри apply_operations_batch

    # Создаем операцию пополнения, если запрошено (только для покупки)
    if create_deposit_operation and transaction_type == 1:
        from app.domain.services.operations_service import create_operation

        if portfolio_id is not None:
            deposit_amount = float(quantity * price)
            asset_row = _asset_repository.get_by_id_sync(asset_id)
            currency_id = (asset_row.get("quote_asset_id") or 1) if asset_row else 1

            try:
                create_operation(
                    user_id=str(user_id),
                    portfolio_id=portfolio_id,
                    operation_type=5,  # Deposit
                    amount=deposit_amount,
                    currency_id=currency_id,
                    operation_date=transaction_date_str,
                    asset_id=asset_id,
                    portfolio_asset_id=portfolio_asset_id
                )
            except Exception as e:
                logger.warning(f"Ошибка при создании операции пополнения для транзакции {tx_id}: {e}", exc_info=True)

    return tx_id


def update_transaction(
    *,
    transaction_id: int,
    user_id: int,
    portfolio_asset_id: Optional[int] = None,
    asset_id: Optional[int] = None,
    transaction_type: Optional[int] = None,
    quantity: Optional[float] = None,
    price: Optional[float] = None,
    transaction_date: Optional[str] = None,
    update_related_deposit: bool = False,
    related_deposit_operation_id: Optional[int] = None,
    related_deposit_amount: Optional[float] = None,
    related_deposit_date: Optional[str] = None,
):
    """
    Обновляет транзакцию через update_operations_batch.
    """
    from app.domain.services import operations_service

    old_tx = _transaction_repository.get_by_id_sync(transaction_id)
    if not old_tx:
        raise Exception(f"Транзакция {transaction_id} не найдена")

    final_quantity = quantity if quantity is not None else old_tx.get("quantity")
    final_price = price if price is not None else old_tx.get("price")
    final_transaction_date = transaction_date if transaction_date is not None else old_tx.get("transaction_date")

    cash_op = _operation_repository.get_by_transaction_id_sync(transaction_id)
    if not cash_op:
        raise Exception(f"Не найдена cash_operation для транзакции {transaction_id}")

    final_amount = float(final_quantity) * float(final_price) if final_quantity and final_price else None

    tx_update = {"operation_id": cash_op["id"]}
    if final_transaction_date is not None:
        tx_update["date"] = normalize_date_to_string(final_transaction_date, include_time=True) or final_transaction_date
    if final_amount is not None:
        tx_update["amount"] = final_amount
    if final_quantity is not None:
        tx_update["quantity"] = float(final_quantity)
    if final_price is not None:
        tx_update["price"] = float(final_price)

    updates = [tx_update]

    if update_related_deposit and related_deposit_operation_id:
        deposit_update = {"operation_id": int(related_deposit_operation_id)}
        dep_date = related_deposit_date or final_transaction_date
        if dep_date is not None:
            deposit_update["date"] = normalize_date_to_string(dep_date, include_time=True) or dep_date
        if related_deposit_amount is not None:
            deposit_update["amount"] = float(related_deposit_amount)
        if len(deposit_update) > 1:
            updates.append(deposit_update)

    result = operations_service.update_operations_batch(updates)
    if result.get("success") is False:
        raise Exception(f"Ошибка обновления транзакции: {result.get('error', 'Неизвестная ошибка')}")

    return transaction_id


def delete_transactions_batch(transaction_ids: list[int]):
    """
    Удаляет несколько транзакций батчем и пересчитывает связанные данные.
    """
    if not transaction_ids:
        return {"success": False, "error": "Список ID транзакций пуст", "deleted_count": 0}
    
    delete_result = rpc("delete_transactions_batch", {"p_transaction_ids": transaction_ids})
    
    if not delete_result or delete_result.get("success") is False:
        error_msg = delete_result.get("error", "Неизвестная ошибка") if delete_result else "Ошибка при удалении транзакций"
        raise Exception(f"Ошибка при batch удалении транзакций: {error_msg}")
    
    return delete_result
