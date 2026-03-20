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
from typing import Optional, Dict, List

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.external.brokers.tinkoff import get_tinkoff_portfolio
from app.infrastructure.external.brokers.tinkoff.import_service import OPERATION_CLASSIFICATION
from app.infrastructure.database.postgres_async import table_select_async, rpc_async, close_connection_pool, get_connection_pool
from app.utils.async_runner import run_async


async def get_portfolio_info(broker_token: str):
    """Получает информацию о портфелях из БД по токену брокера."""
    connections = await table_select_async(
        "user_broker_connections",
        select="portfolio_id, broker_id",
        filters={"api_key": broker_token},
        limit=1
    )
    
    if not connections:
        return None
    
    connection = connections[0]
    parent_portfolio_id = connection["portfolio_id"]

    owner_rows = await table_select_async(
        "portfolios",
        select="user_id",
        filters={"id": parent_portfolio_id},
        limit=1
    )
    if not owner_rows:
        return None
    user_id = owner_rows[0]["user_id"]
    
    # Получаем название родительского портфеля
    parent_portfolios = await table_select_async(
        "portfolios",
        select="id, name",
        filters={"id": parent_portfolio_id},
        limit=1
    )
    parent_portfolio_name = parent_portfolios[0]["name"] if parent_portfolios else f"Портфель {parent_portfolio_id}"
    
    # Получаем все дочерние портфели
    child_portfolios = await table_select_async(
        "portfolios",
        select="id, name, parent_portfolio_id",
        filters={"parent_portfolio_id": parent_portfolio_id, "user_id": user_id}
    )
    
    if not child_portfolios:
        child_portfolios = [{"id": parent_portfolio_id, "name": parent_portfolio_name, "parent_portfolio_id": None}]
    
    return {
        "user_id": user_id,
        "parent_portfolio_id": parent_portfolio_id,
        "parent_portfolio_name": parent_portfolio_name,
        "child_portfolios": child_portfolios
    }


async def show_balance_analysis(broker_data: dict, portfolio_info: Optional[dict] = None, selected_portfolio_id: Optional[int] = None, selected_portfolio_name: Optional[str] = None):
    """Показывает анализ балансов."""
    print("\n" + "="*80)
    print("АНАЛИЗ БАЛАНСОВ")
    print("="*80)
    
    # Фильтруем данные по выбранному портфелю
    filtered_broker_data = broker_data
    if selected_portfolio_id and selected_portfolio_name:
        # Ищем счет брокера с таким же названием
        filtered_broker_data = {}
        for account_name, account_data in broker_data.items():
            # Сравниваем названия (без учета регистра и пробелов)
            account_normalized = account_name.lower().strip()
            portfolio_normalized = selected_portfolio_name.lower().strip()
            if account_normalized == portfolio_normalized or account_normalized in portfolio_normalized or portfolio_normalized in account_normalized:
                filtered_broker_data[account_name] = account_data
                break
        if not filtered_broker_data:
            print(f"\n⚠️  Не найден счет брокера для портфеля '{selected_portfolio_name}'")
            print("   Показываем все счета")
            filtered_broker_data = broker_data
    
    for account_name, account_data in filtered_broker_data.items():
        positions = account_data.get("positions", [])
        transactions = account_data.get("transactions", [])
        
        print(f"\n📁 Счёт: {account_name}")
        
        # Баланс из операций
        balance_from_operations = 0.0
        for tx in transactions:
            payment = tx.get("payment", 0)
            currency = tx.get("currency", "rub")
            if currency and currency.lower() not in ("rub", "rur", "руб"):
                continue
            balance_from_operations += float(payment)
        
        print(f"💰 Баланс из операций: {balance_from_operations:,.2f} RUB")
        
        # Баланс из позиций
        balance_from_positions = 0.0
        for pos in positions:
            ticker = (pos.get("ticker") or "").upper()
            name = (pos.get("name") or "").lower()
            if (ticker.startswith("RUB") or ticker.startswith("RUR")) or "рубль" in name:
                balance_from_positions = float(pos.get("quantity", 0))
                break
        
        if balance_from_positions > 0:
            print(f"💰 Баланс из позиций: {balance_from_positions:,.2f} RUB")
            diff = abs(balance_from_operations - balance_from_positions)
            if diff < 0.01:
                print("   ✅ Балансы совпадают")
            else:
                print(f"   ❌ Расхождение: {diff:,.2f} RUB")
        else:
            print("   ⚠️  Позиция RUB не найдена")
        
        # Сравнение с БД
        if portfolio_info:
            portfolio_ids = [selected_portfolio_id] if selected_portfolio_id else [p["id"] for p in portfolio_info["child_portfolios"]]
            total_balance_db = 0.0
            
            for portfolio_id in portfolio_ids:
                portfolio_values = await table_select_async(
                    "portfolio_daily_values",
                    select="balance",
                    filters={"portfolio_id": portfolio_id},
                    order={"column": "report_date", "desc": True},
                    limit=1
                )
                if portfolio_values:
                    total_balance_db += float(portfolio_values[0].get("balance") or 0)
            
            if total_balance_db > 0:
                print(f"\n💰 Баланс из БД: {total_balance_db:,.2f} RUB")
                diff = abs(balance_from_operations - total_balance_db)
                if diff < 0.01:
                    print("   ✅ Балансы совпадают с БД")
                else:
                    print(f"   ❌ Расхождение с БД: {diff:,.2f} RUB")


