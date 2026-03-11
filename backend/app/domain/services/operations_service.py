"""
Доменный сервис для работы с денежными операциями.
Поддерживает все типы операций: Buy, Sell, Dividend, Coupon, Commission, Tax, Deposit, Withdraw, Other.
"""
from app.infrastructure.database.postgres_service import rpc
from app.domain.services.transactions_service import create_transaction
from app.utils.date import normalize_date_to_string, normalize_date
from typing import Optional, Union, List
from datetime import datetime, timedelta, date
from calendar import monthrange
import logging
from app.infrastructure.database.repositories.operation_repository import OperationRepository
from app.infrastructure.database.repositories.portfolio_asset_repository import PortfolioAssetRepository

logger = logging.getLogger(__name__)

# Создаем экземпляры репозиториев для использования во всех функциях
_operation_repository = OperationRepository()
_portfolio_asset_repository = PortfolioAssetRepository()


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
    currency_id: int = 1,
    operation_date: str,
    portfolio_asset_id: Optional[int] = None,
    asset_id: Optional[int] = None,
    quantity: Optional[float] = None,
    price: Optional[float] = None,
    dividend_yield: Optional[float] = None,
    create_deposit_operation: bool = False
):
    """
    Создает операцию по активу.
    
    Поддерживает все типы операций:
    - Buy (1) / Sell (2): создает transaction + cash_operation
    - Ammortization (9): создает transaction типа Redemption (3) + cash_operation
    - Dividend (3) / Coupon (4): создает cash_operation (без записи в asset_payouts)
    - Commission (7) / Tax (8): создает cash_operation
    - Deposit (5) / Withdraw (6): создает cash_operation
    - Other (10): создает cash_operation
    
    Args:
        user_id: ID пользователя
        portfolio_id: ID портфеля (опционален, если передан portfolio_asset_id)
        operation_type: Тип операции (1-10: 1=Buy, 2=Sell, 3=Dividend, 4=Coupon, 5=Deposit, 6=Withdraw, 7=Commission, 8=Tax, 9=Ammortization, 10=Other)
        amount: Сумма операции (до 6 знаков после запятой для выплат)
        currency_id: ID валюты (по умолчанию 1 = RUB, может быть любой валютой включая криптовалюты)
        operation_date: Дата операции
        portfolio_asset_id: ID портфельного актива (обязателен для Buy/Sell, опционален для остальных)
        asset_id: ID актива (обязателен для Buy/Sell/Dividend/Coupon)
        quantity: Количество (обязательно для Buy/Sell)
        price: Цена за единицу (обязательно для Buy/Sell)
        dividend_yield: Дивидендная доходность (для Dividend/Coupon, опционально)
    
    Returns:
        ID созданной операции (transaction_id для Buy/Sell, cash_operation_id для остальных)
    """
    # Нормализуем дату используя единую функцию
    operation_date = normalize_date_to_string(operation_date, include_time=True) or ""
    
    # Если portfolio_id не передан, но есть portfolio_asset_id, получаем portfolio_id из него
    if not portfolio_id and portfolio_asset_id:
        pa_data = _portfolio_asset_repository.get_by_id_sync(portfolio_asset_id)
        if pa_data:
            portfolio_id = pa_data.get("portfolio_id")
        if not portfolio_id:
            raise ValueError(f"Не удалось найти portfolio_id для portfolio_asset_id={portfolio_asset_id}")
    
    if not portfolio_id:
        raise ValueError("Необходимо указать либо portfolio_id, либо portfolio_asset_id")
    
    # Buy/Sell/Redemption - создаем через существующую функцию транзакций
    if operation_type in [1, 2, 9]:  # Buy, Sell или Ammortization (обрабатывается как Redemption транзакция)
        if not portfolio_asset_id:
            raise ValueError("portfolio_asset_id обязателен для Buy/Sell/Redemption")
        if not asset_id:
            raise ValueError("asset_id обязателен для Buy/Sell/Redemption")
        if not quantity:
            raise ValueError("quantity обязателен для Buy/Sell/Redemption")
        if not price:
            raise ValueError("price обязателен для Buy/Sell/Redemption")
        
        # Маппинг типов: Buy=1, Sell=2, Ammortization=9 -> Redemption=3
        if operation_type == 9:
            transaction_type = 3  # Redemption
        else:
            transaction_type = operation_type  # 1 = buy, 2 = sell (тип 9 обрабатывается выше как 3 = redemption)
        
        # Используем существующую функцию создания транзакций
        # Она автоматически создаст cash_operation через триггер
        tx_id = create_transaction(
            user_id=user_id,
            portfolio_asset_id=portfolio_asset_id,
            asset_id=asset_id,
            transaction_type=transaction_type,
            quantity=quantity,
            price=price,
            transaction_date=operation_date,
            create_deposit_operation=create_deposit_operation and operation_type == 1  # Только для покупки
        )
        
        return {"operation_id": tx_id, "type": "transaction"}
    
    # Для остальных типов операций создаем через batch функцию (с одним элементом)
    op_data = [{
        "user_id": str(user_id),
        "portfolio_id": portfolio_id,
        "operation_type": operation_type,
        "amount": float(amount),
        "currency_id": currency_id,
        "operation_date": operation_date,
        "asset_id": asset_id,
        "portfolio_asset_id": portfolio_asset_id,
        "dividend_yield": float(dividend_yield) if dividend_yield is not None else None
    }]
    
    result = rpc("apply_operations_batch", {"p_operations": op_data})
    
    if not result or result.get("inserted_count", 0) == 0:
        error_msg = result.get("failed_operations", [])
        if error_msg:
            error_msg = error_msg[0].get("error", "Unknown error") if isinstance(error_msg, list) and len(error_msg) > 0 else str(error_msg)
        else:
            error_msg = "apply_operations_batch failed"
        raise Exception(f"Ошибка создания операции: {error_msg}")
    
    # Получаем ID созданной операции
    op_ids = result.get("operation_ids", [])
    if not op_ids or len(op_ids) == 0:
        raise Exception("Операция не была создана")
    
    op_id = op_ids[0]
    
    # Проверяем неполученные выплаты для операций дивидендов/купонов
    # Это нужно, так как мы убрали автоматическую проверку из apply_operations_batch
    if operation_type in [3, 4] and portfolio_asset_id:  # Dividend или Coupon
        try:
            rpc("check_missed_payouts", {
                "p_portfolio_asset_id": portfolio_asset_id
            })
        except Exception as e:
            logger.warning(f"Ошибка при проверке неполученных выплат для актива {portfolio_asset_id}: {e}", exc_info=True)
    
    # Создаем операцию пополнения для комиссии/налога, если запрошено
    if create_deposit_operation and operation_type in [7, 8]:  # Commission или Tax
        try:
            deposit_amount = abs(float(amount))
            # Операция пополнения привязана к активу для удаления при удалении актива
            # Важно: currency_id=1 (RUB) для операций пополнения, чтобы сумма не конвертировалась
            create_operation(
                user_id=user_id,
                portfolio_id=portfolio_id,
                operation_type=5,  # Deposit
                amount=deposit_amount,
                currency_id=1,  # RUB - операция пополнения всегда в рублях
                operation_date=operation_date,
                asset_id=asset_id,  # Привязываем к активу для удаления при удалении актива
                portfolio_asset_id=portfolio_asset_id,  # Привязываем к портфельному активу
                create_deposit_operation=False  # Не создаем рекурсивно
            )
        except Exception as e:
            from app.core.logging import get_logger
            logger = get_logger(__name__)
            logger.warning(f"Ошибка при создании операции пополнения для операции {op_id}: {e}", exc_info=True)
            # Не прерываем выполнение, так как основная операция уже создана
    
    return {"operation_id": op_id, "type": "cash_operation"}


