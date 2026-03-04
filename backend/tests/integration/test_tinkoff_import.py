"""
Интеграционные тесты для импорта портфелей от брокера Tinkoff.

Тестирует:
- Получение данных от Tinkoff API
- Обработку позиций и операций
- Выявление неизвестных типов операций
"""
import os
import pytest
from collections import Counter
from app.infrastructure.external.brokers.tinkoff import get_tinkoff_portfolio
from app.infrastructure.external.brokers.tinkoff.import_service import OPERATION_CLASSIFICATION


# Токен для тестирования можно задать через переменную окружения TINKOFF_TOKEN
# или передать через pytest.mark.parametrize
TINKOFF_TOKEN = os.getenv("TINKOFF_TOKEN")


@pytest.mark.skipif(
    not TINKOFF_TOKEN,
    reason="TINKOFF_TOKEN не установлен. Установите переменную окружения TINKOFF_TOKEN для запуска тестов."
)
class TestTinkoffImport:
    """Тесты для импорта портфелей от Tinkoff."""
    
    def test_get_portfolio_data(self):
        """Тест получения данных портфеля от Tinkoff API."""
        result = get_tinkoff_portfolio(TINKOFF_TOKEN)
        
        # Проверяем, что результат - словарь
        assert isinstance(result, dict), "Результат должен быть словарем"
        
        # Если есть счета, проверяем структуру данных
        if result:
            for account_name, account_data in result.items():
                assert "account_id" in account_data, f"В данных счета {account_name} должен быть account_id"
                assert "positions" in account_data, f"В данных счета {account_name} должны быть positions"
                assert "transactions" in account_data, f"В данных счета {account_name} должны быть transactions"
                
                # Проверяем структуру позиций
                positions = account_data["positions"]
                assert isinstance(positions, list), "positions должен быть списком"
                
                for position in positions:
                    assert "figi" in position, "В позиции должен быть figi"
                    assert "quantity" in position, "В позиции должен быть quantity"
                
                # Проверяем структуру транзакций
                transactions = account_data["transactions"]
                assert isinstance(transactions, list), "transactions должен быть списком"
                
                for transaction in transactions:
                    assert "type" in transaction, "В транзакции должен быть type"
                    assert "date" in transaction, "В транзакции должна быть date"
    
    def test_unknown_operation_types(self):
        """Тест выявления неизвестных типов операций."""
        result = get_tinkoff_portfolio(TINKOFF_TOKEN)
        
        # Собираем все типы операций из транзакций
        operation_types = []
        for account_name, account_data in result.items():
            for transaction in account_data.get("transactions", []):
                op_type = transaction.get("type")
                if op_type:
                    operation_types.append(op_type)
        
        # Определяем неизвестные типы (те, которые не в OPERATION_CLASSIFICATION)
        known_types = set(OPERATION_CLASSIFICATION.values())
        unknown_types = set(operation_types) - known_types
        
        # Выводим информацию о типах операций
        print("\n" + "="*80)
        print("АНАЛИЗ ТИПОВ ОПЕРАЦИЙ")
        print("="*80)
        
        # Подсчитываем частоту каждого типа
        type_counter = Counter(operation_types)
        
        print("\n📊 Все типы операций (с частотой):")
        for op_type, count in type_counter.most_common():
            status = "✅" if op_type in known_types else "❌ НЕИЗВЕСТНЫЙ"
            print(f"  {status} {op_type}: {count} операций")
        
        if unknown_types:
            print(f"\n⚠️  Найдено {len(unknown_types)} неизвестных типов операций:")
            for unknown_type in sorted(unknown_types):
                print(f"  - {unknown_type}")
            print("\n💡 Добавьте эти типы в OPERATION_CLASSIFICATION в import_service.py")
        else:
            print("\n✅ Все типы операций известны и обработаны")
        
        print("="*80 + "\n")
        
        # Проверяем, что есть хотя бы какие-то операции (если есть счета)
        if result and any(account_data.get("transactions") for account_data in result.values()):
            assert len(operation_types) > 0, "Должны быть найдены операции"
    
    def test_payment_for_transactions(self):
        """Тест проверки payment для транзакций Buy/Sell/Redemption."""
        result = get_tinkoff_portfolio(TINKOFF_TOKEN)
        
        transactions_without_payment = []
        transactions_with_zero_payment = []
        
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
        
        # Выводим информацию о проблемах с payment
        print("\n" + "="*80)
        print("ПРОВЕРКА PAYMENT ДЛЯ ТРАНЗАКЦИЙ")
        print("="*80)
        
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
        
        # Проверяем, что нет транзакций без payment или с payment = 0
        assert len(transactions_without_payment) == 0, \
            f"Найдено {len(transactions_without_payment)} транзакций без payment. " \
            "Для импорта от брокера payment должен быть передан для всех транзакций."
        
        assert len(transactions_with_zero_payment) == 0, \
            f"Найдено {len(transactions_with_zero_payment)} транзакций с payment = 0. " \
            "Для облигаций с НКД payment может отличаться от price * quantity, " \
            "но payment не должен быть равен 0, если price и quantity не равны 0."
    
    def test_portfolio_structure(self):
        """Тест структуры данных портфеля."""
        result = get_tinkoff_portfolio(TINKOFF_TOKEN)
        
        print("\n" + "="*80)
        print("СТРУКТУРА ПОРТФЕЛЯ")
        print("="*80)
        
        if not result:
            print("⚠️  Портфель пуст (нет доступных счетов)")
            return
        
        for account_name, account_data in result.items():
            print(f"\n📁 Счёт: {account_name}")
            print(f"   ID: {account_data.get('account_id')}")
            
            positions = account_data.get("positions", [])
            transactions = account_data.get("transactions", [])
            
            print(f"   Позиций: {len(positions)}")
            print(f"   Транзакций: {len(transactions)}")
            
            if positions:
                print("\n   Позиции:")
                for pos in positions[:5]:  # Показываем первые 5
                    ticker = pos.get("ticker") or "N/A"
                    quantity = pos.get("quantity", 0)
                    current_price = pos.get("current_price", 0)
                    print(f"     - {ticker}: {quantity} шт. × {current_price:.2f} = {quantity * current_price:.2f}")
                if len(positions) > 5:
                    print(f"     ... и ещё {len(positions) - 5} позиций")
            
            if transactions:
                print("\n   Последние транзакции:")
                for tx in transactions[:5]:  # Показываем первые 5
                    tx_type = tx.get("type", "N/A")
                    date = tx.get("date", "N/A")
                    ticker = tx.get("ticker") or "N/A"
                    print(f"     - {date} | {tx_type} | {ticker}")
                if len(transactions) > 5:
                    print(f"     ... и ещё {len(transactions) - 5} транзакций")
        
        print("="*80 + "\n")
    
    def test_error_handling(self):
        """Тест обработки ошибок при недоступных счетах."""
        # Этот тест проверяет, что функция корректно обрабатывает ошибки
        # и не падает при недоступных счетах
        result = get_tinkoff_portfolio(TINKOFF_TOKEN)
        
        # Функция должна вернуть словарь (может быть пустым)
        assert isinstance(result, dict), "Результат должен быть словарем даже при ошибках"
        
        # Если есть результат, проверяем, что структура корректна
        for account_name, account_data in result.items():
            assert isinstance(account_data, dict), f"Данные счета {account_name} должны быть словарем"
            assert "account_id" in account_data, f"В данных счета {account_name} должен быть account_id"
            assert "positions" in account_data, f"В данных счета {account_name} должны быть positions"
            assert "transactions" in account_data, f"В данных счета {account_name} должны быть transactions"


