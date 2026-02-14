from app.infrastructure.database.supabase_service import (
    table_select, table_insert, table_delete, table_update, rpc
)
from app.domain.services.user_service import get_user_by_email
from datetime import datetime
from app.domain.services.transactions_service import create_transaction
from app.domain.services.portfolio_service import update_portfolios_with_asset
from app.utils.date import normalize_date_to_string
from app.core.logging import get_logger

logger = get_logger(__name__)



def create_asset(email: str, data: dict):
    # --- Получаем пользователя ---
    user = get_user_by_email(email)
    if not user:
        return {"success": False, "error": "Пользователь не найден"}

    user_id = user["id"]

    portfolio_id = data.get("portfolio_id")
    asset_id = data.get("asset_id")
    asset_type_id = data.get("asset_type_id")
    name = data.get("name")
    ticker = data.get("ticker")
    quantity = float(data.get("quantity", 0))
    currency = int(data.get("currency")) if data.get("currency") else None
    price = float(data.get("average_price", 0))
    date = data.get("date") or datetime.utcnow().isoformat()

    try:
        # --- Если актив кастомный или новый ---
        if not asset_id:
            existing_asset = table_select(
                "assets",
                select="id, name, ticker, asset_type_id, quote_asset_id",
                filters={"user_id": user_id, "ticker": ticker}
            )

            if existing_asset:
                asset_id = existing_asset[0]["id"]
                name = existing_asset[0]["name"]
                asset_type_id = existing_asset[0]["asset_type_id"]
                currency = existing_asset[0]["quote_asset_id"]
                
                # Проверяем, есть ли цена на эту дату, если нет - добавляем
                existing_price = table_select(
                    "asset_prices",
                    select="id",
                    filters={"asset_id": asset_id, "trade_date": date}
                )
                if not existing_price:
                    # Добавляем цену для существующего актива
                    price_data = {
                        "asset_id": asset_id,
                        "price": price,
                        "trade_date": date,
                    }
                    table_insert("asset_prices", price_data)
                    # Обновляем цену актива
                    update_result = rpc('update_asset_latest_price', {'p_asset_id': asset_id})
                    if update_result is False:
                        logger.warning(f"Ошибка при обновлении цены актива {asset_id}")
                    
                    # Обновляем все портфели, содержащие этот актив
                    update_portfolios_with_asset(asset_id, date)
            else:
                # Создаём кастомный актив
                new_asset = {
                    "asset_type_id": asset_type_id,
                    "user_id": user_id,
                    "name": name,
                    "ticker": ticker,
                    "properties": {},
                    "quote_asset_id": currency
                }
                asset_res = table_insert("assets", new_asset)
                if not asset_res:
                    return {"success": False, "error": "Ошибка при создании кастомного актива"}
                asset_id = asset_res[0]["id"]

                # Добавляем цену кастомного актива
                price_data = {
                    "asset_id": asset_id,
                    "price": price,
                    "trade_date": date,
                }
                table_insert("asset_prices", price_data)
                # Обновляем только новый актив
                update_result = rpc('update_asset_latest_price', {'p_asset_id': asset_id})
                if update_result is False:
                    logger.warning(f"Ошибка при обновлении цены актива {asset_id}")
        else:
            # --- Если системный актив, берём name и ticker из таблицы assets ---
            asset_info = table_select("assets", select="name, ticker", filters={"id": asset_id})
            if asset_info:
                name = asset_info[0]["name"]
                ticker = asset_info[0]["ticker"]

        # --- Проверяем, есть ли актив в портфеле ---
        pa_resp = table_select(
            "portfolio_assets",
            select="id, quantity, average_price",
            filters={"portfolio_id": portfolio_id, "asset_id": asset_id}
        )

        if pa_resp:
            portfolio_asset_id = pa_resp[0]["id"]
            current_quantity = pa_resp[0]["quantity"]
            current_avg_price = pa_resp[0]["average_price"]
            new_quantity = current_quantity + quantity
            new_avg_price = ((current_avg_price * current_quantity) + (price * quantity)) / new_quantity if new_quantity else 0
        else:
            pa_data = {
                "portfolio_id": portfolio_id,
                "asset_id": asset_id,
                "quantity": quantity,
                "average_price": price,
            }
            pa_res = table_insert("portfolio_assets", pa_data)
            if not pa_res:
                return {"success": False, "error": "Ошибка при добавлении актива в портфель"}
            portfolio_asset_id = pa_res[0]["id"]
            new_quantity = quantity
            new_avg_price = price

        # --- Добавляем транзакцию покупки ---
        create_transaction(
            user_id=user_id,
            portfolio_asset_id=portfolio_asset_id,
            asset_id=asset_id,
            transaction_type=1,  # BUY
            quantity=quantity,
            price=price,
            transaction_date=date,
        )

        # --- Обновляем историю портфеля с даты транзакции ---
        # Преобразуем дату транзакции в формат YYYY-MM-DD
        from_date = normalize_date_to_string(date)
        if from_date:
            # Обновляем историю портфеля начиная с даты транзакции
            try:
                update_result = rpc("update_portfolio_values_from_date", {
                    "p_portfolio_id": portfolio_id,
                    "p_from_date": from_date
                })
                if update_result is False:
                    logger.warning(f"Ошибка при обновлении истории портфеля {portfolio_id}")
            except Exception as e:
                logger.error(f"Ошибка при обновлении истории портфеля: {e}", exc_info=True)

        # --- Берём последнюю цену актива ---
        last_price_resp = table_select(
            "asset_prices",
            select="price",
            filters={"asset_id": asset_id},
            order={"column": "trade_date", "desc": True},
            limit=1
        )
        last_price = last_price_resp[0]["price"] if last_price_resp else price

        # --- Формируем объект для фронтенда ---
        asset_obj = {
            "asset_id": asset_id,
            "portfolio_asset_id": portfolio_asset_id,
            "name": name,
            "ticker": ticker,
            "quantity": new_quantity,
            "average_price": new_avg_price,
            "last_price": last_price,
            "total_value": round(new_quantity * last_price, 2),
            # заглушки для остальных полей
            "profit": 0,
            "profit_rub": 0,
            "currency_rate_to_rub": 1,
            "currency_ticker": "RUB",
            "leverage": 1,
            "type": "Неизвестно"
        }

        return {"success": True, "message": "Актив успешно добавлен в портфель", "asset": asset_obj}

    except Exception as e:
        logger.error(f"Ошибка при добавлении актива: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
 

def delete_asset(portfolio_asset_id: int):
    """
    Удаляет актив из портфеля.
    
    Порядок удаления (важно для соблюдения foreign key constraints):
      1. transactions, fifo_lots (связаны с portfolio_asset_id)
      2. portfolio_assets
      3. Если актив кастомный:
         - asset_prices
         - asset_latest_prices_full (ВАЖНО: перед удалением assets)
         - assets
    
    ВАЖНО: 
    - Для системных активов НЕ удаляем asset_latest_prices_full и assets,
      так как актив остается в системе для других пользователей.
    - asset_latest_prices_full имеет foreign key на assets(id),
      поэтому удаляется ПЕРЕД удалением assets.
    """
    try:
        # 1️⃣ Проверяем существование portfolio_asset
        pa_resp = table_select('portfolio_assets', select='asset_id', filters={"id": portfolio_asset_id})

        if not pa_resp:
            return {"success": False, "error": f"Портфельный актив с ID {portfolio_asset_id} не найден"}

        asset_id = pa_resp[0]["asset_id"]

        # 2️⃣ Получаем данные актива через RPC
        try:
            asset_meta = rpc("get_portfolio_asset_meta", {"p_portfolio_asset_id": portfolio_asset_id})
        except Exception as rpc_error:
            logger.warning(f"Ошибка при вызове get_portfolio_asset_meta: {rpc_error}")
            return {"success": False, "error": f"Ошибка при получении данных актива: {str(rpc_error)}"}

        # Проверяем результат RPC
        if not asset_meta:
            return {"success": False, "error": f"Метаданные актива не найдены для portfolio_asset_id {portfolio_asset_id}"}
        
        # Обрабатываем результат: может быть словарь (если одна запись) или список
        if isinstance(asset_meta, dict):
            # Если это словарь, используем его напрямую
            portfolio_id = asset_meta.get("portfolio_id")
            is_custom = asset_meta.get("is_custom", False)
        elif isinstance(asset_meta, list) and len(asset_meta) > 0:
            # Если это список, берем первый элемент
            portfolio_id = asset_meta[0].get("portfolio_id")
            is_custom = asset_meta[0].get("is_custom", False)
        else:
            return {"success": False, "error": f"Некорректный формат данных актива: {type(asset_meta)}"}
        
        if not portfolio_id:
            return {"success": False, "error": "Не удалось определить portfolio_id"}

        # 3️⃣ Удаляем все транзакции
        try:
            table_delete("transactions", {"portfolio_asset_id": portfolio_asset_id})
        except Exception as e:
            logger.warning(f"Ошибка при удалении транзакций: {e}", exc_info=True)

        try:
            table_delete("fifo_lots", {"portfolio_asset_id": portfolio_asset_id})
        except Exception as e:
            logger.warning(f"Ошибка при удалении fifo_lots: {e}", exc_info=True)

        # 4️⃣ Удаляем саму запись portfolio_assets
        try:
            table_delete("portfolio_assets", {"id": portfolio_asset_id})
        except Exception as e:
            logger.warning(f"Ошибка при удалении portfolio_assets: {e}", exc_info=True)
            return {"success": False, "error": f"Ошибка при удалении portfolio_assets: {str(e)}"}

        # 5️⃣ Если актив кастомный — удаляем и сам актив
        if is_custom:
            try:
                # Удаляем историю цен актива (все записи с этим asset_id)
                # ВАЖНО: asset_prices имеет foreign key на assets, поэтому удаляем перед assets
                deleted_prices = table_delete("asset_prices", {"asset_id": asset_id})
                if deleted_prices:
                    logger.info(f"Удалено записей из asset_prices для актива {asset_id}: {len(deleted_prices) if isinstance(deleted_prices, list) else 'N/A'}")
                else:
                    logger.debug(f"Не найдено записей в asset_prices для актива {asset_id}")
                
                # Удаляем запись из asset_latest_prices_full (ВАЖНО: перед удалением актива из-за foreign key)
                # Это нужно делать только для кастомных активов, которые будут удалены
                try:
                    deleted_latest = table_delete("asset_latest_prices_full", {"asset_id": asset_id})
                    if deleted_latest:
                        logger.info(f"Удалена запись из asset_latest_prices_full для актива {asset_id}")
                    else:
                        logger.debug(f"Не найдено записи в asset_latest_prices_full для актива {asset_id}")
                except Exception as e:
                    logger.warning(f"Ошибка при удалении из asset_latest_prices_full: {e}", exc_info=True)
                    import traceback
                    traceback.print_exc()
                    # Не прерываем выполнение, но логируем ошибку
                
                # Удаляем сам актив (должно быть последним, чтобы не нарушить внешние ключи)
                # Порядок удаления:
                # 1. asset_prices (удалено выше)
                # 2. asset_latest_prices_full (удалено выше)
                # 3. assets (удаляем сейчас)
                deleted_asset = table_delete("assets", {"id": asset_id})
                if deleted_asset:
                    logger.info(f"Удален кастомный актив {asset_id}")
                else:
                    logger.warning(f"Не удалось удалить актив {asset_id} из таблицы assets")
            except Exception as e:
                logger.error(f"Ошибка при удалении кастомного актива: {e}", exc_info=True)
                import traceback
                traceback.print_exc()
                # Не прерываем выполнение, но логируем ошибку

        # 7️⃣ Обновляем ежедневные позиции и значения портфеля
        try:
            table_delete("portfolio_daily_positions", {"portfolio_asset_id": portfolio_asset_id})
        except Exception as e:
            logger.warning(f"Ошибка при удалении portfolio_daily_positions: {e}", exc_info=True)
        
        # Обновляем историю портфеля (не критично, если не удастся)
        try:
            update_result = rpc("update_portfolio_values_from_date", {"p_portfolio_id": portfolio_id})
            if update_result is False:
                logger.warning(f"Ошибка при обновлении истории портфеля {portfolio_id}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении истории портфеля: {e}", exc_info=True)

        return {"success": True, "message": "Актив и связанные записи успешно удалены"}

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
            from datetime import datetime
            filtered = []
            for row in query:
                trade_date = row.get("trade_date")
                if isinstance(trade_date, str):
                    trade_date = datetime.fromisoformat(trade_date.replace("Z", "+00:00"))
                
                if start_date:
                    start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                    if trade_date < start:
                        continue
                
                if end_date:
                    end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    if trade_date > end:
                        continue
                
                filtered.append(row)
            query = filtered
        
        return {"success": True, "prices": query, "count": len(query)}
    except Exception as e:
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
            "currency_rate_to_rub": portfolio_asset_data.get("currency_rate_to_rub"),
            "name": portfolio_asset_data.get("asset_name"),
            "ticker": portfolio_asset_data.get("ticker"),
            "type": portfolio_asset_data.get("asset_type"),
            "transactions": result.get("transactions", []),
            "transactions_count": len(result.get("transactions", [])),
            "payouts": result.get("all_payouts", []),  # Все выплаты из asset_payouts
            "payouts_count": len(result.get("all_payouts", [])),
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
        
        # 7️⃣ Обновляем графики стоимости для исходного портфеля
        update_pos_result = rpc("update_portfolio_positions_from_date", {"p_portfolio_id": source_portfolio_id, "p_from_date": asset_created_at})
        if update_pos_result is False:
            logger.warning(f"Ошибка при обновлении позиций портфеля {source_portfolio_id}")
        
        update_val_result = rpc("update_portfolio_values_from_date", {"p_portfolio_id": source_portfolio_id, "p_from_date": asset_created_at})
        if update_val_result is False:
            logger.warning(f"Ошибка при обновлении значений портфеля {source_portfolio_id}")
        
        # 8️⃣ Обновляем графики стоимости для целевого портфеля
        update_pos_result2 = rpc("update_portfolio_positions_from_date", {"p_portfolio_id": target_portfolio_id, "p_from_date": asset_created_at})
        if update_pos_result2 is False:
            logger.warning(f"Ошибка при обновлении позиций портфеля {target_portfolio_id}")
        
        update_val_result2 = rpc("update_portfolio_values_from_date", {"p_portfolio_id": target_portfolio_id, "p_from_date": asset_created_at})
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
    