async def show_positions_comparison(broker_data: dict, portfolio_info: Optional[dict] = None, portfolio_id: Optional[int] = None, portfolio_name: Optional[str] = None):
    """Показывает сравнение позиций от брокера и из БД."""
    print("\n" + "="*80)
    print("СРАВНЕНИЕ ПОЗИЦИЙ")
    if portfolio_name:
        print(f"Портфель: {portfolio_name}")
    print("="*80)
    
    # Фильтруем данные по выбранному портфелю
    filtered_broker_data = broker_data
    if portfolio_id and portfolio_name:
        # Ищем счет брокера с таким же названием
        filtered_broker_data = {}
        for account_name, account_data in broker_data.items():
            # Сравниваем названия (без учета регистра и пробелов)
            account_normalized = account_name.lower().strip()
            portfolio_normalized = portfolio_name.lower().strip()
            if account_normalized == portfolio_normalized or account_normalized in portfolio_normalized or portfolio_normalized in account_normalized:
                filtered_broker_data[account_name] = account_data
                break
        if not filtered_broker_data:
            print(f"\n⚠️  Не найден счет брокера для портфеля '{portfolio_name}'")
            print("   Показываем все счета")
            filtered_broker_data = broker_data
    
    # Собираем позиции от брокера (исключаем валюты)
    broker_positions = {}
    for account_name, account_data in filtered_broker_data.items():
        for pos in account_data.get("positions", []):
            ticker = (pos.get("ticker") or "").upper()
            name = (pos.get("name") or "").lower()
            # Пропускаем валюты
            if (ticker.startswith("RUB") or ticker.startswith("RUR")) or "рубль" in name:
                continue
            
            if ticker not in broker_positions:
                broker_positions[ticker] = {
                    "name": pos.get("name", "N/A"),
                    "quantity": float(pos.get("quantity", 0)),
                    "current_price": float(pos.get("current_price", 0)),
                    "value": float(pos.get("quantity", 0)) * float(pos.get("current_price", 0))
                }
            else:
                broker_positions[ticker]["quantity"] += float(pos.get("quantity", 0))
                broker_positions[ticker]["value"] += float(pos.get("quantity", 0)) * float(pos.get("current_price", 0))
    
    print(f"\n📊 Позиций от брокера: {len(broker_positions)}")
    
    # Получаем позиции из БД
    db_positions = {}
    if portfolio_info:
        portfolio_ids = [portfolio_id] if portfolio_id else [p["id"] for p in portfolio_info["child_portfolios"]]
        
        pool = await get_connection_pool()
        async with pool.acquire() as conn:
            for pid in portfolio_ids:
                query = """
                    SELECT pa.quantity, pa.average_price, a.ticker, a.name
                    FROM portfolio_assets pa
                    JOIN assets a ON pa.asset_id = a.id
                    WHERE pa.portfolio_id = $1
                """
                rows = await conn.fetch(query, pid)
                
                for row in rows:
                    pos = dict(row)
                    ticker = (pos.get("ticker") or "").upper()
                    if not ticker:
                        continue
                    
                    if ticker not in db_positions:
                        db_positions[ticker] = {
                            "name": pos.get("name", "N/A"),
                            "quantity": float(pos.get("quantity", 0)),
                            "average_price": float(pos.get("average_price", 0) or 0)
                        }
                    else:
                        db_positions[ticker]["quantity"] += float(pos.get("quantity", 0))
    
    if db_positions:
        print(f"📊 Позиций в БД: {len(db_positions)}")
        
        # Сравнение
        print(f"\n{'Тикер':<15} | {'Название':<35} | {'Брокер':>12} | {'БД':>12} | {'Разница':>12}")
        print("-" * 95)
        
        all_tickers = set(broker_positions.keys()) | set(db_positions.keys())
        differences = []
        
        for ticker in sorted(all_tickers):
            broker_qty = broker_positions.get(ticker, {}).get("quantity", 0)
            db_qty = db_positions.get(ticker, {}).get("quantity", 0)
            diff = broker_qty - db_qty
            
            if abs(diff) > 0.01:
                differences.append(ticker)
            
            name = (broker_positions.get(ticker, {}).get("name") or db_positions.get(ticker, {}).get("name") or "N/A")[:35]
            status = "✅" if abs(diff) < 0.01 else "❌"
            print(f"{ticker:<15} | {name:<35} | {broker_qty:>12.2f} | {db_qty:>12.2f} | {diff:>+12.2f} {status}")
        
        if not differences:
            print("\n✅ Все позиции совпадают!")
        else:
            print(f"\n❌ Найдено расхождений: {len(differences)}")
    else:
        print("\n⚠️  Портфель не найден в БД для сравнения")
        print("\nПозиции от брокера:")
        print(f"{'Тикер':<15} | {'Название':<35} | {'Количество':>12} | {'Цена':>12} | {'Стоимость':>15}")
        print("-" * 95)
        for ticker, pos in sorted(broker_positions.items()):
            print(f"{ticker:<15} | {pos['name'][:35]:<35} | {pos['quantity']:>12.2f} | {pos['current_price']:>12.2f} | {pos['value']:>15,.2f}")