def test_standalone_import():
    """
    Отдельный тест для ручного запуска.
    Можно запустить напрямую: python -m pytest tests/integration/test_tinkoff_import.py::test_standalone_import -v -s
    """
    token = os.getenv("TINKOFF_TOKEN")
    
    if not token:
        print("⚠️  TINKOFF_TOKEN не установлен. Установите переменную окружения для запуска теста.")
        pytest.skip("TINKOFF_TOKEN не установлен")
    
    print("\n" + "="*80)
    print("ТЕСТИРОВАНИЕ ИМПОРТА ПОРТФЕЛЯ TINKOFF")
    print("="*80)
    
    result = get_tinkoff_portfolio(token)
    
    print(f"\n✅ Получено данных для {len(result)} счетов")
    
    # Анализ типов операций
    all_operation_types = set()
    for account_data in result.values():
        for transaction in account_data.get("transactions", []):
            op_type = transaction.get("type")
            if op_type:
                all_operation_types.add(op_type)
    
    known_types = set(OPERATION_CLASSIFICATION.values())
    unknown_types = all_operation_types - known_types
    
    if unknown_types:
        print(f"\n⚠️  НАЙДЕНО {len(unknown_types)} НЕИЗВЕСТНЫХ ТИПОВ ОПЕРАЦИЙ:")
        for unknown_type in sorted(unknown_types):
            print(f"   - {unknown_type}")
        print("\n💡 Добавьте эти типы в OPERATION_CLASSIFICATION в import_service.py")
    else:
        print("\n✅ Все типы операций известны")
    
    print("="*80 + "\n")
    
    assert isinstance(result, dict)
