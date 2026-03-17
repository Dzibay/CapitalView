"""
Сервис импорта портфеля из Tinkoff
"""
from datetime import datetime, timedelta
from t_tech.invest import Client, InstrumentIdType
from t_tech.invest.exceptions import RequestError
from grpc import StatusCode

OPERATION_CLASSIFICATION = {
    "OPERATION_TYPE_BUY": "Buy",
    "OPERATION_TYPE_BUY_CARD": "Buy",
    "OPERATION_TYPE_SELL": "Sell",
    "OPERATION_TYPE_DIVIDEND": "Dividend",
    "OPERATION_TYPE_DIV_EXT": "Dividend",
    "OPERATION_TYPE_COUPON": "Coupon",
    "OPERATION_TYPE_INPUT": "Deposit",
    "OPERATION_TYPE_INP_MULTI": "Deposit",
    "OPERATION_TYPE_OUTPUT": "Withdraw",
    "OPERATION_TYPE_OUT_MULTI": "Withdraw",
    "OPERATION_TYPE_BROKER_FEE": "Commission",
    "OPERATION_TYPE_SERVICE_FEE": "Commission",
    "OPERATION_TYPE_MARGIN_FEE": "Commission",
    "OPERATION_TYPE_TRACK_MFEE": "Commission",
    "OPERATION_TYPE_TRACK_PFEE": "Commission",
    "OPERATION_TYPE_DIVIDEND_TAX": "Tax",
    "OPERATION_TYPE_TAX_CORRECTION": "Tax",
    "OPERATION_TYPE_TAX_COUPON": "Tax",
    "OPERATION_TYPE_TAX_DIVIDEND": "Tax",
    "OPERATION_TYPE_TAX_BACK": "Tax",
    "OPERATION_TYPE_TAX": "Tax",
    "OPERATION_TYPE_BENEFIT_TAX": "Tax",
    "OPERATION_TYPE_BOND_REPAYMENT_FULL": "Redemption",
    "OPERATION_TYPE_BOND_REPAYMENT": "Redemption"
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


def get_tinkoff_portfolio(token):
    """Получает данные портфеля от брокера Tinkoff."""
    print("📥 Получаем данные от брокера Tinkoff...")

    result = {}
    instrument_cache = {}

    with Client(token) as client:
        accounts = client.users.get_accounts().accounts
        if not accounts:
            return {}

        now = datetime.utcnow()
        # from_date = now - timedelta(days=days)

        for account in accounts:
            acc_id = account.id
            acc_name = account.name or f"Account {acc_id}"
            print(f"🔹 Счёт: {acc_name}")

            try:
                # ПОЗИЦИИ
                try:
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
                except RequestError as e:
                    # Если счет недоступен для получения портфеля, пропускаем его
                    if e.code == StatusCode.NOT_FOUND and e.details == "50004":
                        print(f"⚠️  Счёт {acc_name} недоступен (Account not found), пропускаем")
                        continue
                    raise

                # ОПЕРАЦИИ
                try:
                    ops_raw = client.operations.get_operations(
                        account_id=acc_id,
                        # from_=from_date,
                        # to=now
                    ).operations
                except RequestError as e:
                    # Если счет недоступен для получения операций, используем пустой список операций
                    if e.code == StatusCode.NOT_FOUND and e.details == "50004":
                        print(f"⚠️  Операции для счёта {acc_name} недоступны (Account not found), используем пустой список")
                        ops_raw = []
                    else:
                        raise

                transactions = []
                
                # Создаем индекс операций Tax по дате и активу (figi) для быстрого поиска
                # Ключ: (дата операции, figi), значение: список сумм налогов
                tax_by_date_figi = {}
                for op in ops_raw:
                    tax_classified = OPERATION_CLASSIFICATION.get(op.operation_type.name, "")
                    if tax_classified == "Tax":
                        op_date = op.date.date() if op.date else None
                        op_figi = getattr(op, "figi", None)
                        if op_date:
                            tax_payment = op.payment.units + op.payment.nano / 1e9 if op.payment else 0
                            tax_key = (op_date, op_figi)
                            if tax_key not in tax_by_date_figi:
                                tax_by_date_figi[tax_key] = []
                            tax_by_date_figi[tax_key].append(tax_payment)

                for op in ops_raw:
                    figi = getattr(op, "figi", None)
                    price_obj = getattr(op, "price", None)
                    quantity = getattr(op, "quantity", None)
                    quantity_rest = getattr(op, "quantity_rest", None)

                    inst = resolve_instrument(client, figi, instrument_cache)

                    classified = OPERATION_CLASSIFICATION[op.operation_type.name] if op.operation_type.name in OPERATION_CLASSIFICATION else op.operation_type.name
                    
                    # Проверяем, является ли это операцией выплаты дивидендов на карту
                    is_div_ext = op.operation_type.name == "OPERATION_TYPE_DIV_EXT"

                    tx = {
                        "figi": figi,
                        "ticker": inst["ticker"] if inst else None,
                        "name": inst["name"] if inst else None,
                        "isin": inst["isin"] if inst else None,
                        "date": op.date.isoformat() if op.date else None,
                        "type": classified
                    }

                    # BUY / SELL / REDEMPTION (транзакции, которые изменяют количество актива)
                    if classified in ("Buy", "Sell", "Redemption"):
                        op_quantity = (quantity or 0) - (quantity_rest or 0)
                        
                        # Пропускаем операции с quantity = 0 (неисполненные заявки)
                        if classified in ("Buy", "Sell") and op_quantity == 0:
                            continue
                        
                        if classified == "Redemption":
                            # Для операций погашения облигаций quantity может быть 0,
                            # но есть payment (сумма выплаты).
                            # Количество будет рассчитано в portfolio_service из позиций портфеля на момент погашения
                            payment = op.payment.units + op.payment.nano / 1e9 if op.payment else 0
                            
                            tx.update({
                                "price": 0,  # Будет рассчитано из payment / quantity в portfolio_service
                                "quantity": op_quantity if op_quantity > 0 else 0,
                                "payment": payment,
                            })
                        else:
                            # Для Buy и Sell сохраняем и price (цена единицы актива) и payment (общая сумма операции)
                            # price используется в транзакции, payment - в cash_operation
                            # Они могут отличаться из-за накопленного купонного дохода (НКД) у облигаций
                            tx_price = price_obj.units + price_obj.nano / 1e9 if price_obj else None
                            tx_payment = op.payment.units + op.payment.nano / 1e9 if op.payment else 0
                            tx.update({
                                "price": tx_price,
                                "quantity": op_quantity,
                                "payment": tx_payment,
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
                    
                    # Если это OPERATION_TYPE_DIV_EXT (выплата дивидендов на карту),
                    # добавляем дополнительную операцию вывода средств (Withdraw) на сумму дивидендов
                    # Учитываем налог, если есть операция Tax в то же время и для того же актива (figi)
                    if is_div_ext and payment != 0:
                        # Ищем налог на ту же дату и для того же актива (figi)
                        op_date = op.date.date() if op.date else None
                        op_figi = getattr(op, "figi", None)
                        tax_amount = 0
                        tax_key = (op_date, op_figi)
                        if op_date and tax_key in tax_by_date_figi:
                            # Суммируем все налоги на эту дату для этого актива
                            # Налоги обычно отрицательные (уменьшают сумму), поэтому суммируем их
                            tax_amount = sum(tax_by_date_figi[tax_key])
                        
                        # Сумма вывода = сумма дивидендов - налог
                        # Если налог отрицательный (уменьшает сумму), то вычитаем его (добавляем к сумме)
                        # Если налог положительный (возврат налога), то вычитаем его (уменьшаем сумму)
                        withdraw_amount = -abs(payment) - tax_amount
                        
                        withdraw_tx = {
                            "figi": None,
                            "ticker": None,
                            "name": None,
                            "isin": None,
                            "date": op.date.isoformat() if op.date else None,
                            "type": "Withdraw",
                            "price": None,
                            "quantity": None,
                            "payment": withdraw_amount,  # Отрицательное значение для вывода средств (учитывает налог)
                            "currency": op.currency,
                        }
                        transactions.append(withdraw_tx)

                result[acc_name] = {
                    "account_id": acc_id,
                    "positions": positions,
                    "transactions": transactions
                }
            except RequestError as e:
                # Обработка других ошибок RequestError
                print(f"❌ Ошибка при обработке счёта {acc_name}: {e.code.name} - {e.details}")
                # Пропускаем этот счет и продолжаем обработку остальных
                continue
            except Exception as e:
                # Обработка любых других неожиданных ошибок
                print(f"❌ Неожиданная ошибка при обработке счёта {acc_name}: {str(e)}")
                # Пропускаем этот счет и продолжаем обработку остальных
                continue

    return result


# portfolio = get_tinkoff_portfolio('t.b7cVknEoyjXW6FG39o4woo12yzoCAKsTwYgT0LqYFvNEH0hC5IGSMtLxVEwGfwXOv048FR5kGmxMeFpEM-GCRQ')
# for acc in portfolio:
#     if acc == 'Облигации':
#         for tx in portfolio[acc]['transactions']:
#             print(tx)