"""
Доменный сервис для работы с транзакциями.
Перенесено из app/services/transactions_service.py
"""
from typing import Optional
from datetime import datetime
from app.infrastructure.database.postgres_service import rpc, table_select
from app.utils.date import normalize_date_to_string, normalize_date_to_sql_date
from app.core.logging import get_logger
from app.infrastructure.database.repositories.transaction_repository import TransactionRepository
from app.infrastructure.database.repositories.portfolio_asset_repository import PortfolioAssetRepository
from app.infrastructure.database.repositories.asset_repository import AssetRepository
from app.infrastructure.database.repositories.portfolio_repository import PortfolioRepository

logger = get_logger(__name__)

# Создаем экземпляры репозиториев для использования во всех функциях
_transaction_repository = TransactionRepository()
_portfolio_asset_repository = PortfolioAssetRepository()
_asset_repository = AssetRepository()
_portfolio_repository = PortfolioRepository()


def get_transactions(user_id, portfolio_id=None, asset_name=None, start_date=None, end_date=None, limit=1000):
    """
    Получает транзакции пользователя с опциональной фильтрацией.
    
    Args:
        user_id: ID пользователя
        portfolio_id: Фильтр по ID портфеля (опционально)
        asset_name: Фильтр по названию актива (опционально)
        start_date: Начальная дата периода (опционально)
        end_date: Конечная дата периода (опционально)
        limit: Лимит записей (по умолчанию 1000)
    
    Returns:
        Список транзакций с примененными фильтрами
    """
    # Получаем все транзакции (с увеличенным лимитом для фильтрации)
    params = {
        "p_user_id": user_id,
        "p_limit": limit * 10 if (portfolio_id or asset_name or start_date or end_date) else limit
    }
    transactions = rpc("get_user_transactions", params) or []
    
    # Применяем фильтры на стороне Python
    if portfolio_id:
        transactions = [t for t in transactions if t.get('portfolio_id') == portfolio_id]
    
    if asset_name:
        asset_name_lower = asset_name.lower()
        transactions = [
            t for t in transactions 
            if asset_name_lower in (t.get('asset_name') or '').lower() or 
               asset_name_lower in (t.get('ticker') or '').lower()
        ]
    
    if start_date:
        if isinstance(start_date, str):
            from datetime import datetime
            try:
                start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except:
                pass
        transactions = [
            t for t in transactions 
            if t.get('transaction_date') and t['transaction_date'] >= start_date
        ]
    
    if end_date:
        if isinstance(end_date, str):
            from datetime import datetime
            try:
                end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except:
                pass
        transactions = [
            t for t in transactions 
            if t.get('transaction_date') and t['transaction_date'] <= end_date
        ]
    
    # Применяем финальный лимит
    return transactions[:limit]


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
    Использует apply_operations_batch (создаёт транзакции и cash_operations для Buy/Sell/Redemption).
    FIFO + realized_pnl считаются в БД.
    
    Args:
        create_deposit_operation: Если True и transaction_type=1 (Buy), создает операцию пополнения
    """
    from datetime import datetime

    transaction_date_str = normalize_date_to_string(transaction_date, include_time=True) or ""
    payment = float(price * quantity)

    # Тип операции по типу транзакции: Buy=1, Sell=2, Redemption=3
    op_type_names = {1: "Buy", 2: "Sell", 3: "Redemption"}
    op_name = op_type_names.get(transaction_type, "Buy")
    op_types = table_select("operations_type", select="id, name") or []
    op_type_map = {o["name"].lower(): o["id"] for o in op_types if o.get("name")}
    operation_type_id = op_type_map.get(op_name.lower())
    if not operation_type_id:
        raise Exception(f"Тип операции '{op_name}' не найден в operations_type")

    pa_data = _portfolio_asset_repository.get_by_id_sync(portfolio_asset_id)
    if not pa_data:
        raise Exception(f"Портфельный актив {portfolio_asset_id} не найден")
    portfolio_id = pa_data.get("portfolio_id")

    # 1️⃣ Создаём транзакцию через apply_operations_batch (одна операция Buy/Sell/Redemption)
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

    # 2️⃣ Цена актива (idempotent)
    # Таблица asset_prices не имеет столбца id, первичный ключ составной (asset_id, trade_date)
    trade_date_only = transaction_date_str.split('T')[0]
    existing_price = _asset_repository.get_price_history(asset_id, start_date=trade_date_only, end_date=trade_date_only, limit=1)

    if not existing_price:
        _asset_repository.add_price(asset_id, price, trade_date_only)
        
        # Обновляем последнюю цену актива в asset_latest_prices
        try:
            _asset_repository.update_latest_price(asset_id)
        except Exception as e:
            logger.warning(f"Ошибка при обновлении последней цены актива {asset_id}: {e}", exc_info=True)

    # 3️⃣ Инкрементальные апдейты (БЕЗ глобальных refresh)
    # Примечание: apply_operations_batch уже обновляет историю, но update_portfolio_asset
    # обновляет агрегированные данные актива (quantity, average_price и т.д.)
    rpc("update_portfolio_asset", {"pa_id": portfolio_asset_id})
    
    # 4️⃣ Проверяем неполученные выплаты для созданного актива
    try:
        rpc("check_missed_payouts", {
            "p_portfolio_asset_id": portfolio_asset_id
        })
    except Exception as e:
        logger.warning(f"Ошибка при проверке неполученных выплат для актива {portfolio_asset_id}: {e}", exc_info=True)

    # 4️⃣ Создаем операцию пополнения, если запрошено (только для покупки)
    if create_deposit_operation and transaction_type == 1:
        from app.domain.services.operations_service import create_operation

        if portfolio_id is not None:
            deposit_amount = float(quantity * price)
            
            try:
                create_operation(
                    user_id=str(user_id),
                    portfolio_id=portfolio_id,
                    operation_type=5,  # Deposit
                    amount=deposit_amount,
                    currency_id=1,  # RUB - операция пополнения всегда в рублях, независимо от валюты актива
                    operation_date=transaction_date_str,
                    asset_id=asset_id,  # Привязываем к активу для удаления при удалении актива
                    portfolio_asset_id=portfolio_asset_id  # Привязываем к портфельному активу
                )
            except Exception as e:
                logger.warning(f"Ошибка при создании операции пополнения для транзакции {tx_id}: {e}", exc_info=True)
                # Не прерываем выполнение, так как транзакция уже создана

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
    transaction_date: Optional[str] = None
):
    """
    Обновляет существующую транзакцию.
    Удаляет старую транзакцию и создает новую через create_transaction (которая использует apply_transactions_batch).
    Если параметр не передан, используется значение из существующей транзакции.
    """
    from datetime import datetime
    
    # 1️⃣ Получаем информацию о транзакции
    old_tx = _transaction_repository.get_by_id_sync(transaction_id)
    
    if not old_tx:
        raise Exception(f"Транзакция {transaction_id} не найдена")
    old_portfolio_asset_id = old_tx.get("portfolio_asset_id")
    old_transaction_date = old_tx.get("transaction_date")
    
    # Используем переданные значения или значения из существующей транзакции
    final_portfolio_asset_id = portfolio_asset_id if portfolio_asset_id is not None else old_portfolio_asset_id
    final_transaction_type = transaction_type if transaction_type is not None else old_tx.get("transaction_type")
    final_quantity = quantity if quantity is not None else old_tx.get("quantity")
    final_price = price if price is not None else old_tx.get("price")
    final_transaction_date = transaction_date if transaction_date is not None else old_transaction_date
    
    # Получаем asset_id из portfolio_asset_id, если не передан
    if asset_id is None:
        if final_portfolio_asset_id:
            pa_data = _portfolio_asset_repository.get_by_id_sync(final_portfolio_asset_id)
            if pa_data:
                final_asset_id = pa_data.get("asset_id")
            else:
                raise Exception(f"Портфельный актив {final_portfolio_asset_id} не найден")
        else:
            raise Exception("Необходимо указать portfolio_asset_id или asset_id")
    else:
        final_asset_id = asset_id
    
    # Валидация обязательных параметров
    if final_portfolio_asset_id is None:
        raise Exception("portfolio_asset_id обязателен")
    if final_asset_id is None:
        raise Exception("asset_id обязателен")
    if final_transaction_type is None:
        raise Exception("transaction_type обязателен")
    if final_quantity is None:
        raise Exception("quantity обязателен")
    if final_price is None:
        raise Exception("price обязателен")
    if final_transaction_date is None:
        raise Exception("transaction_date обязателен")
    
    # Получаем portfolio_id для старого portfolio_asset_id
    old_portfolio_id = None
    if old_portfolio_asset_id:
        old_pa = _portfolio_asset_repository.get_by_id_sync(old_portfolio_asset_id)
        if old_pa:
            old_portfolio_id = old_pa.get("portfolio_id")
    
    # 2️⃣ Удаляем старую транзакцию через batch функцию (пересчитывает FIFO)
    delete_result = delete_transactions_batch([transaction_id])
    if delete_result.get("success") is False:
        raise Exception(f"Ошибка при удалении транзакции: {delete_result.get('error', 'Неизвестная ошибка')}")
    
    # 3️⃣ Создаем новую транзакцию с обновленными данными
    new_tx_id = create_transaction(
        user_id=user_id,
        portfolio_asset_id=final_portfolio_asset_id,
        asset_id=final_asset_id,
        transaction_type=final_transaction_type,
        quantity=final_quantity,
        price=final_price,
        transaction_date=final_transaction_date
    )
    
    # 4️⃣ Обновляем portfolio_asset для обоих активов (если изменился)
    if old_portfolio_asset_id != final_portfolio_asset_id:
        # Обновляем старый актив
        if old_portfolio_asset_id:
            rpc("update_portfolio_asset", {"pa_id": old_portfolio_asset_id})
        # Обновляем новый актив
        rpc("update_portfolio_asset", {"pa_id": final_portfolio_asset_id})
    else:
        # Если актив не изменился, просто обновляем его
        rpc("update_portfolio_asset", {"pa_id": final_portfolio_asset_id})
    
    # 5️⃣ Получаем portfolio_id для нового portfolio_asset_id
    new_portfolio_id = None
    new_pa = _portfolio_asset_repository.get_by_id_sync(final_portfolio_asset_id)
    if new_pa:
        new_portfolio_id = new_pa.get("portfolio_id")
    
    # 6️⃣ Обновляем историю портфелей с минимальной датой транзакции
    # Преобразуем дату транзакции в формат YYYY-MM-DD используя единую функцию
    from_date = normalize_date_to_sql_date(final_transaction_date) or ""
    
    # Если есть старая дата, берем минимальную
    if old_transaction_date:
        old_date = normalize_date_to_sql_date(old_transaction_date) or ""
        
        # Берем минимальную дату
        if old_date < from_date:
            from_date = old_date
    
    # Обновляем старый портфель, если он изменился
    if old_portfolio_id and old_portfolio_id != new_portfolio_id:
        try:
            rpc("update_portfolio_positions_from_date", {
                "p_portfolio_id": old_portfolio_id,
                "p_from_date": from_date
            })
            rpc("update_portfolio_values_from_date", {
                "p_portfolio_id": old_portfolio_id,
                "p_from_date": from_date
            })
        except Exception as e:
            logger.warning(f"Ошибка при обновлении истории старого портфеля {old_portfolio_id}: {e}", exc_info=True)
    
    # Обновляем новый портфель
    if new_portfolio_id:
        try:
            rpc("update_portfolio_positions_from_date", {
                "p_portfolio_id": new_portfolio_id,
                "p_from_date": from_date
            })
            rpc("update_portfolio_values_from_date", {
                "p_portfolio_id": new_portfolio_id,
                "p_from_date": from_date
            })
        except Exception as e:
            logger.warning(f"Ошибка при обновлении истории портфеля {new_portfolio_id}: {e}", exc_info=True)
    
    # 7️⃣ Проверяем неполученные выплаты для обоих активов (если актив изменился)
    # Проверяем новый актив (create_transaction уже проверит его, но на всякий случай проверяем здесь тоже)
    try:
        rpc("check_missed_payouts", {
            "p_portfolio_asset_id": final_portfolio_asset_id
        })
    except Exception as e:
        logger.warning(f"Ошибка при проверке неполученных выплат для нового актива {final_portfolio_asset_id}: {e}", exc_info=True)
    
    # Проверяем старый актив, если он изменился
    if old_portfolio_asset_id != final_portfolio_asset_id and old_portfolio_asset_id:
        try:
            rpc("check_missed_payouts", {
                "p_portfolio_asset_id": old_portfolio_asset_id
            })
        except Exception as e:
            logger.warning(f"Ошибка при проверке неполученных выплат для старого актива {old_portfolio_asset_id}: {e}", exc_info=True)
    
    return new_tx_id


def delete_transactions_batch(transaction_ids: list[int]):
    """
    Удаляет несколько транзакций батчем и пересчитывает связанные данные.
    SQL функция delete_transactions_batch выполняет:
    - Удаление транзакций
    - Пересчет FIFO лотов для всех затронутых portfolio_assets
    - Обновление portfolio_assets
    - Обновление истории портфелей
    """
    if not transaction_ids:
        return {"success": False, "error": "Список ID транзакций пуст", "deleted_count": 0}
    
    # Вызываем RPC функцию для batch удаления
    delete_result = rpc("delete_transactions_batch", {"p_transaction_ids": transaction_ids})
    
    if not delete_result or delete_result.get("success") is False:
        error_msg = delete_result.get("error", "Неизвестная ошибка") if delete_result else "Ошибка при удалении транзакций"
        raise Exception(f"Ошибка при batch удалении транзакций: {error_msg}")
    
    return delete_result