"""
Доменный сервис для работы с денежными операциями.
Поддерживает все типы операций: Buy, Sell, Dividend, Coupon, Commission, Tax, Deposit, Withdraw, Other.
"""
from app.infrastructure.database.database_service import rpc
from app.utils.date import normalize_date_to_string
from typing import List
from app.core.logging import get_logger
from app.infrastructure.database.repositories.portfolio_asset_repository import PortfolioAssetRepository
from app.infrastructure.database.repositories.asset_repository import AssetRepository

logger = get_logger(__name__)

# Создаем экземпляры репозиториев для использования во всех функциях
_portfolio_asset_repository = PortfolioAssetRepository()
_asset_repository = AssetRepository()


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


def apply_operations(
    *,
    user_id: str,
    operations: List[dict],
) -> dict:
    """
    Универсальная сборка payload под SQL `apply_operations_batch`.
    Поддерживает:
    - cash операции (Dividend/Coupon/Commission/Tax/Deposit/Withdraw/Other)
    - transaction операции (Buy/Sell/Redemption)
    - опцию create_deposit_operation для Buy, Commission, Tax (добавляет Deposit в тот же apply-оперант).
    """
    if not operations:
        raise ValueError("operations не может быть пустым")

    p_operations: list[dict] = []

    for idx, op in enumerate(operations):
        if not isinstance(op, dict):
            raise ValueError(f"operations[{idx}] должен быть объектом")

        operation_type = int(op.get("operation_type"))
        operation_date = op.get("operation_date")
        operation_date_str = normalize_date_to_string(operation_date, include_time=True) or ""

        if not operation_date_str:
            raise ValueError(f"operations[{idx}].operation_date некорректная")

        portfolio_id = op.get("portfolio_id")
        portfolio_asset_id = op.get("portfolio_asset_id")
        asset_id = op.get("asset_id")

        # Если portfolio_id не передан — достаем из portfolio_asset_id
        if not portfolio_id:
            if portfolio_asset_id:
                pa_data = _portfolio_asset_repository.get_by_id_sync(portfolio_asset_id)
                if pa_data:
                    portfolio_id = pa_data.get("portfolio_id")
            if not portfolio_id:
                raise ValueError(
                    f"operations[{idx}] требует portfolio_id или portfolio_asset_id (чтобы вывести portfolio_id)"
                )

        # transaction: Buy/Sell/Redemption
        if operation_type in (1, 2, 9):
            if not portfolio_asset_id:
                raise ValueError(f"operations[{idx}]: portfolio_asset_id обязателен для transaction")
            if not asset_id:
                raise ValueError(f"operations[{idx}]: asset_id обязателен для transaction")

            quantity = op.get("quantity")
            price = op.get("price")
            if quantity is None or price is None:
                raise ValueError(f"operations[{idx}]: quantity и price обязателены для transaction")

            quantity = float(quantity)
            price = float(price)
            payment = float(price * quantity)

            p_operations.append(
                {
                    "user_id": str(user_id),
                    "portfolio_id": int(portfolio_id),
                    "operation_type": operation_type,
                    "operation_date": operation_date_str,
                    "portfolio_asset_id": int(portfolio_asset_id),
                    "asset_id": int(asset_id),
                    "quantity": quantity,
                    "price": price,
                    "payment": payment,
                    "amount": payment,  # payment или amount одинаковые для buy/sell
                }
            )

            # Deposit операция на сумму buy
            if op.get("create_deposit_operation") is True and operation_type == 1:
                asset_row = _asset_repository.get_by_id_sync(asset_id) or {}
                currency_id = asset_row.get("quote_asset_id") or 1

                p_operations.append(
                    {
                        "user_id": str(user_id),
                        "portfolio_id": int(portfolio_id),
                        "operation_type": 5,  # Deposit
                        "operation_date": operation_date_str,
                        "amount": abs(payment),
                        "currency_id": int(currency_id),
                        "asset_id": int(asset_id),
                        "portfolio_asset_id": int(portfolio_asset_id),
                        "dividend_yield": None,
                    }
                )

        else:
            # cash
            amount = op.get("amount")
            if amount is None:
                raise ValueError(f"operations[{idx}]: amount обязателен для cash-операции")
            amount = float(amount)
            if amount == 0:
                raise ValueError(f"operations[{idx}]: amount не может быть равен 0")

            currency_id = op.get("currency_id") or 1
            dividend_yield = op.get("dividend_yield")

            p_operations.append(
                {
                    "user_id": str(user_id),
                    "portfolio_id": int(portfolio_id),
                    "operation_type": operation_type,
                    "operation_date": operation_date_str,
                    "amount": amount,
                    "currency_id": int(currency_id),
                    "asset_id": int(asset_id) if asset_id else None,
                    "portfolio_asset_id": int(portfolio_asset_id) if portfolio_asset_id else None,
                    "dividend_yield": dividend_yield,
                }
            )

            # Deposit-операция для Commission/Tax
            if op.get("create_deposit_operation") is True and operation_type in (7, 8):
                if not portfolio_asset_id:
                    raise ValueError(
                        f"operations[{idx}]: portfolio_asset_id обязателен для create_deposit_operation (Commission/Tax)"
                    )

                # Если asset_id не передан — получаем из portfolio_asset
                if not asset_id:
                    pa_data = _portfolio_asset_repository.get_by_id_sync(portfolio_asset_id) or {}
                    asset_id_for_deposit = pa_data.get("asset_id")
                else:
                    asset_id_for_deposit = asset_id

                if not asset_id_for_deposit:
                    raise ValueError(
                        f"operations[{idx}]: не удалось определить asset_id для Deposit операции (Commission/Tax)"
                    )

                p_operations.append(
                    {
                        "user_id": str(user_id),
                        "portfolio_id": int(portfolio_id),
                        "operation_type": 5,  # Deposit
                        "operation_date": operation_date_str,
                        "amount": abs(amount),
                        "currency_id": 1,  # Deposit для Commission/Tax всегда в RUB (чтобы не было конвертаций)
                        "asset_id": int(asset_id_for_deposit),
                        "portfolio_asset_id": int(portfolio_asset_id),
                        "dividend_yield": None,
                    }
                )

    result = rpc("apply_operations_batch", {"p_operations": p_operations})
    if not result or result.get("inserted_count", 0) == 0:
        failed = result.get("failed_operations", []) if result else []
        error_msg = failed[0].get("error", "Unknown error") if failed else "apply_operations_batch failed"
        raise Exception(error_msg)

    return result