def create_operations_batch(
    *,
    user_id: str,
    portfolio_id: Optional[int] = None,
    operation_type: int,
    amount: float,
    currency_id: int = 1,
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
        operation_type: Тип операции (1-10: 1=Buy, 2=Sell, 3=Dividend, 4=Coupon, 5=Deposit, 6=Withdraw, 7=Commission, 8=Tax, 9=Ammortization, 10=Other)
        amount: Сумма операции
        currency_id: ID валюты (по умолчанию 1 = RUB)
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
    
    # Подготавливаем операции для batch вставки
    operations_list = []
    for op_date in operation_dates:
        op_data = {
            "user_id": user_id,
            "portfolio_id": portfolio_id,
            "operation_type": operation_type,
            "amount": amount,
            "currency_id": currency_id,
            "operation_date": normalize_date_to_string(op_date, include_time=True) or "",
            "asset_id": asset_id,
            "dividend_yield": dividend_yield
        }
        operations_list.append(op_data)
    
    # Используем batch функцию для создания всех операций за один раз
    from app.infrastructure.database.postgres_service import rpc
    result = rpc("apply_operations_batch", {
        "p_operations": operations_list
    })
    
    if not result:
        raise Exception("apply_operations_batch failed")
    
    # Форматируем результат для совместимости
    created_operations = result.get("created", [])
    errors = result.get("failed_operations", [])
    
    return {
        "count": result.get("inserted_count", 0),
        "total_dates": len(operation_dates),
        "created": created_operations,
        "errors": errors
    }


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


def create_operations_from_missed_payouts(
    *,
    user_id: str,
    missed_payouts: List[dict]
):
    """
    Создает операции выплат (дивиденды/купоны) из списка неполученных выплат батчем.
    Использует apply_operations_batch для эффективной обработки всех операций за один раз.
    
    Args:
        user_id: ID пользователя
        missed_payouts: Список словарей с данными неполученных выплат. Каждый словарь должен содержать:
            - id: ID записи в missed_payouts (для сопоставления с результатами)
            - portfolio_id: ID портфеля
            - portfolio_asset_id: ID актива в портфеле
            - asset_id: ID актива
            - payout_type: Тип выплаты ('dividend' или 'coupon')
            - payment_date: Дата выплаты (date или str)
            - expected_amount: Ожидаемая сумма выплаты (уже рассчитана с учетом количества акций)
            - currency_id: (опционально) ID валюты, по умолчанию 1 (RUB)
    
    Returns:
        dict с результатами создания операций:
            - inserted_count: Количество успешно созданных операций
            - failed_count: Количество неудачных операций
            - operation_ids: Список ID созданных операций
            - failed_operations: Список неудачных операций с ошибками (содержит индекс исходной выплаты)
            - created: Список созданных операций для совместимости
            - payout_indices_map: Словарь {индекс_операции: индекс_выплаты} для сопоставления
    """
    if not missed_payouts:
        return {
            "inserted_count": 0,
            "failed_count": 0,
            "operation_ids": [],
            "failed_operations": [],
            "created": [],
            "payout_indices_map": {}
        }
    
    # Подготавливаем операции для batch вставки
    operations_list = []
    payout_indices_map = {}  # {индекс_операции: индекс_выплаты}
    operation_index = 0
    
    for payout_index, payout in enumerate(missed_payouts):
        # Определяем тип операции: 3 = Dividend, 4 = Coupon
        payout_type = payout.get("payout_type", "").lower()
        operation_type = 4 if payout_type == "coupon" else 3
        
        # Получаем дату выплаты
        payment_date = payout.get("payment_date") or payout.get("payout_payment_date")
        if not payment_date:
            logger.warning(f"Пропущена выплата без даты: {payout}")
            continue
        
        # Нормализуем дату
        operation_date = normalize_date_to_string(payment_date, include_time=True)
        if not operation_date:
            logger.warning(f"Не удалось нормализовать дату выплаты: {payment_date}")
            continue
        
        # Получаем сумму выплаты
        expected_amount = payout.get("expected_amount") or payout.get("payout_value") or 0
        if expected_amount <= 0:
            logger.warning(f"Пропущена выплата с нулевой суммой: {payout}")
            continue
        
        # Получаем валюту (по умолчанию RUB)
        currency_id = payout.get("currency_id", 1)
        
        # Формируем данные операции
        op_data = {
            "user_id": str(user_id),
            "portfolio_id": payout.get("portfolio_id"),
            "operation_type": operation_type,
            "amount": float(expected_amount),
            "currency_id": currency_id,
            "operation_date": operation_date,
            "asset_id": payout.get("asset_id"),
            "portfolio_asset_id": payout.get("portfolio_asset_id")
        }
        
        operations_list.append(op_data)
        payout_indices_map[operation_index] = payout_index
        operation_index += 1
    
    if not operations_list:
        return {
            "inserted_count": 0,
            "failed_count": 0,
            "operation_ids": [],
            "failed_operations": [],
            "created": [],
            "failed_payout_indices": []
        }
    
    # Используем batch функцию для создания всех операций за один раз
    result = rpc("apply_operations_batch", {
        "p_operations": operations_list
    })
    
    if not result:
        raise Exception("apply_operations_batch failed")
    
    # Обогащаем failed_operations индексами исходных выплат для удобного сопоставления
    # Оптимизация: создаем словарь для быстрого поиска операций по ключу
    enriched_failed_operations = []
    failed_indices = set()
    
    # Создаем словарь для быстрого поиска операций: ключ = (portfolio_id, asset_id, portfolio_asset_id, operation_date, amount)
    operations_dict = {}
    for op_idx, op_data in enumerate(operations_list):
        key = (
            op_data.get("portfolio_id"),
            op_data.get("asset_id"),
            op_data.get("portfolio_asset_id"),
            op_data.get("operation_date"),
            round(float(op_data.get("amount", 0)), 2)  # Округляем для сравнения
        )
        operations_dict[key] = op_idx
    
    # Быстро находим соответствующие операции для неудачных
    for failed_op in result.get("failed_operations", []):
        failed_op_data = failed_op.get("operation", {})
        if not failed_op_data:
            continue
        
        # Формируем ключ для поиска
        key = (
            failed_op_data.get("portfolio_id"),
            failed_op_data.get("asset_id"),
            failed_op_data.get("portfolio_asset_id"),
            failed_op_data.get("operation_date"),
            round(float(failed_op_data.get("amount", 0)), 2)
        )
        
        op_idx = operations_dict.get(key)
        if op_idx is not None:
            payout_idx = payout_indices_map.get(op_idx)
            if payout_idx is not None:
                failed_indices.add(payout_idx)
                enriched_failed_operations.append({
                    **failed_op,
                    "payout_index": payout_idx,
                    "payout_id": missed_payouts[payout_idx].get("id")
                })
    
    # Примечание: проверка неполученных выплат НЕ выполняется здесь автоматически
    # Выплаты удаляются вручную в endpoint после успешного создания операций
    # Это ускоряет процесс создания операций и предотвращает избыточные проверки
    
    return {
        "inserted_count": result.get("inserted_count", 0),
        "failed_count": result.get("failed_count", 0),
        "operation_ids": result.get("operation_ids", []),
        "failed_operations": enriched_failed_operations,
        "created": result.get("created", []),
        "failed_payout_indices": list(failed_indices)
    }
