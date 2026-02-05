import asyncio
from app.services.supabase_service import rpc, table_select, table_insert, table_update, table_delete
from app.services.supabase_async import rpc_async, table_select_async, table_insert_async
from app.services.user_service import get_user_by_email
from concurrent.futures import ThreadPoolExecutor
from time import time
import json
from datetime import datetime, timezone, date

def normalize_tx_date_day(dt):
    """Возвращает только дату (YYYY-MM-DD) без времени."""
    if not dt:
        return None
    
    # Если это уже date объект
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d")
    
    # Если это datetime объект
    if isinstance(dt, datetime):
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%d")
    
    # Если это строка
    if isinstance(dt, str):
        try:
            # Сначала пробуем стандартный ISO формат
            dt_obj = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            if dt_obj.tzinfo:
                dt_obj = dt_obj.astimezone(timezone.utc)
            return dt_obj.strftime("%Y-%m-%d")
        except ValueError:
            # Если не получилось, извлекаем дату из строки (YYYY-MM-DD)
            try:
                # Ищем паттерн даты YYYY-MM-DD в начале строки
                if 'T' in dt:
                    date_part = dt.split('T')[0]
                elif ' ' in dt:
                    date_part = dt.split(' ')[0]
                else:
                    date_part = dt[:10] if len(dt) >= 10 else dt
                
                # Проверяем, что это валидная дата
                dt_obj = datetime.strptime(date_part, "%Y-%m-%d")
                return dt_obj.strftime("%Y-%m-%d")
            except (ValueError, AttributeError, IndexError):
                return None
    
    return None


# Асинхронные обертки для RPC функций
async def get_user_portfolios(user_email: str):
    """Асинхронная обертка для get_user_portfolios_sync."""
    return await asyncio.to_thread(get_user_portfolios_sync, user_email)

async def get_portfolio_assets(portfolio_id: int):
    """Асинхронная обертка для get_portfolio_assets_sync."""
    return await asyncio.to_thread(get_portfolio_assets_sync, portfolio_id)

async def get_portfolio_transactions(portfolio_id: int):
    """Асинхронная обертка для get_portfolio_transactions_sync."""
    return await asyncio.to_thread(get_portfolio_transactions_sync, portfolio_id)

async def get_portfolio_value_history(portfolio_id: int):
    """Асинхронная обертка для get_portfolio_value_history_sync."""
    return await asyncio.to_thread(get_portfolio_value_history_sync, portfolio_id)


def get_user_portfolios_sync(user_email: str):
    user = get_user_by_email(user_email)
    return rpc("get_user_portfolios", {"u_id": user["id"]})

def get_portfolio_assets_sync(portfolio_id: int):
    return rpc("get_portfolio_assets", {"p_portfolio_id": portfolio_id})

def get_portfolio_transactions_sync(portfolio_id: int):
    return rpc("get_portfolio_transactions", {"p_portfolio_id": portfolio_id})

def get_portfolio_value_history_sync(portfolio_id: int):
    return  rpc("get_portfolio_value_history", {"p_portfolio_id": portfolio_id})


def get_user_portfolios_with_assets_and_history(user_id: str):
    """Загружает все портфели, активы и историю за один запрос."""
    start = time()
    data = rpc("get_all_portfolios_with_assets_and_history", {"p_user_id": user_id})
    print("📦 Данные получены за", time() - start, "сек")
    return data or []

def update_portfolio_description(portfolio_id: int, text: str = None, capital_target_name: str = None,
                                 capital_target_value: float = None, capital_target_deadline: str = None,
                                 capital_target_currency: str = "RUB"):
    # Получаем текущее описание
    portfolio = table_select("portfolios", select="description", filters={"id": portfolio_id})
    desc = portfolio[0].get("description") or {}

    if text is not None:
        desc["text"] = text
    if capital_target_name is not None:
        desc["capital_target_name"] = capital_target_name
    if capital_target_value is not None:
        desc["capital_target_value"] = capital_target_value
    if capital_target_deadline is not None:
        desc["capital_target_deadline"] = capital_target_deadline
    if capital_target_currency is not None:
        desc["capital_target_currency"] = capital_target_currency

    # Обновляем запись
    return table_update("portfolios", {"description": desc}, filters={"id": portfolio_id})

