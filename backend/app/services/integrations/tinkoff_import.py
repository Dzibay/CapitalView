from datetime import datetime, timedelta
from tinkoff.invest import Client, InstrumentIdType

OPERATION_CLASSIFICATION = {
    "OPERATION_TYPE_BUY": "Buy",
    "OPERATION_TYPE_SELL": "Sell",
    "OPERATION_TYPE_DIVIDEND": "Dividend",
    "OPERATION_TYPE_COUPON": "Coupon",

    "OPERATION_TYPE_INPUT": "Deposit",
    "OPERATION_TYPE_INP_MULTI": "Deposit",
    "OPERATION_TYPE_OUTPUT": "Withdraw",
    "OPERATION_TYPE_OUT_MULTI": "Withdraw",

    "OPERATION_TYPE_BROKER_FEE": "Comission",
    "OPERATION_TYPE_SERVICE_FEE": "Comission",
    "OPERATION_TYPE_MARGIN_FEE": "Comission",
    "OPERATION_TYPE_TRACK_MFEE": "Comission",
    "OPERATION_TYPE_TRACK_PFEE": "Comission",

    "OPERATION_TYPE_DIVIDEND_TAX": "Tax",
    "OPERATION_TYPE_TAX_CORRECTION": "Tax",
    "OPERATION_TYPE_TAX_COUPON": "Tax",
    "OPERATION_TYPE_TAX_DIVIDEND": "Tax",
    "OPERATION_TYPE_TAX_BACK": "Tax",
}


def resolve_instrument(client, figi, cache):
    """Получение тикера, isin, имени по FIGI"""
    if not figi:
        return None

    if figi in cache:
        return cache[figi]

    try:
        inst = client.instruments.get_instrument_by(
            id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
            id=figi
        ).instrument

        cache[figi] = {
            "ticker": inst.ticker,
            "name": inst.name,
            "isin": inst.isin,
            "lot": inst.lot,
        }
        return cache[figi]

    except:
        cache[figi] = None
        return None


def get_tinkoff_portfolio(token, days=365):
    print("📥 Получаем данные от брокера Tinkoff...")

    result = {}
    instrument_cache = {}

    with Client(token) as client:
        accounts = client.users.get_accounts().accounts
        if not accounts:
            return {}

        now = datetime.utcnow()
        from_date = now - timedelta(days=days)

        for account in accounts:
            acc_id = account.id
            acc_name = account.name or f"Account {acc_id}"
            print(f"🔹 Счёт: {acc_name}")

            # ======================
            # ПОЗИЦИИ
            # ======================
            portfolio = client.operations.get_portfolio(account_id=acc_id)
            positions = []

            for p in portfolio.positions:
                inst = resolve_instrument(client, p.figi, instrument_cache)

                positions.append({
                    "figi": p.figi,
                    "ticker": inst["ticker"] if inst else None,
                    "name": inst["name"] if inst else None,
                    "isin": inst["isin"] if inst else None,
                    "quantity": p.quantity.units + p.quantity.nano / 1e9,
                    "average_price": p.average_position_price.units + p.average_position_price.nano / 1e9,
                    "current_price": p.current_price.units + p.current_price.nano / 1e9,
                })

            # ======================
            # ОПЕРАЦИИ
            # ======================
            ops_raw = client.operations.get_operations(
                account_id=acc_id,
                from_=from_date,
                to=now
            ).operations

            transactions = []

            for op in ops_raw:
                figi = getattr(op, "figi", None)
                price_obj = getattr(op, "price", None)
                quantity = getattr(op, "quantity", None)
                quantity_rest = getattr(op, "quantity_rest", None)

                inst = resolve_instrument(client, figi, instrument_cache)

                classified = OPERATION_CLASSIFICATION.get(
                    op.operation_type.name,
                    "Other"
                )

                tx = {
                    "figi": figi,
                    "ticker": inst["ticker"] if inst else None,
                    "name": inst["name"] if inst else None,
                    "isin": inst["isin"] if inst else None,
                    "date": op.date.isoformat() if op.date else None,
                    "type": classified
                }

                # BUY / SELL
                if classified in ("Buy", "Sell"):
                    tx.update({
                        "price": price_obj.units + price_obj.nano / 1e9 if price_obj else None,
                        "quantity": (quantity or 0) - (quantity_rest or 0),
                        "payment": 0,
                    })

                # Денежные операции
                else:
                    payment = op.payment.units + op.payment.nano / 1e9 if op.payment else 0
                    tx.update({
                        "price": None,
                        "quantity": None,
                        "payment": payment,
                        "currency": op.currency,
                    })

                transactions.append(tx)

            # ======================
            result[acc_name] = {
                "account_id": acc_id,
                "positions": positions,
                "transactions": transactions
            }

    return result


data = get_tinkoff_portfolio('t.b7cVknEoyjXW6FG39o4woo12yzoCAKsTwYgT0LqYFvNEH0hC5IGSMtLxVEwGfwXOv048FR5kGmxMeFpEM-GCRQ')
for acc in data:
    if acc == 'Акции':
        print(acc)
        # for pos in data[acc]["positions"]:
        #     print('  ', pos)
        print('\n\n')
        for t in data[acc]["transactions"]:
            print('  ', t)
    