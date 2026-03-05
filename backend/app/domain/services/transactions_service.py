"""
Доменный сервис для работы с транзакциями.
Перенесено из app/services/transactions_service.py
"""
from app.infrastructure.database.supabase_service import table_select, table_insert, rpc
from app.core.logging import get_logger

logger = get_logger(__name__)


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
    transaction_date: str
):
    """
    Единственный разрешённый способ создания транзакций.
    Использует apply_transactions_batch для единообразия.
    FIFO + realized_pnl считаются в БД.
    """
    from datetime import datetime
    
    # Нормализуем дату
    if isinstance(transaction_date, datetime):
        transaction_date_str = transaction_date.isoformat()
    elif isinstance(transaction_date, str) and 'T' not in transaction_date:
        transaction_date_str = f"{transaction_date}T00:00:00"
    else:
        transaction_date_str = transaction_date

    # 1️⃣ Создаём транзакцию через batch функцию (с одним элементом)
    tx_data = [{
        "user_id": str(user_id),
        "portfolio_asset_id": portfolio_asset_id,
        "transaction_type": transaction_type,
        "quantity": float(quantity),
        "price": float(price),
        "transaction_date": transaction_date_str,
        "payment": float(price * quantity)  # Добавляем payment для корректной обработки
    }]
    
    result = rpc("apply_transactions_batch", {"p_transactions": tx_data})
    
    if not result or result.get("inserted_count", 0) == 0:
        error_msg = result.get("failed_transactions", [])
        if error_msg:
            error_msg = error_msg[0].get("error", "Unknown error") if isinstance(error_msg, list) and len(error_msg) > 0 else str(error_msg)
        else:
            error_msg = "apply_transactions_batch failed"
        raise Exception(f"Ошибка создания транзакции: {error_msg}")
    
    # Получаем ID созданной транзакции
    tx_ids = result.get("transaction_ids", [])
    if not tx_ids or len(tx_ids) == 0:
        raise Exception("Транзакция не была создана")
    
    tx_id = tx_ids[0]

    # 2️⃣ Цена актива (idempotent)
    existing_price = table_select(
        "asset_prices",
        "id",
        filters={"asset_id": asset_id, "trade_date": transaction_date_str.split('T')[0]}
    )

    if not existing_price:
        table_insert("asset_prices", {
            "asset_id": asset_id,
            "price": price,
            "trade_date": transaction_date_str.split('T')[0]
        })
        
        # Обновляем последнюю цену актива в asset_latest_prices
        try:
            rpc("update_asset_latest_price", {"p_asset_id": asset_id})
        except Exception as e:
            logger.warning(f"Ошибка при обновлении последней цены актива {asset_id}: {e}", exc_info=True)

    # 3️⃣ Инкрементальные апдейты (БЕЗ глобальных refresh)
    # Примечание: apply_transactions_batch уже обновляет историю, но update_portfolio_asset
    # обновляет агрегированные данные актива (quantity, average_price и т.д.)
    rpc("update_portfolio_asset", {"pa_id": portfolio_asset_id})

    return tx_id


def update_transaction(
    *,
    transaction_id: int,
    user_id: int,
    portfolio_asset_id: int,
    asset_id: int,
    transaction_type: int,
    quantity: float,
    price: float,
    transaction_date: str
):
    """
    Обновляет существующую транзакцию.
    Удаляет старую транзакцию и создает новую через create_transaction (которая использует apply_transactions_batch).
    """
    from datetime import datetime
    
    # 1️⃣ Получаем информацию о транзакции
    existing_tx = table_select(
        "transactions",
        select="*",
        filters={"id": transaction_id},
        limit=1
    )
    
    if not existing_tx:
        raise Exception(f"Транзакция {transaction_id} не найдена")
    
    old_tx = existing_tx[0]
    old_portfolio_asset_id = old_tx.get("portfolio_asset_id")
    old_transaction_date = old_tx.get("transaction_date")
    
    # Получаем portfolio_id для старого portfolio_asset_id
    old_portfolio_id = None
    if old_portfolio_asset_id:
        old_pa = table_select(
            "portfolio_assets",
            select="portfolio_id",
            filters={"id": old_portfolio_asset_id},
            limit=1
        )
        if old_pa:
            old_portfolio_id = old_pa[0].get("portfolio_id")
    
    # 2️⃣ Удаляем старую транзакцию через batch функцию (пересчитывает FIFO)
    delete_result = delete_transactions_batch([transaction_id])
    if delete_result.get("success") is False:
        raise Exception(f"Ошибка при удалении транзакции: {delete_result.get('error', 'Неизвестная ошибка')}")
    
    # 3️⃣ Создаем новую транзакцию с обновленными данными
    new_tx_id = create_transaction(
        user_id=user_id,
        portfolio_asset_id=portfolio_asset_id,
        asset_id=asset_id,
        transaction_type=transaction_type,
        quantity=quantity,
        price=price,
        transaction_date=transaction_date
    )
    
    # 4️⃣ Если portfolio_asset_id изменился, обновляем оба
    if old_portfolio_asset_id != portfolio_asset_id:
        rpc("update_portfolio_asset", {"pa_id": portfolio_asset_id})
    
    # 5️⃣ Получаем portfolio_id для нового portfolio_asset_id
    new_portfolio_id = None
    new_pa = table_select(
        "portfolio_assets",
        select="portfolio_id",
        filters={"id": portfolio_asset_id},
        limit=1
    )
    if new_pa:
        new_portfolio_id = new_pa[0].get("portfolio_id")
    
    # 6️⃣ Обновляем историю портфелей с минимальной датой транзакции
    # Преобразуем дату транзакции в формат YYYY-MM-DD
    if isinstance(transaction_date, str):
        from_date = transaction_date[:10] if 'T' in transaction_date else transaction_date
    elif hasattr(transaction_date, 'date'):
        from_date = transaction_date.date().isoformat()
    else:
        from_date = str(transaction_date)[:10]
    
    # Если есть старая дата, берем минимальную
    if old_transaction_date:
        if isinstance(old_transaction_date, str):
            old_date = old_transaction_date[:10] if 'T' in old_transaction_date else old_transaction_date
        elif hasattr(old_transaction_date, 'date'):
            old_date = old_transaction_date.date().isoformat()
        else:
            old_date = str(old_transaction_date)[:10]
        
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