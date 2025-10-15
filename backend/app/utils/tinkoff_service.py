from tinkoff.invest import Client, InstrumentIdType
from datetime import datetime, timedelta

def get_full_portfolio(token, days=365):
    print('Получаем данные от брокера')
    """
    Получает портфель и транзакции пользователя в Тинькофф Инвестициях.
    """

    with Client(token) as client:
        accounts = client.users.get_accounts()
        if not accounts.accounts:
            return {"positions": [], "transactions": []}

        result_data = {}
        for account in accounts.accounts:
            print(f'Account {account}')
            account_id = account.id

            # 1️⃣ Получаем текущие позиции
            portfolio = client.operations.get_portfolio(account_id=account_id)
            positions_data = []

            for position in portfolio.positions:
                figi = position.figi
                instrument = client.instruments.get_instrument_by(
                    id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                    id=figi
                ).instrument

                instrument_type = getattr(instrument, 'instrument_type', None)
                currency = getattr(instrument, 'currency', None)

                positions_data.append({
                    "figi": figi,
                    "ticker": getattr(instrument, 'ticker', None),
                    "name": getattr(instrument, 'name', None),
                    "isin": getattr(instrument, 'isin', None),
                    "instrument_type": instrument_type if instrument_type else None,
                    "lot": getattr(instrument, 'lot', None),
                    "currency": currency if currency else None,
                    "current_price": position.current_price.units + position.current_price.nano / 1e9,
                    "average_price": position.average_position_price.units + position.average_position_price.nano / 1e9,
                    "quantity": position.quantity.units + position.quantity.nano / 1e9
                })

            # 2️⃣ Получаем операции
            now = datetime.utcnow()
            from_date = now - timedelta(days=days)

            operations = client.operations.get_operations(
                account_id=account_id,
                from_=from_date,
                to=now
            )
            transactions_data = []
            for op in operations.operations:
                if getattr(op, 'quantity', 0) > 0:
                    price = getattr(op, 'price', None)
                    op_type_str = op.operation_type.name.lower()

                    # Определяем тип операции (buy/sell)
                    if "buy" in op_type_str:
                        op_type_str = "buy"
                    elif "sell" in op_type_str:
                        op_type_str = "sell"
                    else:
                        op_type_str = "other"

                    transactions_data.append({
                        "id": getattr(op, 'id', None),
                        "figi": getattr(op, 'figi', None),
                        "instrument_type": getattr(op, 'instrument_type', None),
                        "date": getattr(op, 'date', None),
                        "price": price.units + price.nano / 1e9 if price else None,
                        "quantity": getattr(op, 'quantity', None),
                        "type": op_type_str,
                        "currency": getattr(price, 'currency', None) if price else None
                    })
            result_data[account.name] = {"positions": positions_data, "transactions": transactions_data}
        return result_data

