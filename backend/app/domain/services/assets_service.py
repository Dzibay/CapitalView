import json
from app.infrastructure.database.supabase_service import rpc, table_insert, table_select, table_update
from app.domain.services.user_service import get_user_by_email
from datetime import datetime
from app.utils.date import normalize_date_to_string
from app.domain.services.portfolio_service import update_portfolios_with_asset
from app.core.logging import get_logger

logger = get_logger(__name__)



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
    date = data.get("date") or datetime.utcnow().isoformat()
    
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
        # Преобразуем дату в формат date для PostgreSQL
        from app.utils.date import normalize_date_to_string
        transaction_date = normalize_date_to_string(date)
        if not transaction_date:
            transaction_date = datetime.utcnow().date().isoformat()

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
    

def add_asset_price(data):
    """
    Добавляет цену актива и обновляет последнюю цену.
    
    Args:
        data: Словарь с полями:
            - asset_id: ID актива
            - price: Цена
            - date: Дата цены
    """
    asset_id = data.get('asset_id')
    price = data.get('price', 0)
    date = data.get('date')

    # Валидация обязательных полей
    if not asset_id:
        return {"success": False, "error": "asset_id обязателен"}
    if not price or price <= 0:
        return {"success": False, "error": "price должен быть больше 0"}
    if not date:
        return {"success": False, "error": "date обязателен"}
    
    # Проверяем, что актив не является системным (user_id IS NULL)
    try:
        asset = table_select("assets", "id, user_id", filters={"id": asset_id})
        if not asset or len(asset) == 0:
            return {"success": False, "error": "Актив не найден"}
        
        asset_data = asset[0]
        if asset_data.get("user_id") is None:
            return {"success": False, "error": "Невозможно изменить цену системного актива"}
    except Exception as e:
        logger.error(f"Ошибка при проверке актива {asset_id}: {e}")
        return {"success": False, "error": "Ошибка при проверке актива"}

    price_data = {
        "asset_id": asset_id,
        "price": price,
        "trade_date": date
    }

    try:
        res = table_insert("asset_prices", price_data)
        
        # Обновляем только один актив
        # Если RPC выбросит исключение, это не критично - цена уже добавлена
        try:
            update_result = rpc('update_asset_latest_price', {'p_asset_id': asset_id})
            # Если функция возвращает boolean False, это ошибка
            if update_result is False:
                logger.warning(f"RPC функция вернула False для актива {asset_id}")
                # Не возвращаем ошибку, так как цена уже добавлена
        except Exception as rpc_error:
            # Если RPC выбросил исключение, логируем, но не прерываем выполнение
            logger.warning(f"Ошибка при обновлении цены актива {asset_id}: {rpc_error}")
            # Продолжаем выполнение, так как цена уже добавлена
        
        # Находим все портфели, содержащие этот актив, и обновляем их
        update_portfolios_with_asset(asset_id, date)
        
        return {"success": True, "message": "Цена успешно добавлена", "data": res}
    except Exception as e:
        logger.error(f"Ошибка при добавлении цены актива: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def add_asset_prices_batch(asset_id: int, prices: list):
    """
    Массовое добавление цен актива.
    
    Args:
        asset_id: ID актива
        prices: Список словарей с полями:
            - price: Цена
            - date: Дата цены (может быть строкой или datetime)
    
    Returns:
        dict с результатом операции
    """
    if not asset_id:
        return {"success": False, "error": "asset_id обязателен"}
    if not prices or len(prices) == 0:
        return {"success": False, "error": "prices не может быть пустым"}
    
    # Проверяем, что актив не является системным (user_id IS NULL)
    try:
        asset = table_select("assets", "id, user_id", filters={"id": asset_id})
        if not asset or len(asset) == 0:
            return {"success": False, "error": "Актив не найден"}
        
        asset_data = asset[0]
        if asset_data.get("user_id") is None:
            return {"success": False, "error": "Невозможно изменить цену системного актива"}
    except Exception as e:
        logger.error(f"Ошибка при проверке актива {asset_id}: {e}")
        return {"success": False, "error": "Ошибка при проверке актива"}
    
    # Подготавливаем данные для upsert
    price_data_list = []
    for price_item in prices:
        price = price_item.get('price', 0)
        date = price_item.get('date')
        
        if not price or price <= 0:
            continue  # Пропускаем некорректные цены
        
        if not date:
            continue  # Пропускаем записи без даты
        
        # Нормализуем дату
        if hasattr(date, 'isoformat'):
            date_str = date.isoformat()
        elif isinstance(date, str):
            date_str = date
        else:
            date_str = str(date)
        
        price_data_list.append({
            "asset_id": asset_id,
            "price": float(price),
            "trade_date": date_str
        })
    
    if not price_data_list:
        return {"success": False, "error": "Нет валидных цен для добавления"}
    
    try:
        # Используем RPC функцию для массовой вставки
        result = rpc("upsert_asset_prices", {"p_prices": price_data_list})
        
        if result is False:
            return {"success": False, "error": "Ошибка при массовом добавлении цен"}
        
        # Обновляем последнюю цену актива
        try:
            update_result = rpc('update_asset_latest_price', {'p_asset_id': asset_id})
            if update_result is False:
                logger.warning(f"RPC функция вернула False для актива {asset_id}")
        except Exception as rpc_error:
            logger.warning(f"Ошибка при обновлении цены актива {asset_id}: {rpc_error}")
        
        # Находим минимальную дату для обновления портфелей
        min_date = min([p.get('trade_date', '') for p in price_data_list], default=None)
        if min_date:
            update_portfolios_with_asset(asset_id, min_date)
        
        return {
            "success": True,
            "message": f"Успешно добавлено {len(price_data_list)} цен",
            "count": len(price_data_list)
        }
    except Exception as e:
        logger.error(f"Ошибка при массовом добавлении цен актива: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def get_asset_info(asset_id: int):
    """
    Получает детальную информацию об активе.
    """
    try:
        # Получаем основную информацию об активе
        asset = table_select(
            "assets",
            select="*",
            filters={"id": asset_id},
            limit=1
        )
        
        if not asset:
            return {"success": False, "error": "Актив не найден"}
        
        asset_info = asset[0]
        
        # Получаем последнюю цену
        latest_price = table_select(
            "asset_latest_prices_full",
            select="*",
            filters={"asset_id": asset_id},
            limit=1
        )
        
        if latest_price:
            asset_info["latest_price"] = latest_price[0]
        else:
            asset_info["latest_price"] = None
        
        return {"success": True, "asset": asset_info}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_asset_price_history(asset_id: int, start_date: str = None, end_date: str = None, limit: int = 1000):
    """
    Получает историю цен актива.
    
    Args:
        asset_id: ID актива
        start_date: Начальная дата (опционально)
        end_date: Конечная дата (опционально)
        limit: Лимит записей
    """
    try:
        filters = {"asset_id": asset_id}
        
        # Применяем фильтры по датам если указаны
        query = table_select(
            "asset_prices",
            select="*",
            filters=filters,
            order={"column": "trade_date", "desc": True},
            limit=limit
        )
        
        # Фильтруем по датам в Python, если нужно
        if start_date or end_date:
            from datetime import datetime, date as date_type
            filtered = []
            for row in query:
                trade_date = row.get("trade_date")
                
                # Нормализуем trade_date до date для сравнения
                if isinstance(trade_date, str):
                    try:
                        trade_date = datetime.fromisoformat(trade_date.replace("Z", "+00:00"))
                    except:
                        try:
                            trade_date = datetime.fromisoformat(trade_date)
                        except:
                            continue
                elif isinstance(trade_date, date_type):
                    trade_date = datetime.combine(trade_date, datetime.min.time())
                
                # Нормализуем до начала дня для сравнения
                trade_date_normalized = trade_date.replace(hour=0, minute=0, second=0, microsecond=0)
                
                if start_date:
                    try:
                        start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                    except:
                        start = datetime.fromisoformat(start_date)
                    start_normalized = start.replace(hour=0, minute=0, second=0, microsecond=0)
                    if trade_date_normalized < start_normalized:
                        continue
                
                if end_date:
                    try:
                        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    except:
                        end = datetime.fromisoformat(end_date)
                    # Включаем саму дату end_date (нормализуем до конца дня)
                    end_normalized = end.replace(hour=23, minute=59, second=59, microsecond=999999)
                    if trade_date_normalized > end_normalized:
                        continue
                
                filtered.append(row)
            query = filtered
        
        return {"success": True, "prices": query, "count": len(query)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_asset_daily_values(portfolio_asset_id: int, from_date: str = None, to_date: str = None):
    """
    Получает историю стоимости актива для графика.
    Использует предрассчитанные данные из portfolio_daily_positions.
    
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
            "p_price_history_limit": 1000  # Лимит для начальной загрузки
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
            "payouts": result.get("all_payouts", []),  # Все выплаты из asset_payouts
            "payouts_count": len(result.get("all_payouts", [])),
            # ОПТИМИЗИРОВАНО: добавляем daily_values и cash_operations из основного запроса
            "daily_values": result.get("daily_values", []),
            "cash_operations": result.get("cash_operations", []),
            "price_history": result.get("price_history", [])  # История цен из того же запроса
        }
        
        # Добавляем информацию о портфелях
        portfolios_data = result.get("portfolios", [])
        for portfolio in portfolios_data:
            portfolio_total = portfolio.get("portfolio_total_value", 0)
            asset_value = portfolio.get("asset_value", 0)
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
    
    Args:
        portfolio_asset_id: ID портфельного актива для перемещения
        target_portfolio_id: ID целевого портфеля
        user_id: ID пользователя (для проверки прав доступа)
    
    Returns:
        dict с результатом операции
    """
    try:
        # 1️⃣ Получаем информацию о портфельном активе
        asset_meta = rpc("get_portfolio_asset_meta", {"p_portfolio_asset_id": portfolio_asset_id})
        
        if not asset_meta:
            return {"success": False, "error": "Портфельный актив не найден"}
        
        # Обрабатываем результат: может быть словарь (если одна запись) или список
        if isinstance(asset_meta, dict):
            meta = asset_meta
        elif isinstance(asset_meta, list) and len(asset_meta) > 0:
            meta = asset_meta[0]
        else:
            return {"success": False, "error": f"Некорректный формат данных актива: {type(asset_meta)}"}
        
        source_portfolio_id = meta.get("portfolio_id")
        asset_id = meta.get("asset_id")
        asset_created_at = meta.get("created_at")
        
        # Получаем дату первой транзакции по перемещенному активу через прямой SQL запрос
        from app.infrastructure.database.supabase_service import get_supabase_client
        supabase = get_supabase_client()
        
        first_tx_result = supabase.table("transactions")\
            .select("transaction_date")\
            .eq("portfolio_asset_id", portfolio_asset_id)\
            .order("transaction_date", desc=False)\
            .limit(1)\
            .execute()
        
        # Используем дату первой транзакции, если она есть, иначе дату создания актива
        first_tx_date = None
        if first_tx_result.data and len(first_tx_result.data) > 0:
            tx_date = first_tx_result.data[0].get("transaction_date")
            if tx_date:
                # Преобразуем в строку формата YYYY-MM-DD
                if isinstance(tx_date, str):
                    first_tx_date = tx_date[:10] if 'T' in tx_date else tx_date
                else:
                    first_tx_date = str(tx_date)[:10]
        
        # Если даты первой транзакции нет, используем дату создания актива
        from_date = first_tx_date if first_tx_date else asset_created_at
        
        # Если и даты создания нет, используем минимальную дату
        if not from_date:
            from_date = "0001-01-01"
        elif isinstance(from_date, str) and 'T' in from_date:
            from_date = from_date[:10]
        
        logger.info(f"Перемещение актива {portfolio_asset_id}: первая транзакция = {first_tx_date}, дата создания = {asset_created_at}, используем {from_date}")
        
        # Проверяем, что целевой портфель существует и отличается от исходного
        if source_portfolio_id == target_portfolio_id:
            return {"success": False, "error": "Актив уже находится в указанном портфеле"}
        
        # Проверяем существование целевого портфеля
        target_portfolio = table_select(
            "portfolios",
            select="id, user_id",
            filters={"id": target_portfolio_id},
            limit=1
        )
        
        if not target_portfolio:
            return {"success": False, "error": "Целевой портфель не найден"}
        
        # Проверяем права доступа (если передан user_id)
        if user_id and target_portfolio[0]["user_id"] != user_id:
            return {"success": False, "error": "Нет доступа к целевому портфелю"}
        
        # 2️⃣ Проверяем, нет ли уже такого актива в целевом портфеле
        existing_asset = table_select(
            "portfolio_assets",
            select="id",
            filters={"portfolio_id": target_portfolio_id, "asset_id": asset_id},
            limit=1
        )
        
        if existing_asset:
            return {
                "success": False,
                "error": "Актив уже существует в целевом портфеле",
                "existing_portfolio_asset_id": existing_asset[0]["id"]
            }
        
        # 3️⃣ Обновляем portfolio_id в portfolio_assets
        table_update(
            "portfolio_assets",
            {"portfolio_id": target_portfolio_id},
            {"id": portfolio_asset_id}
        )
        
        # 6️⃣ Обновляем portfolio_id в portfolio_daily_positions
        table_update(
            "portfolio_daily_positions",
            {"portfolio_id": target_portfolio_id},
            {"portfolio_asset_id": portfolio_asset_id}
        )
        
        # 7️⃣ Пересчитываем позиции перемещенного актива с даты первой транзакции
        update_asset_pos_result = rpc("update_portfolio_asset_positions_from_date", {
            "p_portfolio_asset_id": portfolio_asset_id,
            "p_from_date": from_date
        })
        if update_asset_pos_result is False:
            logger.warning(f"Ошибка при обновлении позиций актива {portfolio_asset_id}")
        
        # 8️⃣ Обновляем графики стоимости для исходного портфеля (с даты первой транзакции)
        update_pos_result = rpc("update_portfolio_positions_from_date", {
            "p_portfolio_id": source_portfolio_id,
            "p_from_date": from_date
        })
        if update_pos_result is False:
            logger.warning(f"Ошибка при обновлении позиций портфеля {source_portfolio_id}")
        
        update_val_result = rpc("update_portfolio_values_from_date", {
            "p_portfolio_id": source_portfolio_id,
            "p_from_date": from_date
        })
        if update_val_result is False:
            logger.warning(f"Ошибка при обновлении значений портфеля {source_portfolio_id}")
        
        # 9️⃣ Обновляем графики стоимости для целевого портфеля (с даты первой транзакции)
        update_pos_result2 = rpc("update_portfolio_positions_from_date", {
            "p_portfolio_id": target_portfolio_id,
            "p_from_date": from_date
        })
        if update_pos_result2 is False:
            logger.warning(f"Ошибка при обновлении позиций портфеля {target_portfolio_id}")
        
        update_val_result2 = rpc("update_portfolio_values_from_date", {
            "p_portfolio_id": target_portfolio_id,
            "p_from_date": from_date
        })
        if update_val_result2 is False:
            logger.warning(f"Ошибка при обновлении значений портфеля {target_portfolio_id}")
        
        # 9️⃣ Пересчитываем данные портфельного актива
        update_pa_result = rpc("update_portfolio_asset", {"pa_id": portfolio_asset_id})
        if update_pa_result is False:
            logger.warning(f"Ошибка при обновлении portfolio_asset {portfolio_asset_id}")
        
        return {
            "success": True,
            "message": "Актив успешно перемещен",
            "portfolio_asset_id": portfolio_asset_id,
            "source_portfolio_id": source_portfolio_id,
            "target_portfolio_id": target_portfolio_id
        }
        
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
    