async def show_operations(broker_data: dict, portfolio_info: Optional[dict] = None, portfolio_id: Optional[int] = None, portfolio_name: Optional[str] = None, limit: int = 10):
    """Показывает операции от брокера в исходном виде."""
    print("\n" + "="*80)
    print("ОПЕРАЦИИ ОТ БРОКЕРА")
    if portfolio_name:
        print(f"Портфель: {portfolio_name}")
    print("="*80)
    
    # Фильтруем данные по выбранному портфелю
    filtered_broker_data = broker_data
    if portfolio_id and portfolio_name:
        # Ищем счет брокера с таким же названием
        filtered_broker_data = {}
        for account_name, account_data in broker_data.items():
            # Сравниваем названия (без учета регистра и пробелов)
            account_normalized = account_name.lower().strip()
            portfolio_normalized = portfolio_name.lower().strip()
            if account_normalized == portfolio_normalized or account_normalized in portfolio_normalized or portfolio_normalized in account_normalized:
                filtered_broker_data[account_name] = account_data
                break
        if not filtered_broker_data:
            print(f"\n⚠️  Не найден счет брокера для портфеля '{portfolio_name}'")
            print("   Показываем все операции")
            filtered_broker_data = broker_data
    
    # Собираем операции от брокера только из отфильтрованных счетов
    all_transactions = []
    for account_name, account_data in filtered_broker_data.items():
        for tx in account_data.get("transactions", []):
            tx_with_account = tx.copy()
            tx_with_account["account_name"] = account_name
            all_transactions.append(tx_with_account)
    
    # Сортируем по дате (от новых к старым)
    all_transactions.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    # Ограничиваем количество только если не выбран конкретный портфель
    transactions_to_show = all_transactions if (portfolio_id and limit is None) else (all_transactions[:limit] if limit else all_transactions)
    
    print(f"\n📋 Показано операций: {len(transactions_to_show)} из {len(all_transactions)}")
    print(f"\n{'Дата':<20} | {'Счёт':<20} | {'Тип':<15} | {'Тикер':<15} | {'Цена':>12} | {'Количество':>12} | {'Сумма':>15}")
    print("-" * 125)
    
    for tx in transactions_to_show:
        date_str = tx.get("date", "N/A")[:19] if tx.get("date") else "N/A"
        account = (tx.get("account_name", "N/A") or "N/A")[:20]
        tx_type = tx.get("type", "N/A")[:15]
        ticker = (tx.get("ticker") or "—")[:15]
        price = tx.get("price")
        price_str = f"{price:>12,.2f}" if price is not None else f"{'—':>12}"
        quantity = tx.get("quantity")
        qty_str = f"{quantity:>10.2f} шт." if quantity is not None else f"{'':>12}"
        payment = tx.get("payment", 0)
        payment_str = f"{payment:>15,.2f}"
        
        print(f"{date_str:<20} | {account:<20} | {tx_type:<15} | {ticker:<15} | {price_str:>12} | {qty_str:>12} | {payment_str:>15}")
        


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
    
    try:
        # Получаем данные портфеля
        print("\n📥 Получаем данные от брокера Tinkoff...")
        broker_data = get_tinkoff_portfolio(token)
        
        if not broker_data:
            print("⚠️  Портфель пуст (нет доступных счетов)")
            return
        
        print(f"✅ Получено данных для {len(broker_data)} счетов")
        
        # Получаем информацию о портфелях из БД
        portfolio_info = await get_portfolio_info(token)
        
        # Интерактивное меню
        print("\n" + "="*80)
        print("ВЫБОР ТИПА АНАЛИЗА")
        print("="*80)
        print("1. Баланс")
        print("2. Позиции")
        print("3. Операции")
        print("4. Всё (краткая статистика)")
        print("0. Выход")
        
        choice = input("\nВыберите тип анализа (Enter для всего): ").strip()
        
        if choice == "0":
            return
        
        # Выбор портфеля (если есть)
        selected_portfolio_id = None
        selected_portfolio_name = None
        if portfolio_info and choice in ("1", "2", "3", ""):
            print("\n" + "-"*80)
            print("ВЫБОР ПОРТФЕЛЯ")
            print("-"*80)
            print("0. Все портфели")
            for i, p in enumerate(portfolio_info["child_portfolios"], 1):
                print(f"{i}. {p['name']} (ID: {p['id']})")
            
            portfolio_choice = input("\nВыберите портфель (Enter для всех): ").strip()
            if portfolio_choice and portfolio_choice != "0":
                try:
                    idx = int(portfolio_choice) - 1
                    if 0 <= idx < len(portfolio_info["child_portfolios"]):
                        selected_portfolio_id = portfolio_info["child_portfolios"][idx]["id"]
                        selected_portfolio_name = portfolio_info["child_portfolios"][idx]["name"]
                        print(f"✅ Выбран портфель: {selected_portfolio_name}")
                except ValueError:
                    pass
        
        # Выполняем анализ
        if choice == "1" or choice == "":
            await show_balance_analysis(broker_data, portfolio_info, selected_portfolio_id, selected_portfolio_name)
        
        if choice == "2" or choice == "":
            await show_positions_comparison(broker_data, portfolio_info, selected_portfolio_id, selected_portfolio_name)
        
        if choice == "3" or choice == "":
            limit = None if selected_portfolio_id else 10
            await show_operations(broker_data, portfolio_info, selected_portfolio_id, selected_portfolio_name, limit)
        
        if choice == "4" or choice == "":
            # Краткая статистика
            print("\n" + "="*80)
            print("КРАТКАЯ СТАТИСТИКА")
            print("="*80)
            
            total_positions = sum(len(acc.get("positions", [])) for acc in broker_data.values())
            total_transactions = sum(len(acc.get("transactions", [])) for acc in broker_data.values())
            
            print(f"\n📊 Всего счетов: {len(broker_data)}")
            print(f"📊 Всего позиций: {total_positions}")
            print(f"📊 Всего операций: {total_transactions}")
            
            if portfolio_info:
                print(f"\n📁 Портфелей в БД: {len(portfolio_info['child_portfolios'])}")
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await close_connection_pool()


if __name__ == "__main__":
    from app.utils.async_runner import run_async
    run_async(main())