async def get_user_portfolio_parent(user_email: str):
    portfolios = await get_user_portfolios(user_email)
    for portfolio in portfolios:
        if not portfolio["parent_portfolio_id"]:
            return portfolio
    return None


def get_portfolio_info(portfolio_id: int):
    """
    Получает детальную информацию о портфеле.
    """
    try:
        # Получаем основную информацию о портфеле
        portfolio = table_select(
            "portfolios",
            select="*",
            filters={"id": portfolio_id},
            limit=1
        )
        
        if not portfolio:
            return {"success": False, "error": "Портфель не найден"}
        
        portfolio_info = portfolio[0]
        
        # Получаем активы портфеля
        assets = get_portfolio_assets_sync(portfolio_id)
        portfolio_info["assets"] = assets
        portfolio_info["assets_count"] = len(assets) if assets else 0
        
        # Получаем транзакции портфеля
        transactions = get_portfolio_transactions_sync(portfolio_id)
        portfolio_info["transactions"] = transactions
        portfolio_info["transactions_count"] = len(transactions) if transactions else 0
        
        # Получаем историю стоимости
        history = get_portfolio_value_history_sync(portfolio_id)
        portfolio_info["value_history"] = history if history else []
        
        return {"success": True, "portfolio": portfolio_info}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_portfolio_summary(portfolio_id: int):
    """
    Получает краткую сводку по портфелю (без детальной истории).
    """
    try:
        portfolio = table_select(
            "portfolios",
            select="*",
            filters={"id": portfolio_id},
            limit=1
        )
        
        if not portfolio:
            return {"success": False, "error": "Портфель не найден"}
        
        portfolio_info = portfolio[0]
        
        # Получаем только активы
        assets = get_portfolio_assets_sync(portfolio_id)
        portfolio_info["assets"] = assets
        portfolio_info["assets_count"] = len(assets) if assets else 0
        
        # Вычисляем общую стоимость портфеля
        total_value = 0
        if assets:
            for asset in assets:
                total_value += asset.get("total_value", 0) or 0
        
        portfolio_info["total_value"] = total_value
        
        return {"success": True, "portfolio": portfolio_info}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- пул потоков для фоновых операций ---
executor = ThreadPoolExecutor(max_workers=10)


async def table_insert_bulk_async(table: str, rows: list[dict]):
    """Батчевая вставка данных в таблицу."""
    if not rows:
        return True
    # Используем асинхронную обертку вместо executor
    await table_insert_async(table, rows)
    return True

