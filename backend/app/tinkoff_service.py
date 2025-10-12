from tinkoff.invest import Client, InstrumentIdType
from datetime import datetime, timedelta

def get_full_portfolio(token):
    with Client(token) as client:
        accounts = client.users.get_accounts()
        if not accounts.accounts:
            return {"positions": [], "transactions": []}

        account_id = accounts.accounts[0].id

        # 1. Портфель
        portfolio = client.operations.get_portfolio(account_id=account_id)
        positions_data = []

        for position in portfolio.positions:
            figi = position.figi
            instrument = client.instruments.get_instrument_by(
                id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                id=figi
            ).instrument

            # проверяем поля
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

        # 2. Транзакции за последний год
        now = datetime.utcnow()
        one_year_ago = now - timedelta(days=365)
        operations = client.operations.get_operations(
            account_id=account_id,
            from_=one_year_ago,
            to=now
        )

        transactions_data = []
        for op in operations.operations:
            price = getattr(op, 'price', None)
            op_type_str = op.operation_type.name.lower()  # 'operation_type_buy'
            if "buy" in op_type_str:
                op_type_str = "buy"
            elif "sell" in op_type_str:
                op_type_str = "sell"
            else:
                op_type_str = "other"
            transactions_data.append({
                "id": getattr(op, 'id', None),
                "figi": getattr(op, 'figi', None),
                "instrument_type": op.instrument_type if getattr(op, 'instrument_type', None) else None,
                "date": getattr(op, 'date', None),
                "price": price.units + price.nano / 1e9 if price else None,
                "quantity": getattr(op, 'quantity', None),
                "type": op_type_str,
                "currency": price.currency if price and getattr(price, 'currency', None) else None
            })

        return {
            "positions": positions_data,
            "transactions": transactions_data
        }

# -------------------------
# Пример использования
# -------------------------
if __name__ == 'main':
    token = 't.Wwc9-ETWh-SiWqphi_F3TQ-U7TZNsuhUryWHiDWu1vqvq19ypX7I9il3E9PlfZgKyt4gPiHrXD4RjyNiVUHzzA'
    data = get_full_portfolio(token)
    positions = data['positions']
    transactions = data["transactions"]
    for position in positions:
        print(position['ticker'])
        for i in transactions:
            if i['figi'] == position['figi']:
                if i['price'] != 0:
                    if i['quantity'] > 0:
                        print(i['is_buy'], i['quantity'], i['price'], i['date'])

