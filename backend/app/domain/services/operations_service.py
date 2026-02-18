"""
Доменный сервис для работы с денежными операциями.
Поддерживает все типы операций: Buy, Sell, Dividend, Coupon, Commission, Tax, Deposit, Withdraw, Other.
"""
from app.infrastructure.database.supabase_service import rpc, table_insert
from app.domain.services.transactions_service import create_transaction
from app.utils.date import normalize_date_to_string
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


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
    
    # Логируем для диагностики
    if operations and len(operations) > 0:
        logger.info(f"Получено операций: {len(operations)}")
        # Проверяем первую операцию на наличие amount_rub
        first_op = operations[0]
        if isinstance(first_op, dict):
            all_keys = list(first_op.keys())
            has_amount_rub = 'amount_rub' in first_op
            has_amountRub = 'amountRub' in first_op
            
            if not has_amount_rub and not has_amountRub:
                logger.warning(f"amount_rub отсутствует в операции! Доступные поля: {all_keys}")
            elif has_amount_rub:
                logger.info(f"amount_rub найден (snake_case): {first_op.get('amount_rub')}, все поля: {all_keys}")
            elif has_amountRub:
                logger.info(f"amountRub найден (camelCase): {first_op.get('amountRub')}, все поля: {all_keys}")
    
    return operations


def create_operation(
    *,
    user_id: str,
    portfolio_id: Optional[int] = None,
    operation_type: int,
    amount: float,
    currency_id: int = 47,
    operation_date: str,
    portfolio_asset_id: Optional[int] = None,
    asset_id: Optional[int] = None,
    quantity: Optional[float] = None,
    price: Optional[float] = None,
    dividend_yield: Optional[float] = None
):
    """
    Создает операцию по активу.
    
    Поддерживает все типы операций:
    - Buy (1) / Sell (2): создает transaction + cash_operation
    - Dividend (3) / Coupon (4): создает cash_operation (без записи в asset_payouts)
    - Commission (7) / Tax (8): создает cash_operation
    - Deposit (5) / Withdraw (6): создает cash_operation
    - Other (9): создает cash_operation
    
    Args:
        user_id: ID пользователя
        portfolio_id: ID портфеля (опционален, если передан portfolio_asset_id)
        operation_type: Тип операции (1-9)
        amount: Сумма операции (до 6 знаков после запятой для выплат)
        currency_id: ID валюты (по умолчанию 47 = RUB, может быть любой валютой включая криптовалюты)
        operation_date: Дата операции
        portfolio_asset_id: ID портфельного актива (обязателен для Buy/Sell, опционален для остальных)
        asset_id: ID актива (обязателен для Buy/Sell/Dividend/Coupon)
        quantity: Количество (обязательно для Buy/Sell)
        price: Цена за единицу (обязательно для Buy/Sell)
        dividend_yield: Дивидендная доходность (для Dividend/Coupon, опционально)
    
    Returns:
        ID созданной операции (transaction_id для Buy/Sell, cash_operation_id для остальных)
    """
    # Нормализуем дату
    if isinstance(operation_date, datetime):
        operation_date = operation_date.isoformat()
    elif isinstance(operation_date, str) and 'T' not in operation_date:
        operation_date = f"{operation_date}T00:00:00"
    
    # Если portfolio_id не передан, но есть portfolio_asset_id, получаем portfolio_id из него
    if not portfolio_id and portfolio_asset_id:
        from app.infrastructure.database.supabase_service import table_select
        pa_data = table_select(
            "portfolio_assets",
            select="portfolio_id",
            filters={"id": portfolio_asset_id},
            limit=1
        )
        if pa_data and len(pa_data) > 0:
            portfolio_id = pa_data[0].get("portfolio_id")
        if not portfolio_id:
            raise ValueError(f"Не удалось найти portfolio_id для portfolio_asset_id={portfolio_asset_id}")
    
    if not portfolio_id:
        raise ValueError("Необходимо указать либо portfolio_id, либо portfolio_asset_id")
    
    # Buy/Sell - создаем через существующую функцию транзакций
    if operation_type in [1, 2]:  # Buy или Sell
        if not portfolio_asset_id:
            raise ValueError("portfolio_asset_id обязателен для Buy/Sell")
        if not asset_id:
            raise ValueError("asset_id обязателен для Buy/Sell")
        if not quantity:
            raise ValueError("quantity обязателен для Buy/Sell")
        if not price:
            raise ValueError("price обязателен для Buy/Sell")
        
        # Используем существующую функцию создания транзакций
        # Она автоматически создаст cash_operation через триггер
        tx_id = create_transaction(
            user_id=user_id,
            portfolio_asset_id=portfolio_asset_id,
            asset_id=asset_id,
            transaction_type=operation_type,  # 1 = buy, 2 = sell
            quantity=quantity,
            price=price,
            transaction_date=operation_date
        )
        
        return {"operation_id": tx_id, "type": "transaction"}
    
    # Для остальных типов операций создаем через SQL функцию
    result = rpc("apply_operation", {
        "p_user_id": user_id,
        "p_portfolio_id": portfolio_id,
        "p_operation_type": operation_type,
        "p_amount": amount,
        "p_currency_id": currency_id,
        "p_operation_date": operation_date,
        "p_asset_id": asset_id,
        "p_dividend_yield": dividend_yield
    })
    
    if not result:
        raise Exception("apply_operation failed")
    
    return {"operation_id": result, "type": "cash_operation"}