async def import_broker_portfolio(email: str, parent_portfolio_id: int, broker_data: dict):
    """
    Оптимизированный импорт транзакций портфелей брокера:
    1) создаём дочерние портфели (если нужно)
    2) загружаем существующие транзакции и операции
    3) добавляем только новые транзакции/операции (без дубликатов)
    4) обновляем историю портфеля только с даты самой старой новой транзакции
    """

    user = get_user_by_email(email)
    user_id = user["id"]

    # Загружаем типы операций
    op_types = await table_select_async("operations_type", select="id, name")
    op_type_map = {o["name"].lower(): o["id"] for o in op_types}

    # Загружаем все активы
    all_assets = await rpc_async("get_all_assets", {})
    isin_to_asset = {
        a["properties"].get("isin"): a["id"]
        for a in all_assets
        if a["properties"] and a["properties"].get("isin")
    }

    for portfolio_name, pdata in broker_data.items():

        print(f"📦 Синхронизируем портфель '{portfolio_name}'")

        # --- 1. ищем или создаём дочерний портфель ---
        existing = await table_select_async(
            "portfolios", select="id",
            filters={"parent_portfolio_id": parent_portfolio_id, "name": portfolio_name}
        )

        if not existing:
            print(f"➕ Создаём дочерний портфель '{portfolio_name}'...")
            inserted = await table_insert_async("portfolios", {
                "user_id": user_id,
                "parent_portfolio_id": parent_portfolio_id,
                "name": portfolio_name,
                "description": {"source": "tinkoff"}
            })

            if inserted:
                portfolio_id = inserted[0]["id"]
            else:
                # ищем повторно
                pf = await table_select_async(
                    "portfolios", select="id",
                    filters={"parent_portfolio_id": parent_portfolio_id, "name": portfolio_name}
                )
                if not pf:
                    raise Exception(f"Не удалось создать портфель '{portfolio_name}'!")
                portfolio_id = pf[0]["id"]
            pa_map = {}
            existing_tx_keys = set()
            existing_ops_keys = set()
        else:
            portfolio_id = existing[0]["id"]

            # ========================
            # 2. Загружаем существующие транзакции и операции для проверки дубликатов
            # ========================

            print(f"🔍 Проверяем существующие транзакции портфеля '{portfolio_name}' (id={portfolio_id})")

            # Получаем все portfolio_asset_id этого портфеля
            pa_rows = await table_select_async(
                "portfolio_assets",
                select="id, asset_id",
                filters={"portfolio_id": portfolio_id}
            )
            pa_map = {row["asset_id"]: row["id"] for row in pa_rows}
            pa_ids = [row["id"] for row in pa_rows]

            # Загружаем существующие транзакции
            existing_tx_keys = set()
            if pa_ids:
                existing_transactions = await table_select_async(
                    "transactions",
                    select="portfolio_asset_id,transaction_date,transaction_type,price,quantity",
                    in_filters={"portfolio_asset_id": pa_ids}
                )
                
                for tx in existing_transactions:
                    # Нормализуем дату до дня (YYYY-MM-DD)
                    tx_date = normalize_tx_date_day(tx["transaction_date"])
                    if not tx_date:
                        continue
                    # Округляем price и quantity для сравнения
                    price = round(float(tx.get("price") or 0), 6)
                    qty = round(float(tx.get("quantity") or 0), 6)
                    tx_type = tx.get("transaction_type")
                    # Ключ уникальности: (portfolio_asset_id, date, type, price, quantity)
                    existing_tx_keys.add((tx["portfolio_asset_id"], tx_date, tx_type, price, qty))

            # Загружаем существующие денежные операции
            existing_ops_keys = set()
            existing_ops = await table_select_async(
                "cash_operations",
                select="portfolio_id,type,date,amount,asset_id",
                filters={"portfolio_id": portfolio_id}
            )
            
            print(f"   📋 Загружено {len(existing_ops)} существующих денежных операций из БД")
            
            for op in existing_ops:
                # Нормализуем дату до дня
                op_date = normalize_tx_date_day(op["date"])
                if not op_date:
                    print(f"   ⚠️ Пропущена операция из-за невалидной даты: {op}")
                    continue
                # Округляем amount до 2 знаков для денежных операций (копейки)
                # Это решает проблему с разной точностью хранения в БД
                amount = round(float(op.get("amount") or 0), 2)
                # Нормализуем типы для корректного сравнения
                op_portfolio_id = int(op.get("portfolio_id") or 0)
                op_type = int(op.get("type") or 0)
                # Нормализуем asset_id: приводим к int или None
                asset_id_raw = op.get("asset_id")
                asset_id = int(asset_id_raw) if asset_id_raw is not None else None
                # Ключ уникальности: (portfolio_id, type, date, amount, asset_id)
                key = (op_portfolio_id, op_type, op_date, amount, asset_id)
                existing_ops_keys.add(key)

            print(f"   ✔ Найдено существующих: {len(existing_tx_keys)} транзакций, {len(existing_ops_keys)} операций")
            # Отладочный вывод первых нескольких ключей для проверки
            if existing_ops_keys and len(existing_ops_keys) > 0:
                sample_keys = list(existing_ops_keys)[:3]
                print(f"   🔍 Примеры ключей существующих операций: {sample_keys}")

        # ========================
        # 3. Фильтруем и добавляем только новые транзакции брокера
        # ========================

        new_tx = []
        new_ops = []
        affected_pa = set()
        min_tx_date = None  # Самая старая дата новой транзакции
        min_op_date = None  # Самая старая дата новой денежной операции

        for tx in pdata["transactions"]:
            tx_type = tx["type"]
            tx_date = tx["date"]
            isin = tx.get("isin")
            payment = float(tx.get("payment") or 0)
            asset_id = isin_to_asset[isin] if isin in isin_to_asset else None

            # Покупка / продажа
            if tx_type in ("Buy", "Sell"):
                if not isin or isin not in isin_to_asset:
                    continue

                # portfolio_asset_id, если нет — создаём
                pa_id = pa_map.get(asset_id)
                if not pa_id:
                    pa_inserted = await table_insert_async("portfolio_assets", {
                        "portfolio_id": portfolio_id,
                        "asset_id": asset_id,
                        "quantity": 0,
                        "average_price": 0
                    })
                    pa_id = pa_inserted[0]["id"]
                    pa_map[asset_id] = pa_id

                # Нормализуем дату и значения для проверки
                tx_date_normalized = normalize_tx_date_day(tx_date)
                if not tx_date_normalized:
                    continue
                
                price = round(float(tx["price"]), 6)
                qty = round(float(tx["quantity"]), 6)
                tx_type_id = 1 if tx_type == "Buy" else 2
                
                # Проверяем, существует ли уже такая транзакция
                tx_key = (pa_id, tx_date_normalized, tx_type_id, price, qty)
                if tx_key in existing_tx_keys:
                    continue  # Пропускаем дубликат

                # Добавляем в множество существующих, чтобы не дублировать в рамках одного импорта
                existing_tx_keys.add(tx_key)
                affected_pa.add(pa_id)

                # Обновляем минимальную дату
                if min_tx_date is None or tx_date_normalized < min_tx_date:
                    min_tx_date = tx_date_normalized

                new_tx.append({
                    "portfolio_asset_id": pa_id,
                    "transaction_type": tx_type_id,
                    "price": float(tx["price"]),
                    "quantity": float(tx["quantity"]),
                    "transaction_date": tx_date,
                    "user_id": user_id
                })

            else:
                # Денежные операции
                if abs(payment) < 1e-8:
                    continue

                op_type_id = op_type_map.get(tx_type.lower())
                if not op_type_id:
                    continue

                # Нормализуем дату и значения для проверки
                op_date_normalized = normalize_tx_date_day(tx_date)
                if not op_date_normalized:
                    continue
                
                # Округляем amount до 2 знаков для денежных операций (копейки)
                # Это решает проблему с разной точностью хранения в БД
                amount = round(payment, 2)
                
                # Нормализуем все значения для корректного сравнения
                portfolio_id_int = int(portfolio_id) if portfolio_id else 0
                op_type_id_int = int(op_type_id) if op_type_id else 0
                asset_id_normalized = int(asset_id) if asset_id is not None else None
                
                # Проверяем, существует ли уже такая операция
                op_key = (portfolio_id_int, op_type_id_int, op_date_normalized, amount, asset_id_normalized)
                
                # Проверяем точное совпадение
                if op_key in existing_ops_keys:
                    continue  # Пропускаем дубликат
                
                # Добавляем в множество существующих
                existing_ops_keys.add(op_key)
                
                # Обновляем минимальную дату для денежных операций
                if min_op_date is None or op_date_normalized < min_op_date:
                    min_op_date = op_date_normalized

                new_ops.append({
                    "user_id": user_id,
                    "portfolio_id": portfolio_id,
                    "type": op_type_id,
                    "amount": payment,
                    "currency": 47,   # рубли
                    "date": tx_date,
                    "asset_id": asset_id,
                    "transaction_id": None
                })

        # Вставляем только новые записи
        if new_tx:
            # Сортируем транзакции по дате перед вставкой, чтобы FIFO работал корректно
            # Это важно для правильного расчета FIFO - транзакции должны обрабатываться в хронологическом порядке
            new_tx_sorted = sorted(new_tx, key=lambda x: (
                datetime.fromisoformat(x["transaction_date"].replace("Z", "+00:00")) if isinstance(x["transaction_date"], str) 
                else x["transaction_date"] if isinstance(x["transaction_date"], datetime)
                else datetime.min
            ))
            
            print(f"   ➕ Добавляем {len(new_tx_sorted)} новых транзакций (отсортированы по дате)...")
            try:
                await table_insert_bulk_async("transactions", new_tx_sorted)
                print(f"   ✅ Транзакции успешно добавлены")
            except Exception as e:
                print(f"   ❌ Ошибка при добавлении транзакций: {e}")
                import traceback
                traceback.print_exc()

        if new_ops:
            print(f"   ➕ Добавляем {len(new_ops)} новых денежных операций...")
            try:
                await table_insert_bulk_async("cash_operations", new_ops)
                print(f"   ✅ Денежные операции успешно добавлены")
                
                # Проверяем, что операции действительно добавились
                # Загружаем операции снова для проверки
                check_ops = await table_select_async(
                    "cash_operations",
                    select="id,portfolio_id,type,date,amount",
                    filters={"portfolio_id": portfolio_id}
                )
                print(f"   📊 Всего операций в портфеле после добавления: {len(check_ops) if check_ops else 0}")
            except Exception as e:
                print(f"   ❌ Ошибка при добавлении денежных операций: {e}")
                import traceback
                traceback.print_exc()

        if not new_tx and not new_ops:
            print("   ℹ️ Новых транзакций и операций не найдено")
            continue

        # ========================
        # 4. Пересчёт активов (только для затронутых активов)
        # ========================
        if affected_pa:
            print(f"   🔄 Пересчитываем {len(affected_pa)} активов...")
            for pa_id in affected_pa:
                await rpc_async("update_portfolio_asset", {"pa_id": pa_id})

        
        # ==========================
        # 5. Обновление истории портфеля с даты самой старой новой транзакции или операции
        # ==========================
        
        # Определяем минимальную дату для обновления (из транзакций или операций)
        min_date = None
        if min_tx_date and min_op_date:
            # Если есть и транзакции, и операции, берем самую раннюю дату
            min_date = min_tx_date if min_tx_date < min_op_date else min_op_date
        elif min_tx_date:
            min_date = min_tx_date
        elif min_op_date:
            min_date = min_op_date
        
        if min_date:
            print(f"   📊 Обновляем историю портфеля с даты {min_date}...")
            
            # Преобразуем дату в формат для SQL функции (YYYY-MM-DD)
            if isinstance(min_date, str):
                from_date_str = min_date[:10] if len(min_date) > 10 else min_date
            elif hasattr(min_date, 'isoformat'):
                from_date_str = min_date.isoformat()[:10]
            else:
                from_date_str = str(min_date)[:10]
            
            # Обновляем FIFO (только если есть транзакции, т.к. FIFO связан с транзакциями)
            if min_tx_date:
                try:
                    await rpc_async("rebuild_fifo_for_portfolio", {"p_portfolio_id": portfolio_id})
                    print('   ✔ Fifo данные обновлены')
                except Exception as e:
                    error_msg = str(e)
                    # Ошибка "Not enough quantity to sell" может возникать из-за:
                    # 1. Транзакции в неправильном порядке (исправлено сортировкой выше)
                    # 2. Проблемы с данными (продажи до покупок)
                    # 3. Проблемы с существующими данными в БД
                    if "Not enough quantity" in error_msg or "P0001" in str(e):
                        print(f'   ⚠️ Ошибка обновления FIFO (возможно, проблема с порядком транзакций или данными): {error_msg}')
                        print(f'   💡 Это может быть связано с некорректными данными в БД. Проверьте транзакции для portfolio_asset_id из ошибки.')
                        # Не прерываем процесс, продолжаем обновление позиций и значений
                    else:
                        print(f'   ⚠️ Ошибка обновления FIFO: {error_msg}')
            
            # Обновляем позиции с даты самой старой новой транзакции или операции
            try:
                await rpc_async("update_portfolio_positions_from_date", {"p_portfolio_id": portfolio_id, "p_from_date": from_date_str})
                print('   ✔ Positions данные обновлены')
            except Exception as e:
                print(f'   ⚠️ Ошибка обновления позиций: {e}')
            
            # Обновляем значения с даты самой старой новой транзакции или операции
            try:
                await rpc_async("update_portfolio_values_from_date", {"p_portfolio_id": portfolio_id, "p_from_date": from_date_str})
                print('   ✔ Values данные обновлены')
            except Exception as e:
                print(f'   ⚠️ Ошибка обновления значений: {e}')
        else:
            print("   ℹ️ Нет новых данных для обновления истории")

        print(f"🎯 Готово: добавлено {len(new_tx)} транзакций, {len(new_ops)} денежн. операций")

    return {"success": True}





