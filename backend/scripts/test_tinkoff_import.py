"""
Скрипт для ручного тестирования импорта портфелей от Tinkoff.

Использование:
    python scripts/test_tinkoff_import.py

Требуется переменная окружения TINKOFF_TOKEN с токеном доступа к Tinkoff Invest API.
"""
import os
import sys
import asyncio
from pathlib import Path
from collections import Counter
from datetime import datetime

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.external.brokers.tinkoff import get_tinkoff_portfolio
from app.infrastructure.external.brokers.tinkoff.import_service import OPERATION_CLASSIFICATION
from app.infrastructure.database.postgres_async import table_select_async, rpc_async, close_connection_pool
from app.utils.async_runner import run_async


async def main():
    """Основная функция для тестирования импорта."""
    token = os.getenv("TINKOFF_TOKEN")
    
    if not token:
        print("❌ ОШИБКА: TINKOFF_TOKEN не установлен!")
        print("\nУстановите переменную окружения:")
        print("  Windows PowerShell: $env:TINKOFF_TOKEN='your_token_here'")
        print("  Windows CMD: set TINKOFF_TOKEN=your_token_here")
        print("  Linux/Mac: export TINKOFF_TOKEN='your_token_here'")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("ТЕСТИРОВАНИЕ ИМПОРТА ПОРТФЕЛЯ TINKOFF")
    print("="*80)
    print()
    
    try:
        # Получаем данные портфеля
        print("📥 Получаем данные от брокера Tinkoff...")
        result = get_tinkoff_portfolio(token)
        
        if not result:
            print("⚠️  Портфель пуст (нет доступных счетов)")
            return
        
        print(f"\n✅ Получено данных для {len(result)} счетов\n")
        
        # Анализ структуры портфеля
        print("="*80)
        print("СТРУКТУРА ПОРТФЕЛЯ")
        print("="*80)
        
        total_positions = 0
        total_transactions = 0
        all_operation_types = []
        
        for account_name, account_data in result.items():
            positions = account_data.get("positions", [])
            transactions = account_data.get("transactions", [])
            
            total_positions += len(positions)
            total_transactions += len(transactions)
            
            # Собираем типы операций
            for transaction in transactions:
                op_type = transaction.get("type")
                if op_type:
                    all_operation_types.append(op_type)
            
            print(f"\n📁 Счёт: {account_name}")
            print(f"   ID: {account_data.get('account_id')}")
            print(f"   Позиций: {len(positions)}")
            print(f"   Транзакций: {len(transactions)}")
            
            if positions:
                print("\n   Все позиции:")
                for pos in positions:
                    ticker = pos.get("ticker") or "N/A"
                    name = pos.get("name") or "N/A"
                    quantity = pos.get("quantity", 0)
                    current_price = pos.get("current_price", 0)
                    value = quantity * current_price
                    print(f"     - {ticker:15} | {name[:35]:35} | {quantity:>10.2f} шт. × {current_price:>10.2f} = {value:>12.2f}")
            
            if transactions:
                # Сортируем транзакции по дате (от новых к старым)
                sorted_transactions = sorted(
                    transactions,
                    key=lambda tx: tx.get("date", ""),
                    reverse=True
                )
                
                print("\n   5 последних операций:")
                print(f"     {'Дата':<20} | {'Тип':<15} | {'Тикер':<15} | {'Количество':>12} | {'Сумма':>15}")
                print(f"     {'-'*20} | {'-'*15} | {'-'*15} | {'-'*12} | {'-'*15}")
                for tx in sorted_transactions[:5]:
                    tx_type = tx.get("type", "N/A")
                    date = tx.get("date", "N/A")[:19] if tx.get("date") else "N/A"  # Обрезаем до секунд
                    ticker = (tx.get("ticker") or "—")[:15]
                    payment = tx.get("payment", 0)
                    quantity = tx.get("quantity")
                    if quantity is not None:
                        qty_str = f"{quantity:>10.2f} шт."
                    else:
                        qty_str = f"{'':>12}"
                    payment_str = f"{payment:>15,.2f}"
                    print(f"     {date:<20} | {tx_type:<15} | {ticker:<15} | {qty_str:>12} | {payment_str:>15}")
                
                # Группируем операции по типам и показываем по одной каждого типа
                operations_by_type = {}
                for tx in transactions:
                    tx_type = tx.get("type", "N/A")
                    if tx_type not in operations_by_type:
                        operations_by_type[tx_type] = tx
                
                if operations_by_type:
                    print("\n   По одной операции каждого типа:")
                    print(f"     {'Дата':<20} | {'Тип':<15} | {'Тикер':<15} | {'Количество':>12} | {'Сумма':>15}")
                    print(f"     {'-'*20} | {'-'*15} | {'-'*15} | {'-'*12} | {'-'*15}")
                    for tx_type in sorted(operations_by_type.keys()):
                        tx = operations_by_type[tx_type]
                        date = tx.get("date", "N/A")[:19] if tx.get("date") else "N/A"  # Обрезаем до секунд
                        ticker = (tx.get("ticker") or "—")[:15]
                        payment = tx.get("payment", 0)
                        quantity = tx.get("quantity")
                        if quantity is not None:
                            qty_str = f"{quantity:>10.2f} шт."
                        else:
                            qty_str = f"{'':>12}"
                        payment_str = f"{payment:>15,.2f}"
                        print(f"     {date:<20} | {tx_type:<15} | {ticker:<15} | {qty_str:>12} | {payment_str:>15}")
        
        print("\n" + "="*80)
        print(f"ИТОГО: {total_positions} позиций, {total_transactions} транзакций")
        print("="*80)
        
        # Анализ типов операций
        print("\n" + "="*80)
        print("АНАЛИЗ ТИПОВ ОПЕРАЦИЙ")
        print("="*80)
        
        if not all_operation_types:
            print("\n⚠️  Операции не найдены")
        else:
            known_types = set(OPERATION_CLASSIFICATION.values())
            type_counter = Counter(all_operation_types)
            
            print("\n📊 Все типы операций (с частотой):")
            for op_type, count in type_counter.most_common():
                status = "✅" if op_type in known_types else "❌ НЕИЗВЕСТНЫЙ"
                print(f"  {status} {op_type:20} : {count:>5} операций")
            
            unknown_types = set(all_operation_types) - known_types
            
            if unknown_types:
                print(f"\n⚠️  НАЙДЕНО {len(unknown_types)} НЕИЗВЕСТНЫХ ТИПОВ ОПЕРАЦИЙ:")
                print("\n   Неизвестные типы:")
                for unknown_type in sorted(unknown_types):
                    count = type_counter[unknown_type]
                    print(f"     - {unknown_type:20} : {count:>5} операций")
                
                print("\n💡 Добавьте эти типы в OPERATION_CLASSIFICATION в:")
                print("   app/infrastructure/external/brokers/tinkoff/import_service.py")
                print("\n   Пример:")
                for unknown_type in sorted(unknown_types):
                    print(f'     "{unknown_type}": "Unknown",')
            else:
                print("\n✅ Все типы операций известны и обработаны")
        
        # Проверка payment для транзакций Buy/Sell/Redemption
        print("\n" + "="*80)
        print("ПРОВЕРКА PAYMENT ДЛЯ ТРАНЗАКЦИЙ")
        print("="*80)
        
        transactions_with_zero_payment = []
        transactions_without_payment = []
        
        for account_name, account_data in result.items():
            for tx in account_data.get("transactions", []):
                tx_type = tx.get("type")
                if tx_type in ("Buy", "Sell", "Redemption"):
                    payment = tx.get("payment")
                    price = tx.get("price")
                    quantity = tx.get("quantity")
                    
                    if payment is None:
                        transactions_without_payment.append({
                            "account": account_name,
                            "type": tx_type,
                            "date": tx.get("date"),
                            "ticker": tx.get("ticker"),
                            "price": price,
                            "quantity": quantity
                        })
                    elif payment == 0 and price is not None and quantity is not None and price != 0 and quantity != 0:
                        expected_payment = price * quantity
                        transactions_with_zero_payment.append({
                            "account": account_name,
                            "type": tx_type,
                            "date": tx.get("date"),
                            "ticker": tx.get("ticker"),
                            "price": price,
                            "quantity": quantity,
                            "payment": payment,
                            "expected_payment": expected_payment
                        })
        
        if transactions_without_payment:
            print(f"\n❌ НАЙДЕНО {len(transactions_without_payment)} ТРАНЗАКЦИЙ БЕЗ PAYMENT:")
            for tx in transactions_without_payment[:10]:  # Показываем первые 10
                print(f"   - {tx['date']} | {tx['type']:10} | {tx['ticker']:10} | "
                      f"price: {tx['price']}, quantity: {tx['quantity']}")
            if len(transactions_without_payment) > 10:
                print(f"   ... и ещё {len(transactions_without_payment) - 10} транзакций")
            print("\n💡 Для импорта от брокера payment должен быть передан для всех транзакций")
        
        if transactions_with_zero_payment:
            print(f"\n❌ НАЙДЕНО {len(transactions_with_zero_payment)} ТРАНЗАКЦИЙ С PAYMENT = 0:")
            for tx in transactions_with_zero_payment[:10]:  # Показываем первые 10
                print(f"   - {tx['date']} | {tx['type']:10} | {tx['ticker']:10} | "
                      f"price: {tx['price']}, quantity: {tx['quantity']}, "
                      f"payment: {tx['payment']}, ожидалось: {tx['expected_payment']:.2f}")
            if len(transactions_with_zero_payment) > 10:
                print(f"   ... и ещё {len(transactions_with_zero_payment) - 10} транзакций")
            print("\n💡 Для облигаций с НКД payment может отличаться от price * quantity,")
            print("   но payment не должен быть равен 0, если price и quantity не равны 0")
        
        if not transactions_without_payment and not transactions_with_zero_payment:
            print("\n✅ Все транзакции Buy/Sell/Redemption имеют корректный payment")
        
        print("="*80 + "\n")
        
        # Проверка баланса портфеля из данных брокера
        print("\n" + "="*80)
        print("ПРОВЕРКА БАЛАНСА ПОРТФЕЛЯ (РОССИЙСКИЙ РУБЛЬ)")
        print("="*80)
        
        for account_name, account_data in result.items():
            positions = account_data.get("positions", [])
            transactions = account_data.get("transactions", [])
            
            print(f"\n📁 Счёт: {account_name}")
            
            # Рассчитываем баланс из операций (сумма всех операций в рублях)
            # Используем точное значение payment от брокера без изменения знаков
            balance_from_operations = 0.0
            
            for tx in transactions:
                payment = tx.get("payment", 0)
                currency = tx.get("currency", "rub")
                
                # Учитываем только операции в рублях
                if currency and currency.lower() not in ("rub", "rur", "руб"):
                    continue
                
                # Используем точное значение payment от брокера (со знаком)
                balance_from_operations += float(payment)
            
            print(f"💰 Баланс из операций (сумма всех операций в RUB): {balance_from_operations:,.2f} RUB")
            
            # Получаем баланс из позиций (ищем позицию с валютой RUB)
            balance_from_positions = 0.0
            rub_position = None
            
            for pos in positions:
                # Ищем позицию с тикером валюты RUB (может быть "RUB000UTSTOM" или содержать "RUB")
                ticker = (pos.get("ticker") or "").upper()
                name = (pos.get("name") or "").lower()
                # Проверяем по тикеру (начинается с RUB) или по названию (содержит "рубль")
                if (ticker.startswith("RUB") or ticker.startswith("RUR")) or "рубль" in name:
                    rub_position = pos
                    balance_from_positions = float(pos.get("quantity", 0))
                    break
            
            if rub_position:
                print(f"💰 Баланс из позиций (количество RUB в портфеле): {balance_from_positions:,.2f} RUB")
            else:
                print("⚠️  Позиция RUB не найдена в портфеле")
            
            # Сравниваем балансы
            print("\n" + "-"*80)
            if rub_position:
                difference = abs(balance_from_operations - balance_from_positions)
                if difference < 0.01:  # Допускаем погрешность в 1 копейку
                    print(f"✅ Балансы совпадают!")
                else:
                    print(f"❌ РАСХОЖДЕНИЕ БАЛАНСОВ!")
                    print(f"   Разница: {difference:,.2f} RUB")
                    print(f"   Баланс из операций: {balance_from_operations:,.2f} RUB")
                    print(f"   Баланс из позиций: {balance_from_positions:,.2f} RUB")
            else:
                print(f"⚠️  Не удалось сравнить балансы: позиция RUB не найдена")
                print(f"   Баланс из операций: {balance_from_operations:,.2f} RUB")
            print("-"*80)
        
        # Сравнение с данными из базы данных
        print("\n" + "="*80)
        print("СРАВНЕНИЕ С ДАННЫМИ ИЗ БАЗЫ ДАННЫХ")
        print("="*80)
        
        try:
            await compare_with_database(token, result)
        except Exception as e:
            print(f"\n⚠️  ОШИБКА при сравнении с БД: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"\n❌ ОШИБКА при получении данных: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def compare_with_database(broker_token: str, broker_data: dict):
    """Сравнивает данные от брокера с данными из базы данных."""
    # Маппинг типов операций: английские названия от брокера -> русские названия в БД
    operation_type_mapping = {
        "Deposit": "Депозит",
        "Withdraw": "Вывод",
        "Dividend": "Дивиденды",
        "Coupon": "Купоны",
        "Commission": "Комиссия",
        "Commision": "Комиссия",  # опечатка в некоторых данных
        "Tax": "Налог",
        "Buy": "Покупка",
        "Sell": "Продажа",
        "Redemption": "Погашение",
        "ammortization": "Погашение",
        "Ammortization": "Погашение",
    }
    
    # Находим портфель по токену брокера
    connections = await table_select_async(
        "user_broker_connections",
        select="portfolio_id, user_id, broker_id",
        filters={"api_key": broker_token},
        limit=1
    )
    
    if not connections:
        print("\n⚠️  Портфель с таким токеном не найден в базе данных")
        print("   Импортируйте портфель через веб-интерфейс для сравнения")
        return
    
    connection = connections[0]
    parent_portfolio_id = connection["portfolio_id"]
    user_id = connection["user_id"]
    broker_id = connection["broker_id"]
    
    print(f"\n📊 Найден родительский портфель в БД: ID={parent_portfolio_id}, user_id={user_id}, broker_id={broker_id}")
    
    # Получаем название родительского портфеля
    parent_portfolios = await table_select_async(
        "portfolios",
        select="name",
        filters={"id": parent_portfolio_id},
        limit=1
    )
    parent_portfolio_name = parent_portfolios[0]["name"] if parent_portfolios else f"Портфель {parent_portfolio_id}"
    
    print(f"   Название: {parent_portfolio_name}")
    
    # Получаем все дочерние портфели
    child_portfolios = await table_select_async(
        "portfolios",
        select="id, name, parent_portfolio_id",
        filters={"parent_portfolio_id": parent_portfolio_id, "user_id": user_id}
    )
    
    if not child_portfolios:
        print("\n⚠️  Дочерние портфели не найдены")
        print("   Сравнение будет выполнено только для родительского портфеля")
        child_portfolios = [{"id": parent_portfolio_id, "name": parent_portfolio_name, "parent_portfolio_id": None}]
    else:
        print(f"\n📁 Найдено дочерних портфелей: {len(child_portfolios)}")
        for child in child_portfolios:
            print(f"   - ID={child['id']}, Название: {child['name']}")
    
    # Собираем все ID портфелей для получения операций и балансов
    all_portfolio_ids = [p["id"] for p in child_portfolios]
    
    # Получаем операции из БД для всех дочерних портфелей
    all_operations_db = []
    for portfolio_id in all_portfolio_ids:
        operations_db = await rpc_async("get_cash_operations", {
            "p_user_id": user_id,
            "p_portfolio_id": portfolio_id,
            "p_start_date": None,
            "p_end_date": None,
            "p_limit": 10000
        })
        
        # Обрабатываем случай, когда результат может быть None или пустым
        if operations_db is None:
            operations_db = []
        elif not isinstance(operations_db, list):
            operations_db = []
        
        all_operations_db.extend(operations_db)
    
    print(f"\n📋 Операции из БД (все дочерние портфели): {len(all_operations_db)} операций")
    
    # Получаем балансы из БД для всех дочерних портфелей
    all_balances_db = {}
    total_balance_from_db = 0.0
    
    for portfolio_id in all_portfolio_ids:
        portfolio_values = await table_select_async(
            "portfolio_daily_values",
            select="balance",
            filters={"portfolio_id": portfolio_id},
            order={"column": "report_date", "desc": True},
            limit=1
        )
        
        balance = 0.0
        if portfolio_values:
            balance = float(portfolio_values[0].get("balance") or 0)
        
        all_balances_db[portfolio_id] = balance
        total_balance_from_db += balance
    
    print(f"💰 Общий баланс из БД (все дочерние портфели): {total_balance_from_db:,.2f} RUB")
    for portfolio_id, balance in all_balances_db.items():
        portfolio_name = next((p["name"] for p in child_portfolios if p["id"] == portfolio_id), f"Портфель {portfolio_id}")
        print(f"   - {portfolio_name}: {balance:,.2f} RUB")
    
    # Сравниваем операции для каждого счета от брокера
    # Если у брокера несколько счетов, они могут соответствовать разным дочерним портфелям
    # Пока сравниваем все операции от брокера со всеми операциями из БД
    total_broker_transactions = []
    for account_name, account_data in broker_data.items():
        broker_transactions = account_data.get("transactions", [])
        total_broker_transactions.extend(broker_transactions)
    
    print(f"\n📁 Сравнение операций")
    print(f"   Операций от брокера (все счета): {len(total_broker_transactions)}")
    print(f"   Операций в БД (все дочерние портфели): {len(all_operations_db)}")
    
    # Группируем операции от брокера по ключу (дата, тип, сумма)
    broker_ops_map = {}
    for tx in total_broker_transactions:
        payment = tx.get("payment", 0)
        currency = tx.get("currency", "rub")
        
        # Учитываем только операции в рублях
        if currency and currency.lower() not in ("rub", "rur", "руб"):
            continue
        
        tx_type = tx.get("type", "N/A")
        # Преобразуем тип операции от брокера в формат БД
        tx_type_db = operation_type_mapping.get(tx_type, tx_type)
        tx_date = tx.get("date", "")
        
        # Нормализуем дату (убираем микросекунды и timezone для сравнения)
        if tx_date:
            try:
                dt = datetime.fromisoformat(tx_date.replace('Z', '+00:00'))
                # Убираем микросекунды и timezone, оставляем только дату и время
                dt_normalized = dt.replace(microsecond=0)
                # Форматируем как YYYY-MM-DD HH:MM:SS для единообразия
                tx_date_normalized = dt_normalized.strftime("%Y-%m-%d %H:%M:%S")
            except:
                # Если не удалось распарсить, обрезаем до секунд
                tx_date_normalized = tx_date[:19] if len(tx_date) > 19 else tx_date
        else:
            tx_date_normalized = ""
        
        # Нормализуем сумму: округляем до 2 знаков после запятой
        # Используем abs() для сравнения, так как знак может отличаться
        payment_normalized = round(abs(float(payment)), 2)
            
        # Ключ для сравнения: (дата, тип, абсолютная сумма)
        key = (tx_date_normalized, tx_type_db, payment_normalized)
        broker_ops_map[key] = broker_ops_map.get(key, 0) + 1
    
    # Группируем операции из БД по ключу (дата, тип, сумма)
    db_ops_map = {}
    for op in all_operations_db:
        op_type = op.get("operation_type", "N/A")
        op_date = op.get("operation_date")
        # Используем amount_rub, если есть, иначе amount
        amount_rub = float(op.get("amount_rub") or op.get("amount") or 0)
        
        # Нормализуем дату
        if op_date:
            if isinstance(op_date, str):
                try:
                    dt = datetime.fromisoformat(op_date.replace('Z', '+00:00'))
                    dt_normalized = dt.replace(microsecond=0)
                    op_date_normalized = dt_normalized.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    op_date_normalized = op_date[:19] if len(op_date) > 19 else op_date
            elif isinstance(op_date, datetime):
                dt_normalized = op_date.replace(microsecond=0)
                op_date_normalized = dt_normalized.strftime("%Y-%m-%d %H:%M:%S")
            else:
                op_date_normalized = str(op_date)
        else:
            op_date_normalized = ""
        
        # Нормализуем сумму: округляем до 2 знаков после запятой
        # Используем abs() для сравнения, так как знак может отличаться
        amount_normalized = round(abs(amount_rub), 2)
        
        # Ключ для сравнения: (дата, тип, абсолютная сумма)
        key = (op_date_normalized, op_type, amount_normalized)
        db_ops_map[key] = db_ops_map.get(key, 0) + 1
    
    # Находим различия
    only_in_broker = set(broker_ops_map.keys()) - set(db_ops_map.keys())
    only_in_db = set(db_ops_map.keys()) - set(broker_ops_map.keys())
    in_both = set(broker_ops_map.keys()) & set(db_ops_map.keys())
    
    # Проверяем количество операций (могут быть дубликаты)
    differences = []
    for key in in_both:
        broker_count = broker_ops_map[key]
        db_count = db_ops_map[key]
        if broker_count != db_count:
            differences.append((key, broker_count, db_count))
    
    # Подсчитываем операции по типам для анализа
    broker_by_type = {}
    db_by_type = {}
    
    for key, count in broker_ops_map.items():
        _, op_type, _ = key
        broker_by_type[op_type] = broker_by_type.get(op_type, 0) + count
    
    for key, count in db_ops_map.items():
        _, op_type, _ = key
        db_by_type[op_type] = db_by_type.get(op_type, 0) + count
    
    # Выводим операции, которых не хватает в БД
    print(f"\n{'='*80}")
    print(f"ОПЕРАЦИИ, КОТОРЫХ НЕ ХВАТАЕТ В БД")
    print(f"{'='*80}")
    
    if only_in_broker or differences:
        # Собираем все операции, которых не хватает в БД
        missing_operations = []
        
        # Операции, которых вообще нет в БД
        for key in only_in_broker:
            date, op_type, amount = key
            count = broker_ops_map[key]
            # Находим исходные транзакции от брокера для деталей
            for tx in total_broker_transactions:
                tx_payment = tx.get("payment", 0)
                tx_currency = tx.get("currency", "rub")
                if tx_currency and tx_currency.lower() not in ("rub", "rur", "руб"):
                    continue
                tx_type = tx.get("type", "N/A")
                tx_type_db = operation_type_mapping.get(tx_type, tx_type)
                tx_date = tx.get("date", "")
                
                # Нормализуем для сравнения
                if tx_date:
                    try:
                        dt = datetime.fromisoformat(tx_date.replace('Z', '+00:00'))
                        dt_normalized = dt.replace(microsecond=0)
                        tx_date_normalized = dt_normalized.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        tx_date_normalized = tx_date[:19] if len(tx_date) > 19 else tx_date
                else:
                    tx_date_normalized = ""
                
                payment_normalized = round(abs(float(tx_payment)), 2)
                tx_key = (tx_date_normalized, tx_type_db, payment_normalized)
                
                if tx_key == key:
                    missing_operations.append({
                        'date': tx_date,
                        'type': tx_type_db,
                        'amount': tx_payment,
                        'ticker': tx.get("ticker", ""),
                        'quantity': tx.get("quantity"),
                        'count': count
                    })
                    break
        
        # Операции с разным количеством (не хватает в БД)
        for key, broker_count, db_count in differences:
            if broker_count > db_count:
                date, op_type, amount = key
                missing_count = broker_count - db_count
                # Находим исходные транзакции от брокера
                for tx in total_broker_transactions:
                    tx_payment = tx.get("payment", 0)
                    tx_currency = tx.get("currency", "rub")
                    if tx_currency and tx_currency.lower() not in ("rub", "rur", "руб"):
                        continue
                    tx_type = tx.get("type", "N/A")
                    tx_type_db = operation_type_mapping.get(tx_type, tx_type)
                    tx_date = tx.get("date", "")
                    
                    if tx_date:
                        try:
                            dt = datetime.fromisoformat(tx_date.replace('Z', '+00:00'))
                            dt_normalized = dt.replace(microsecond=0)
                            tx_date_normalized = dt_normalized.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            tx_date_normalized = tx_date[:19] if len(tx_date) > 19 else tx_date
                    else:
                        tx_date_normalized = ""
                    
                    payment_normalized = round(abs(float(tx_payment)), 2)
                    tx_key = (tx_date_normalized, tx_type_db, payment_normalized)
                    
                    if tx_key == key:
                        missing_operations.append({
                            'date': tx_date,
                            'type': tx_type_db,
                            'amount': tx_payment,
                            'ticker': tx.get("ticker", ""),
                            'quantity': tx.get("quantity"),
                            'count': missing_count
                        })
                        break
        
        if missing_operations:
            print(f"\n   ❌ Найдено {len(missing_operations)} операций, которых не хватает в БД:")
            print(f"     {'Дата':<20} | {'Тип':<15} | {'Тикер':<15} | {'Количество':>12} | {'Сумма':>15}")
            print(f"     {'-'*20} | {'-'*15} | {'-'*15} | {'-'*12} | {'-'*15}")
            # Сортируем по дате
            missing_operations.sort(key=lambda x: x['date'])
            for op in missing_operations:
                date_str = op['date'][:19] if op['date'] else "N/A"
                ticker = (op['ticker'] or "")[:15]
                quantity = op['quantity']
                qty_str = f"{quantity:>10.2f} шт." if quantity is not None else f"{'':>12}"
                amount_str = f"{op['amount']:>15,.2f}"
                print(f"     {date_str:<20} | {op['type']:<15} | {ticker:<15} | {qty_str:>12} | {amount_str:>15}")
        else:
            print("\n   ✅ Все операции от брокера присутствуют в БД")
    else:
        print("\n   ✅ Все операции учтены корректно!")
    
    # Общая статистика
    total_broker_ops = sum(broker_ops_map.values())
    total_db_ops = sum(db_ops_map.values())
    print(f"\n   📊 Общая статистика:")
    print(f"     Всего операций от брокера: {total_broker_ops}")
    print(f"     Всего операций в БД: {total_db_ops}")
    print(f"     Разница: {total_broker_ops - total_db_ops:+d}")
    
    if not only_in_broker and not only_in_db and not differences:
        print("\n   ✅ Все операции совпадают!")
    else:
        print(f"\n   ❌ Найдены неодинаковые операции:")
        print(f"     - Операции только от брокера: {len(only_in_broker)}")
        print(f"     - Операции только в БД: {len(only_in_db)}")
        print(f"     - Операции с разным количеством: {len(differences)}")
    
    # Сравниваем балансы (суммируем по всем счетам от брокера и всем дочерним портфелям)
    if broker_data:
        # Рассчитываем баланс от брокера (суммируем по всем счетам)
        balance_from_broker_ops = 0.0
        balance_from_broker_positions = 0.0
        
        for account_name, account_data in broker_data.items():
            positions = account_data.get("positions", [])
            transactions = account_data.get("transactions", [])
            
            # Рассчитываем баланс из операций для этого счёта
            for tx in transactions:
                payment = tx.get("payment", 0)
                currency = tx.get("currency", "rub")
                if currency and currency.lower() not in ("rub", "rur", "руб"):
                    continue
                balance_from_broker_ops += float(payment)
            
            # Получаем баланс из позиций для этого счёта
            for pos in positions:
                ticker = (pos.get("ticker") or "").upper()
                name = (pos.get("name") or "").lower()
                if (ticker.startswith("RUB") or ticker.startswith("RUR")) or "рубль" in name:
                    balance_from_broker_positions += float(pos.get("quantity", 0))
                    break
        
        print("\n" + "-"*80)
        print("СРАВНЕНИЕ БАЛАНСОВ")
        print("-"*80)
        print(f"💰 Баланс от брокера (из операций, все счета): {balance_from_broker_ops:,.2f} RUB")
        if balance_from_broker_positions > 0:
            print(f"💰 Баланс от брокера (из позиций, все счета): {balance_from_broker_positions:,.2f} RUB")
        print(f"💰 Баланс из БД (portfolio_daily_values, все дочерние портфели): {total_balance_from_db:,.2f} RUB")
        
        if total_balance_from_db > 0 or balance_from_broker_ops != 0 or balance_from_broker_positions != 0:
            diff_ops = abs(balance_from_broker_ops - total_balance_from_db)
            diff_pos = abs(balance_from_broker_positions - total_balance_from_db) if balance_from_broker_positions > 0 else None
            
            print("\n   Разница балансов:")
            print(f"   Брокер (операции) vs БД: {diff_ops:,.2f} RUB")
            if diff_ops < 0.01:
                print("   ✅ Балансы совпадают!")
            else:
                print("   ❌ РАСХОЖДЕНИЕ БАЛАНСОВ!")
            
            if diff_pos is not None:
                print(f"   Брокер (позиции) vs БД: {diff_pos:,.2f} RUB")
                if diff_pos < 0.01:
                    print("   ✅ Балансы совпадают!")
                else:
                    print("   ❌ РАСХОЖДЕНИЕ БАЛАНСОВ!")
        print("-"*80)


if __name__ == "__main__":
    from app.utils.async_runner import run_async
    run_async(main())
