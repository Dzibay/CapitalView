"""
Скрипт для тестирования импорта портфеля от БКС.

Использование:
    python scripts/test_bks_import.py

Требуется переменная окружения BKS_REFRESH_TOKEN с refresh-токеном
(получается в веб-версии БКС Мир инвестиций).
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.external.brokers.bks import get_bks_portfolio


def main():
    token = os.getenv("BKS_REFRESH_TOKEN")

    if not token:
        print("❌ ОШИБКА: BKS_REFRESH_TOKEN не установлен!")
        print("\nУстановите переменную окружения:")
        print("  Windows PowerShell: $env:BKS_REFRESH_TOKEN='your_refresh_token_here'")
        print("  Windows CMD: set BKS_REFRESH_TOKEN=your_refresh_token_here")
        print("  Linux/Mac: export BKS_REFRESH_TOKEN='your_refresh_token_here'")
        print("\nТокен получается в веб-версии БКС Мир инвестиций.")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("ТЕСТИРОВАНИЕ ИМПОРТА ПОРТФЕЛЯ БКС")
    print("=" * 80)

    try:
        broker_data = get_bks_portfolio(token)

        if not broker_data:
            print("⚠️  Портфель пуст")
            return

        print("\n" + "-" * 80)
        print("ПОЛУЧЕННЫЕ ДАННЫЕ ОТ БРОКЕРА")
        print("-" * 80)

        for account_name, account_data in broker_data.items():
            print(f"\n📁 Счёт: {account_name}")
            print(f"   account_id: {account_data.get('account_id', 'N/A')}")

            positions = account_data.get("positions", [])
            print(f"\n   📊 Позиций: {len(positions)}")
            if positions:
                print("   " + "-" * 60)
                for i, p in enumerate(positions[:15], 1):
                    ticker = p.get("ticker") or "—"
                    qty = p.get("quantity", 0)
                    avg = p.get("average_price", 0)
                    curr = p.get("current_price", 0)
                    print(f"   {i:2}. {ticker:<12} | qty: {qty:>10.2f} | avg: {avg:>10.2f} | curr: {curr:>10.2f}")
                if len(positions) > 15:
                    print(f"   ... и ещё {len(positions) - 15} позиций")

            transactions = account_data.get("transactions", [])
            print(f"\n   📋 Сделок/операций: {len(transactions)}")
            if transactions:
                print("   " + "-" * 60)
                for i, tx in enumerate(transactions[:15], 1):
                    date_str = (tx.get("date") or "N/A")[:19]
                    tx_type = tx.get("type", "N/A")
                    ticker = (tx.get("ticker") or "—")[:10]
                    payment = tx.get("payment", 0)
                    print(f"   {i:2}. {date_str} | {tx_type:<10} | {ticker:<10} | {payment:>12,.2f}")
                if len(transactions) > 15:
                    print(f"   ... и ещё {len(transactions) - 15} операций")

        print("\n" + "-" * 80)
        print("RAW JSON (первые 2000 символов)")
        print("-" * 80)
        json_str = json.dumps(broker_data, ensure_ascii=False, indent=2)
        print(json_str[:2000])
        if len(json_str) > 2000:
            print("\n... (обрезано)")

        print("\n" + "=" * 80)
        print("✅ Тест завершён успешно")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
