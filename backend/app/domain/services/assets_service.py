import json
from app.infrastructure.database.database_service import rpc
from app.domain.services.user_service import get_user_by_email
from datetime import datetime
from app.utils.date import normalize_date_to_string, normalize_date_to_sql_date
from app.core.logging import get_logger
from app.infrastructure.database.repositories.asset_repository import AssetRepository
logger = get_logger(__name__)

_asset_repository = AssetRepository()


def create_asset(email: str, data: dict):
    """
    Создает актив в портфеле через RPC функцию с ACID транзакцией.
    Для кастомных активов всегда создается новый уникальный актив (не ищется существующий).
    """
    # --- Получаем пользователя ---
    user = get_user_by_email(email)
    if not user:
        return {"success": False, "error": "Пользователь не найден"}

    user_id = user["id"]

    # Нормализуем значения, преобразуя строки "None" и пустые строки в None
    def normalize_value(value):
        if value is None or value == "None" or value == "":
            return None
        return value
    
    portfolio_id = normalize_value(data.get("portfolio_id"))
    asset_id = normalize_value(data.get("asset_id"))
    asset_type_id = normalize_value(data.get("asset_type_id"))
    name = data.get("name")
    ticker = data.get("ticker")  # Не используется для кастомных активов
    quantity = float(data.get("quantity", 0))
    currency = int(data.get("currency")) if data.get("currency") and data.get("currency") != "None" else None
    price = float(data.get("average_price", 0))
    date = data.get("date") or normalize_date_to_string(datetime.utcnow(), include_time=True)
    
    # Преобразуем portfolio_id и asset_id в int, если они не None
    if portfolio_id is not None:
        try:
            portfolio_id = int(portfolio_id)
        except (ValueError, TypeError):
            return {"success": False, "error": "Некорректный portfolio_id"}
    
    if asset_id is not None:
        try:
            asset_id = int(asset_id)
        except (ValueError, TypeError):
            return {"success": False, "error": "Некорректный asset_id"}

    try:
        # Преобразуем дату в формат date для PostgreSQL (импорт уже есть в начале файла)
        transaction_date = normalize_date_to_string(date)
        if not transaction_date:
            transaction_date = normalize_date_to_sql_date(datetime.utcnow().date())

        # Вызываем RPC функцию для создания актива
        rpc_params = {
            "p_user_id": str(user_id),
            "p_portfolio_id": portfolio_id,
            "p_asset_id": asset_id,  # NULL для кастомного актива
            "p_asset_type_id": asset_type_id,
            "p_name": name,
            "p_ticker": ticker,  # Не используется для кастомных активов
            "p_currency_id": currency,
            "p_quantity": quantity,
            "p_price": price,
            "p_transaction_date": transaction_date
        }
        
        result = rpc("create_portfolio_asset", rpc_params)
        
        if not result:
            return {"success": False, "error": "Ошибка при создании актива: пустой ответ от RPC"}
        
        # RPC функция возвращает text (JSON строка), нужно распарсить
        if isinstance(result, str):
            try:
                parsed_result = json.loads(result)
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка при парсинге JSON из RPC: {e}, result: {result}")
                return {"success": False, "error": f"Ошибка при парсинге ответа от RPC: {str(e)}"}
        elif isinstance(result, dict):
            parsed_result = result
        elif isinstance(result, list) and len(result) > 0:
            parsed_result = result[0]
        else:
            return {"success": False, "error": f"Некорректный формат ответа от RPC: {type(result)}"}
        
        # Создаем операцию пополнения, если запрошено и есть транзакция покупки
        create_deposit_operation = data.get("create_deposit_operation", False)
        if create_deposit_operation and quantity > 0 and price > 0:
            try:
                from app.domain.services.operations_service import apply_operations
                
                asset_info = parsed_result.get("asset", {})
                asset_id_from_result = asset_info.get("asset_id")
                portfolio_asset_id_from_result = asset_info.get("portfolio_asset_id")
                
                if asset_id_from_result and portfolio_id:
                    deposit_amount = float(quantity * price)
                    # Валюта операции пополнения = валюта актива (quote_asset_id; 1 = RUB по умолчанию)
                    asset_row = _asset_repository.get_by_id_sync(asset_id_from_result)
                    currency_id = (asset_row.get("quote_asset_id") or 1) if asset_row else 1
                    apply_operations(
                        user_id=str(user_id),
                        operations=[
                            {
                                "operation_type": 5,  # Deposit
                                "operation_date": transaction_date,
                                "amount": deposit_amount,
                                "currency_id": currency_id,
                                "asset_id": asset_id_from_result,  # Для удаления вместе с активом
                                "portfolio_asset_id": portfolio_asset_id_from_result,
                                "portfolio_id": portfolio_id,
                            }
                        ],
                    )
            except Exception as e:
                logger.warning(f"Ошибка при создании операции пополнения для актива: {e}", exc_info=True)
                # Не прерываем выполнение, так как актив уже создан
        
        return parsed_result

    except Exception as e:
        logger.error(f"Ошибка при добавлении актива: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
 

def delete_asset(portfolio_asset_id: int):
    """
    Удаляет актив из портфеля через RPC функцию с ACID транзакцией.
    """
    try:
        result = rpc("delete_portfolio_asset", {"p_portfolio_asset_id": portfolio_asset_id})
        
        if not result:
            return {"success": False, "error": "Ошибка при удалении актива: пустой ответ от RPC"}
        
        # RPC функция возвращает text (JSON строка), нужно распарсить
        if isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка при парсинге JSON из RPC: {e}, result: {result}")
                return {"success": False, "error": f"Ошибка при парсинге ответа от RPC: {str(e)}"}
        elif isinstance(result, dict):
            return result
        elif isinstance(result, list) and len(result) > 0:
            return result[0]
        else:
            return {"success": False, "error": f"Некорректный формат ответа от RPC: {type(result)}"}

    except Exception as e:
        logger.error(f"Ошибка при удалении актива {portfolio_asset_id}: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return {"success": False, "error": f"Ошибка при удалении актива: {str(e)}"}
    

def get_asset_info(asset_id: int):
    """
    Получает детальную информацию об активе.
    """
    try:
        # Получаем основную информацию об активе
        asset_info = _asset_repository.get_by_id_sync(asset_id)
        
        if not asset_info:
            return {"success": False, "error": "Актив не найден"}
        
        # Получаем последнюю цену
        latest_price = _asset_repository.get_latest_price(asset_id)
        
        if latest_price:
            asset_info["latest_price"] = latest_price
        else:
            asset_info["latest_price"] = None
        
        return {"success": True, "asset": asset_info}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_asset_daily_values(portfolio_asset_id: int, from_date: str = None, to_date: str = None):
    """
    Получает историю стоимости актива для графика.
    Использует предрассчитанные данные из portfolio_asset_daily_values.
    
    Args:
        portfolio_asset_id: ID актива в портфеле
        from_date: Начальная дата (опционально, формат: 'YYYY-MM-DD')
        to_date: Конечная дата (опционально, формат: 'YYYY-MM-DD')
    
    Returns:
        dict с ключами:
            - success: bool
            - values: list - список записей с полями:
                - report_date: дата
                - position_value: стоимость позиции в RUB
                - quantity: количество
                - average_price: средняя цена
                - cumulative_invested: инвестированная стоимость в RUB
                - unrealized_pnl: нереализованная прибыль в RUB
            - error: str (если success=False)
    """
    try:
        params = {"p_portfolio_asset_id": portfolio_asset_id}
        
        if from_date:
            params["p_from_date"] = from_date
        if to_date:
            params["p_to_date"] = to_date
        
        result = rpc("get_portfolio_asset_daily_values", params)
        
        if result is None:
            logger.warning(f"get_portfolio_asset_daily_values вернул None для portfolio_asset_id={portfolio_asset_id}")
            return {"success": False, "error": "Не удалось получить данные"}
        
        if not result:
            logger.warning(f"get_portfolio_asset_daily_values вернул пустой результат для portfolio_asset_id={portfolio_asset_id}")
            return {"success": True, "values": [], "count": 0}
        
        # Проверяем, что есть данные с position_value
        values_with_position = [v for v in result if v.get("position_value") is not None]
        if values_with_position:
            logger.info(f"Загружено {len(result)} записей для portfolio_asset_id={portfolio_asset_id}, из них {len(values_with_position)} с position_value")
        else:
            logger.warning(f"Все записи для portfolio_asset_id={portfolio_asset_id} имеют position_value=null")
        
        return {"success": True, "values": result, "count": len(result) if result else 0}
    except Exception as e:
        logger.error(f"Ошибка при получении истории стоимости актива {portfolio_asset_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def get_portfolio_asset_info(portfolio_asset_id: int, user_id: str):
    """
    Получает детальную информацию о портфельном активе (оптимизированная версия).
    Использует единый SQL запрос для получения всей информации.
    
    Args:
        portfolio_asset_id: ID портфельного актива
        user_id: ID пользователя (обязательный параметр)
    """
    try:
        if not user_id:
            return {"success": False, "error": "user_id обязателен для получения информации об активе"}
        
        # Используем оптимизированную функцию для получения всей информации за один запрос
        # Включаем историю цен с лимитом для начальной загрузки (можно загрузить больше отдельно)
        result = rpc("get_portfolio_asset_detail", {
            "p_portfolio_asset_id": portfolio_asset_id,
            "p_user_id": user_id,
            "p_include_price_history": True,
            "p_price_history_limit": 100000
        })
        
        if not result:
            return {"success": False, "error": "Портфельный актив не найден"}
        
        # Извлекаем данные из результата
        portfolio_asset_data = result.get("portfolio_asset")
        if not portfolio_asset_data:
            return {"success": False, "error": "Данные портфельного актива не найдены"}
        
        # Формируем результат в том же формате, что и раньше
        portfolio_asset = {
            "id": portfolio_asset_data.get("portfolio_asset_id"),
            "asset_id": portfolio_asset_data.get("asset_id"),
            "portfolio_id": portfolio_asset_data.get("portfolio_id"),
            "quantity": portfolio_asset_data.get("quantity"),
            "leverage": portfolio_asset_data.get("leverage"),
            "average_price": portfolio_asset_data.get("average_price"),
            "last_price": portfolio_asset_data.get("last_price"),
            "daily_change": portfolio_asset_data.get("daily_change"),
            "currency_ticker": portfolio_asset_data.get("currency_ticker"),
            "quote_asset_id": portfolio_asset_data.get("quote_asset_id"),
            "currency_rate_to_rub": portfolio_asset_data.get("currency_rate_to_rub"),
            "name": portfolio_asset_data.get("asset_name"),
            "ticker": portfolio_asset_data.get("ticker"),
            "type": portfolio_asset_data.get("asset_type"),
            "transactions": result.get("transactions", []),
            "transactions_count": len(result.get("transactions", [])),
            "all_payouts": result.get("all_payouts", []),  # Все выплаты из asset_payouts (история)
            "payouts_count": len(result.get("all_payouts", [])),
            # ОПТИМИЗИРОВАНО: добавляем daily_values и cash_operations из основного запроса
            "daily_values": result.get("daily_values", []),
            "cash_operations": result.get("cash_operations", []),
            "price_history": result.get("price_history", []),  # История цен из того же запроса
            # ИСПРАВЛЕНО: добавляем поля из portfolio_asset_daily_values для использования на фронтенде
            "asset_value": portfolio_asset_data.get("asset_value"),
            "invested_value": portfolio_asset_data.get("invested_value"),
            "realized_pnl": portfolio_asset_data.get("realized_pnl"),
            "payouts": portfolio_asset_data.get("payouts"),  # Накопленные выплаты из portfolio_asset_daily_values
            "commissions": portfolio_asset_data.get("commissions"),
            "taxes": portfolio_asset_data.get("taxes"),
            "total_pnl": portfolio_asset_data.get("total_pnl")  # Общая прибыль из таблицы
        }
        
        # Добавляем информацию о портфелях
        portfolios_data = result.get("portfolios", [])
        for portfolio in portfolios_data:
            # Обрабатываем случай, когда portfolio_total_value может быть None
            portfolio_total = portfolio.get("portfolio_total_value") or 0
            asset_value = portfolio.get("asset_value") or 0
            
            # Преобразуем в числа для безопасного сравнения
            try:
                portfolio_total = float(portfolio_total) if portfolio_total is not None else 0
                asset_value = float(asset_value) if asset_value is not None else 0
            except (ValueError, TypeError):
                portfolio_total = 0
                asset_value = 0
            
            if portfolio_total > 0:
                portfolio["percentage_in_portfolio"] = round((asset_value / portfolio_total) * 100, 2)
            else:
                portfolio["percentage_in_portfolio"] = 0
        
        return {
            "success": True,
            "portfolio_asset": portfolio_asset,
            "portfolios": portfolios_data  # Добавляем информацию о портфелях в ответ
        }
    except Exception as e:
        logger.error(f"Ошибка при получении информации о портфельном активе: {e}")
        return {"success": False, "error": str(e)}


def move_asset_to_portfolio(portfolio_asset_id: int, target_portfolio_id: int, user_id: int = None):
    """
    Перемещает актив из одного портфеля в другой.
    Оптимизировано: 1 SQL-функция вместо 15-20 round-trip.
    """
    try:
        user_id_str = str(user_id) if user_id else None
        result = rpc("move_portfolio_asset", {
            "p_portfolio_asset_id": portfolio_asset_id,
            "p_target_portfolio_id": target_portfolio_id,
            "p_user_id": user_id_str
        })

        if not result:
            return {"success": False, "error": "Ошибка при перемещении актива: пустой ответ"}

        if isinstance(result, str):
            import json as _json
            try:
                result = _json.loads(result)
            except _json.JSONDecodeError:
                return {"success": False, "error": f"Некорректный ответ: {result}"}

        return result

    except Exception as e:
        logger.error(f"Ошибка при перемещении актива: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def get_asset_in_all_portfolios(asset_id: int, user_id: str):
    """
    Получает информацию об активе во всех портфелях пользователя.
    
    Args:
        asset_id: ID актива
        user_id: ID пользователя (UUID - str)
        
    Returns:
        dict с ключами:
            - success: bool
            - portfolios: list - список портфелей с информацией об активе
            - error: str (если success=False)
    """
    try:
        user_id_str = str(user_id) if user_id else None
        
        # Получаем все портфели пользователя, где есть этот актив
        result = rpc("get_asset_in_all_portfolios", {
            "p_asset_id": asset_id,
            "p_user_id": user_id_str
        })
        
        if result is None:
            return {"success": False, "error": "Не удалось получить данные"}
        
        return {"success": True, "portfolios": result if result else []}
    except Exception as e:
        logger.error(f"Ошибка при получении информации об активе в портфелях: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    