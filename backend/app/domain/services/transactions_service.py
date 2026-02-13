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
    transaction_type: int,   # 1 = buy, 2 = sell
    quantity: float,
    price: float,
    transaction_date: str
):
    """
    Единственный разрешённый способ создания транзакций.
    FIFO + realized_pnl считаются в БД.
    """

    # 1️⃣ Создаём транзакцию через FIFO-safe RPC
    tx_id = rpc("apply_transaction", {
        "p_user_id": user_id,
        "p_portfolio_asset_id": portfolio_asset_id,
        "p_transaction_type": transaction_type,
        "p_quantity": quantity,
        "p_price": price,
        "p_transaction_date": transaction_date
    })

    if not tx_id:
        raise Exception("apply_transaction failed")

    # 2️⃣ Цена актива (idempotent)
    existing_price = table_select(
        "asset_prices",
        "id",
        filters={"asset_id": asset_id, "trade_date": transaction_date}
    )

    if not existing_price:
        table_insert("asset_prices", {
            "asset_id": asset_id,
            "price": price,
            "trade_date": transaction_date
        })

    # 3️⃣ Инкрементальные апдейты (БЕЗ глобальных refresh)
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
    Удаляет старую транзакцию и создает новую через apply_transaction.
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
    
    # 2️⃣ Удаляем старую транзакцию через RPC (пересчитывает FIFO)
    delete_result = rpc("delete_transaction", {"p_transaction_id": transaction_id})
    if delete_result is False:
        raise Exception("Ошибка при удалении транзакции")
    
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


def delete_transaction(transaction_id: int):
    """
    Удаляет транзакцию и пересчитывает связанные данные.
    SQL функция delete_transaction выполняет:
    - Удаление транзакции
    - Пересчет FIFO лотов
    - Обновление portfolio_asset
    - Обновление истории портфеля
    """
    # Вызываем RPC функцию, которая выполняет все необходимые операции
    delete_result = rpc("delete_transaction", {"p_transaction_id": transaction_id})
    
    if delete_result is False:
        raise Exception(f"Ошибка при удалении транзакции {transaction_id}")
    
    return True