def update_operations_batch(updates: List[dict]) -> dict:
    """
    Батчевое обновление операций (дата/сумма/quantity/price). В SQL пересчитываются
    fifo_lots, portfolio_assets, portfolio_daily_positions, portfolio_daily_values
    и синхронизируются связанные транзакции.
    updates: список dict с ключами operation_id (обязательно),
             date, amount, quantity, price (опционально).
    """
    if not updates:
        return {"success": True, "updated_count": 0}
    payload = []
    for u in updates:
        op_id = u.get("operation_id")
        if op_id is None:
            continue
        item = {"operation_id": int(op_id)}
        if u.get("date") is not None:
            item["date"] = normalize_date_to_string(u["date"], include_time=True) or u.get("date")
        if u.get("amount") is not None:
            item["amount"] = float(u["amount"])
        if u.get("quantity") is not None:
            item["quantity"] = float(u["quantity"])
        if u.get("price") is not None:
            item["price"] = float(u["price"])
        if len(item) > 1:
            payload.append(item)
    if not payload:
        return {"success": True, "updated_count": 0}
    result = rpc("update_operations_batch", {"p_updates": payload})
    if not result or result.get("success") is False:
        error_msg = result.get("error", "Неизвестная ошибка") if result else "Ошибка при обновлении операций"
        raise Exception(f"Ошибка при batch обновлении операций: {error_msg}")
    return result


def delete_operations_batch(operation_ids: list[int]):
    """
    Удаляет несколько операций батчем и пересчитывает историю портфелей.
    SQL функция delete_operations_batch выполняет:
    - Удаление операций из cash_operations
    - Обновление истории портфелей с минимальной даты удаленных операций
    """
    if not operation_ids:
        return {"success": False, "error": "Список ID операций пуст", "deleted_count": 0}
    
    # Вызываем RPC функцию для batch удаления
    delete_result = rpc("delete_operations_batch", {"p_operation_ids": operation_ids})
    
    if not delete_result or delete_result.get("success") is False:
        error_msg = delete_result.get("error", "Неизвестная ошибка") if delete_result else "Ошибка при удалении операций"
        raise Exception(f"Ошибка при batch удалении операций: {error_msg}")
    
    return delete_result
