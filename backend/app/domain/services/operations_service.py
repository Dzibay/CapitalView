"""
Доменный сервис для работы с денежными операциями.
Поддерживает все типы операций: Buy, Sell, Dividend, Coupon, Commission, Tax, Deposit, Withdraw, Other.
"""
from app.utils.date import normalize_date_to_string
from typing import List
from app.core.logging import get_logger
from app.infrastructure.database.repositories.portfolio_asset_repository import PortfolioAssetRepository
from app.infrastructure.database.repositories.asset_repository import AssetRepository
from app.infrastructure.database.repositories.operation_repository import OperationRepository

logger = get_logger(__name__)


def normalize_cash_operation_amount(operation_type: int, amount: float) -> float:
    """
    Приводит сумму cash-операции к каноническому знаку.

    Расходы (вывод, комиссия, налог) хранятся отрицательными; доходы (дивиденд,
    купон, амортизация как денежная выплата, пополнение) — положительными.

    Тип 10 (Other) не меняем — знак остаётся как ввёл пользователь.
    """
    t = int(operation_type)
    x = float(amount)
    if x == 0:
        return x
    if t in (6, 7, 8):
        return -abs(x)
    if t in (3, 4, 5, 9):
        return abs(x)
    return x


_portfolio_asset_repository = PortfolioAssetRepository()
_asset_repository = AssetRepository()
_operation_repository = OperationRepository()


async def get_operations(user_id, portfolio_id=None, start_date=None, end_date=None, limit=1000):
    """Получает операции пользователя с опциональной фильтрацией."""
    return await _operation_repository.get_user_operations(
        user_id, portfolio_id, start_date, end_date, limit,
    )


async def apply_operations(
    *,
    user_id: str,
    operations: List[dict],
) -> dict:
    """
    Универсальная сборка payload под SQL `apply_operations_batch`.
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

        if not portfolio_id:
            if portfolio_asset_id:
                pa_data = await _portfolio_asset_repository.get_by_id(portfolio_asset_id)
                if pa_data:
                    portfolio_id = pa_data.get("portfolio_id")
            if not portfolio_id:
                raise ValueError(
                    f"operations[{idx}] требует portfolio_id или portfolio_asset_id (чтобы вывести portfolio_id)"
                )

        is_tx_amortization = operation_type == 9 and op.get("quantity") is not None and op.get("price") is not None
        if operation_type in (1, 2) or is_tx_amortization:
            if not portfolio_asset_id:
                raise ValueError(f"operations[{idx}]: portfolio_asset_id обязателен для transaction")
            if not asset_id:
                raise ValueError(f"operations[{idx}]: asset_id обязателен для transaction")

            quantity = float(op.get("quantity"))
            price = float(op.get("price"))
            payment = float(price * quantity)

            tx_po = {
                "user_id": str(user_id),
                "portfolio_id": int(portfolio_id),
                "operation_type": operation_type,
                "operation_date": operation_date_str,
                "portfolio_asset_id": int(portfolio_asset_id),
                "asset_id": int(asset_id),
                "quantity": quantity,
                "price": price,
                "payment": payment,
                "amount": payment,
            }
            if op.get("commission") is not None:
                tx_po["commission"] = float(op["commission"])
            if op.get("commission_rub") is not None:
                tx_po["commission_rub"] = float(op["commission_rub"])
            p_operations.append(tx_po)

            if op.get("create_deposit_operation") is True and operation_type == 1:
                asset_row = await _asset_repository.get_by_id(asset_id) or {}
                currency_id = asset_row.get("quote_asset_id") or 1

                p_operations.append(
                    {
                        "user_id": str(user_id),
                        "portfolio_id": int(portfolio_id),
                        "operation_type": 5,
                        "operation_date": operation_date_str,
                        "amount": abs(payment),
                        "currency_id": int(currency_id),
                        "asset_id": int(asset_id),
                        "portfolio_asset_id": int(portfolio_asset_id),
                        "dividend_yield": None,
                    }
                )

        else:
            amount = op.get("amount")
            if amount is None:
                raise ValueError(f"operations[{idx}]: amount обязателен для cash-операции")
            amount = float(amount)
            if amount == 0:
                raise ValueError(f"operations[{idx}]: amount не может быть равен 0")
            amount = normalize_cash_operation_amount(operation_type, amount)

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

            if op.get("create_deposit_operation") is True and operation_type in (7, 8):
                if not portfolio_asset_id:
                    raise ValueError(
                        f"operations[{idx}]: portfolio_asset_id обязателен для create_deposit_operation (Commission/Tax)"
                    )

                if not asset_id:
                    pa_data = await _portfolio_asset_repository.get_by_id(portfolio_asset_id) or {}
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
                        "operation_type": 5,
                        "operation_date": operation_date_str,
                        "amount": abs(amount),
                        "currency_id": 1,
                        "asset_id": int(asset_id_for_deposit),
                        "portfolio_asset_id": int(portfolio_asset_id),
                        "dividend_yield": None,
                    }
                )

    result = await _operation_repository.apply_operations_batch(p_operations)
    if not result or result.get("inserted_count", 0) == 0:
        failed = result.get("failed_operations", []) if result else []
        error_msg = failed[0].get("error", "Unknown error") if failed else "apply_operations_batch failed"
        raise Exception(error_msg)

    return result


async def update_operations_batch(updates: List[dict]) -> dict:
    """Батчевое обновление операций."""
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
    result = await _operation_repository.update_operations_batch(payload)
    if not result or result.get("success") is False:
        error_msg = result.get("error", "Неизвестная ошибка") if result else "Ошибка при обновлении операций"
        raise Exception(f"Ошибка при batch обновлении операций: {error_msg}")
    return result


async def delete_operations_batch(operation_ids: list[int]):
    """Удаляет несколько операций батчем и пересчитывает историю портфелей."""
    if not operation_ids:
        return {"success": False, "error": "Список ID операций пуст", "deleted_count": 0}

    delete_result = await _operation_repository.delete_operations_batch(operation_ids)

    if not delete_result or delete_result.get("success") is False:
        error_msg = delete_result.get("error", "Неизвестная ошибка") if delete_result else "Ошибка при удалении операций"
        raise Exception(f"Ошибка при batch удалении операций: {error_msg}")

    return delete_result
