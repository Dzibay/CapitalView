"""
Доменный сервис для работы с денежными операциями.
Поддерживает все типы операций: Buy, Sell, Dividend, Coupon, Commission, Tax, Deposit, Withdraw, Other.
"""
from app.infrastructure.database.supabase_service import rpc, table_insert
from app.domain.services.transactions_service import create_transaction
from app.utils.date import normalize_date_to_string, normalize_date
from typing import Optional, Union
from datetime import datetime, timedelta, date
from calendar import monthrange
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


def create_operations_batch(
    *,
    user_id: str,
    portfolio_id: Optional[int] = None,
    operation_type: int,
    amount: float,
    currency_id: int = 47,
    start_date: Union[datetime, str],
    end_date: Union[datetime, str],
    day_of_month: int,
    portfolio_asset_id: Optional[int] = None,
    asset_id: Optional[int] = None,
    quantity: Optional[float] = None,
    price: Optional[float] = None,
    dividend_yield: Optional[float] = None
):
    """
    Создает повторяющиеся операции ежемесячно в указанный день месяца.
    
    Args:
        user_id: ID пользователя
        portfolio_id: ID портфеля (опционален, если передан portfolio_asset_id)
        operation_type: Тип операции (1-9)
        amount: Сумма операции
        currency_id: ID валюты (по умолчанию 47 = RUB)
        start_date: Дата начала повторения
        end_date: Дата окончания повторения
        day_of_month: День месяца для создания операции (1-31)
        portfolio_asset_id: ID портфельного актива (обязателен для Buy/Sell)
        asset_id: ID актива (обязателен для Buy/Sell/Dividend/Coupon)
        quantity: Количество (обязательно для Buy/Sell)
        price: Цена за единицу (обязательно для Buy/Sell)
        dividend_yield: Дивидендная доходность (для Dividend/Coupon, опционально)
    
    Returns:
        dict с количеством созданных операций и списком ID
    """
    # Нормализуем даты к date объектам используя утилиты
    start_date = normalize_date(start_date)
    end_date = normalize_date(end_date)
    
    if not start_date or not end_date:
        raise ValueError("start_date и end_date обязательны и должны быть валидными датами")
    
    if end_date < start_date:
        raise ValueError("end_date должна быть позже или равна start_date")
    
    # Генерируем список дат для операций
    operation_dates = []
    
    # Находим первый валидный день месяца
    def get_next_month_date(date_obj, day):
        """Получает следующую дату с указанным днем месяца."""
        year = date_obj.year
        month = date_obj.month
        
        # Получаем количество дней в месяце
        _, last_day = monthrange(year, month)
        target_day = min(day, last_day)
        
        try:
            return date(year, month, target_day)
        except ValueError:
            return date(year, month, last_day)
    
    # Находим первую дату операции
    first_op_date = get_next_month_date(start_date, day_of_month)
    
    # Если первая дата раньше start_date, переходим к следующему месяцу
    if first_op_date < start_date:
        # Переходим к следующему месяцу
        if start_date.month == 12:
            next_month = date(start_date.year + 1, 1, 1)
        else:
            next_month = date(start_date.year, start_date.month + 1, 1)
        first_op_date = get_next_month_date(next_month, day_of_month)
    
    current_date = first_op_date
    
    # Генерируем даты до end_date
    while current_date <= end_date:
        if current_date >= start_date:
            # Преобразуем date в datetime для создания операции
            operation_dates.append(datetime.combine(current_date, datetime.min.time()))
        
        # Переходим к следующему месяцу
        if current_date.month == 12:
            next_month = date(current_date.year + 1, 1, 1)
        else:
            next_month = date(current_date.year, current_date.month + 1, 1)
        current_date = get_next_month_date(next_month, day_of_month)
    
    if not operation_dates:
        raise ValueError("Не удалось сгенерировать даты для операций. Проверьте start_date, end_date и day_of_month")
    
    # Создаем операции
    created_operations = []
    errors = []
    
    for op_date in operation_dates:
        try:
            result = create_operation(
                user_id=user_id,
                portfolio_id=portfolio_id,
                operation_type=operation_type,
                amount=amount,
                currency_id=currency_id,
                operation_date=op_date.isoformat(),
                portfolio_asset_id=portfolio_asset_id,
                asset_id=asset_id,
                quantity=quantity,
                price=price,
                dividend_yield=dividend_yield
            )
            created_operations.append({
                "date": op_date.isoformat(),
                "operation_id": result.get("operation_id"),
                "type": result.get("type")
            })
        except Exception as e:
            errors.append({
                "date": op_date.isoformat(),
                "error": str(e)
            })
            logger.error(f"Ошибка при создании операции на дату {op_date.isoformat()}: {e}")
    
    return {
        "count": len(created_operations),
        "total_dates": len(operation_dates),
        "created": created_operations,
        "errors": errors
    }
