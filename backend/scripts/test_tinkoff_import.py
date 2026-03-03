"""
Скрипт для ручного тестирования импорта портфелей от Tinkoff.

Использование:
    python scripts/test_tinkoff_import.py

Требуется переменная окружения TINKOFF_TOKEN с токеном доступа к Tinkoff Invest API.
"""
import os
import sys
from pathlib import Path
from collections import Counter

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.external.brokers.tinkoff import get_tinkoff_portfolio
from app.infrastructure.external.brokers.tinkoff.import_service import OPERATION_CLASSIFICATION


def main():
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
                print("\n   Позиции (первые 5):")
                for pos in positions[:5]:
                    ticker = pos.get("ticker") or "N/A"
                    name = pos.get("name") or "N/A"
                    quantity = pos.get("quantity", 0)
                    current_price = pos.get("current_price", 0)
                    value = quantity * current_price
                    print(f"     - {ticker:10} | {name[:30]:30} | {quantity:>10.2f} шт. × {current_price:>10.2f} = {value:>12.2f}")
                if len(positions) > 5:
                    print(f"     ... и ещё {len(positions) - 5} позиций")
            
            if transactions:
                print("\n   Последние транзакции (первые 5):")
                for tx in transactions[:5]:
                    tx_type = tx.get("type", "N/A")
                    date = tx.get("date", "N/A")
                    ticker = tx.get("ticker") or "N/A"
                    payment = tx.get("payment", 0)
                    quantity = tx.get("quantity")
                    if quantity:
                        print(f"     - {date} | {tx_type:15} | {ticker:10} | {quantity:>10.2f} шт.")
                    else:
                        print(f"     - {date} | {tx_type:15} | {ticker:10} | {payment:>12.2f}")
                if len(transactions) > 5:
                    print(f"     ... и ещё {len(transactions) - 5} транзакций")
        
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
        
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА при получении данных: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
