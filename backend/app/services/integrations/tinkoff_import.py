import json
from datetime import datetime, timedelta
from tinkoff.invest import Client, InstrumentIdType

# === Сопоставление OperationType → operations_type.name ===
OPERATION_CLASSIFICATION = {
    # Активные операции
    "OPERATION_TYPE_BUY": "Buy",
    "OPERATION_TYPE_SELL": "Sell",

    # Доходы
    "OPERATION_TYPE_DIVIDEND": "Dividend",
    "OPERATION_TYPE_COUPON": "Coupon",

    # Пополнения / выводы
    "OPERATION_TYPE_INPUT": "Deposit",
    "OPERATION_TYPE_INP_MULTI": "Deposit",
    "OPERATION_TYPE_OUTPUT": "Withdraw",
    "OPERATION_TYPE_OUT_MULTI": "Withdraw",

    # Комиссии
    "OPERATION_TYPE_BROKER_FEE": "Comission",
    "OPERATION_TYPE_SERVICE_FEE": "Comission",
    "OPERATION_TYPE_TRACK_MFEE": "Comission",
    "OPERATION_TYPE_TRACK_PFEE": "Comission",
    "OPERATION_TYPE_MARGIN_FEE": "Comission",

    # Налоги
    "OPERATION_TYPE_DIVIDEND_TAX": "Tax",
    "OPERATION_TYPE_TAX_CORRECTION": "Tax",
    "OPERATION_TYPE_TAX_COUPON": "Tax",
    "OPERATION_TYPE_TAX_DIVIDEND": "Tax",
    "OPERATION_TYPE_TAX_BACK": "Tax",
}

def get_tinkoff_portfolio(token, days=365):
    """
    Получает портфель и все операции из Тинькофф Инвестиций.
    Классифицирует операции в соответствии с таблицей operations_type.
    Сохраняет результат в JSON.
    """
    print("📥 Получаем данные от брокера Tinkoff...")

    result_data = {}

    with Client(token) as client:
        accounts = client.users.get_accounts()
        if not accounts.accounts:
            print("⚠️ У пользователя нет брокерских счетов.")
            return {"positions": [], "transactions": []}

        now = datetime.utcnow()
        from_date = now - timedelta(days=days)

        for account in accounts.accounts:
            account_id = account.id
            account_name = getattr(account, "name", f"Account_{account_id}")
            print(f"🔹 Счёт: {account_name} ({account_id})")

            # === 1️⃣ Получаем текущие позиции ===
            portfolio = client.operations.get_portfolio(account_id=account_id)
            positions_data = []

            for position in portfolio.positions:
                figi = position.figi
                try:
                    instrument = client.instruments.get_instrument_by(
                        id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                        id=figi
                    ).instrument
                except Exception:
                    instrument = None

                positions_data.append({
                    "figi": figi,
                    "ticker": getattr(instrument, "ticker", None),
                    "name": getattr(instrument, "name", None),
                    "isin": getattr(instrument, "isin", None),
                    "instrument_type": getattr(instrument, "instrument_type", None),
                    "currency": getattr(instrument, "currency", None),
                    "lot": getattr(instrument, "lot", None),
                    "current_price": position.current_price.units + position.current_price.nano / 1e9,
                    "average_price": position.average_position_price.units + position.average_position_price.nano / 1e9,
                    "quantity": position.quantity.units + position.quantity.nano / 1e9,
                })

            # === 2️⃣ Получаем операции ===
            print(f"⏳ Загружаем операции за {days} дней...")
            operations = client.operations.get_operations(
                account_id=account_id,
                from_=from_date,
                to=now
            )

            transactions_data = []
            for op in operations.operations:
                op_type_name = getattr(op.operation_type, "name", "UNKNOWN")
                classified_type = OPERATION_CLASSIFICATION.get(op_type_name, "Other")

                price = getattr(op, "price", None)
                payment = (op.payment.units + op.payment.nano / 1e9) if getattr(op, "payment", None) else 0

                transactions_data.append({
                    "id": getattr(op, "id", None),
                    "figi": getattr(op, "figi", None),
                    "instrument_type": getattr(op, "instrument_type", None),
                    "date": getattr(op, "date", None).isoformat() if getattr(op, "date", None) else None,
                    "price": price.units + price.nano / 1e9 if price else None,
                    "quantity": getattr(op, "quantity", None),
                    "currency": getattr(op, "currency", None),
                    "payment": payment,
                    "state": getattr(op, "state", None).name if getattr(op, "state", None) else None,
                    "description": getattr(op, "name", None),
                    "operation_type": op_type_name,
                    "classified_type": classified_type,
                })

            result_data[account_name] = {
                "account_id": account_id,
                "positions": positions_data,
                "transactions": transactions_data,
            }

    # === 3️⃣ Сохраняем в файл ===
    # filename = f"tinkoff_classified_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    # with open(filename, "w", encoding="utf-8") as f:
    #     json.dump(result_data, f, indent=2, ensure_ascii=False)

    # print(f"✅ Данные успешно сохранены в файл: {filename}")
    return result_data



# data = get_tinkoff_portfolio('t.Wwc9-ETWh-SiWqphi_F3TQ-U7TZNsuhUryWHiDWu1vqvq19ypX7I9il3E9PlfZgKyt4gPiHrXD4RjyNiVUHzzA')
# for acc in data:
#     print(acc)
#     for pos in data[acc]["positions"]:
#         print('  ', pos)
#     print('\n\n')
#     for t in data[acc]["transactions"]:
#         print('  ', t)
    