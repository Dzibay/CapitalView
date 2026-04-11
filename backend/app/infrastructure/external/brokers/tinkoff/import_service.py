"""
Сервис импорта портфеля из Tinkoff
"""
from datetime import datetime, timedelta
from t_tech.invest import Client, InstrumentIdType
from t_tech.invest.exceptions import RequestError
from grpc import StatusCode

from app.core.logging import get_logger

logger = get_logger(__name__)

# Маппинг OperationType (Tinkoff Invest API) → внутренние типы для portfolio_import_service.
# Неизвестное имя типа (новый enum в API и т.п.) → Other (см. classify_tinkoff_operation).
OPERATION_CLASSIFICATION = {
    # Buy
    "OPERATION_TYPE_BUY": "Buy",
    "OPERATION_TYPE_BUY_CARD": "Buy",
    "OPERATION_TYPE_BUY_MARGIN": "Buy",
    "OPERATION_TYPE_DELIVERY_BUY": "Buy",
    "OPERATION_TYPE_INPUT_SECURITIES": "Buy",
    # Sell
    "OPERATION_TYPE_DELIVERY_SELL": "Sell",
    "OPERATION_TYPE_OUTPUT_SECURITIES": "Sell",
    "OPERATION_TYPE_SELL": "Sell",
    "OPERATION_TYPE_SELL_CARD": "Sell",
    "OPERATION_TYPE_SELL_MARGIN": "Sell",
    # Dividend
    "OPERATION_TYPE_DIVIDEND": "Dividend",
    "OPERATION_TYPE_DIVIDEND_TRANSFER": "Dividend",
    "OPERATION_TYPE_DIV_EXT": "Dividend",
    # Coupon
    "OPERATION_TYPE_COUPON": "Coupon",
    # Deposit
    "OPERATION_TYPE_INPUT": "Deposit",
    "OPERATION_TYPE_INPUT_ACQUIRING": "Deposit",
    "OPERATION_TYPE_INPUT_SWIFT": "Deposit",
    "OPERATION_TYPE_INP_MULTI": "Deposit",
    # Withdraw
    "OPERATION_TYPE_OUTPUT": "Withdraw",
    "OPERATION_TYPE_OUTPUT_ACQUIRING": "Withdraw",
    "OPERATION_TYPE_OUTPUT_SWIFT": "Withdraw",
    "OPERATION_TYPE_OUT_MULTI": "Withdraw",
    # Commission
    "OPERATION_TYPE_ADVICE_FEE": "Commission",
    "OPERATION_TYPE_BROKER_FEE": "Commission",
    "OPERATION_TYPE_CASH_FEE": "Commission",
    "OPERATION_TYPE_MARGIN_FEE": "Commission",
    "OPERATION_TYPE_OTHER_FEE": "Commission",
    "OPERATION_TYPE_OUT_FEE": "Commission",
    "OPERATION_TYPE_OUTPUT_PENALTY": "Commission",
    "OPERATION_TYPE_OUT_STAMP_DUTY": "Commission",
    "OPERATION_TYPE_OVER_COM": "Commission",
    "OPERATION_TYPE_SERVICE_FEE": "Commission",
    "OPERATION_TYPE_SUCCESS_FEE": "Commission",
    "OPERATION_TYPE_TRACK_MFEE": "Commission",
    "OPERATION_TYPE_TRACK_PFEE": "Commission",
    # Tax
    "OPERATION_TYPE_BENEFIT_TAX": "Tax",
    "OPERATION_TYPE_BENEFIT_TAX_PROGRESSIVE": "Tax",
    "OPERATION_TYPE_BOND_TAX": "Tax",
    "OPERATION_TYPE_BOND_TAX_PROGRESSIVE": "Tax",
    "OPERATION_TYPE_DIVIDEND_TAX": "Tax",
    "OPERATION_TYPE_DIVIDEND_TAX_PROGRESSIVE": "Tax",
    "OPERATION_TYPE_TAX": "Tax",
    "OPERATION_TYPE_TAX_CORRECTION": "Tax",
    "OPERATION_TYPE_TAX_CORRECTION_COUPON": "Tax",
    "OPERATION_TYPE_TAX_CORRECTION_PROGRESSIVE": "Tax",
    "OPERATION_TYPE_TAX_PROGRESSIVE": "Tax",
    "OPERATION_TYPE_TAX_REPO": "Tax",
    "OPERATION_TYPE_TAX_REPO_HOLD": "Tax",
    "OPERATION_TYPE_TAX_REPO_HOLD_PROGRESSIVE": "Tax",
    "OPERATION_TYPE_TAX_REPO_PROGRESSIVE": "Tax",
    "OPERATION_TYPE_TAX_REPO_REFUND": "Tax",
    "OPERATION_TYPE_TAX_REPO_REFUND_PROGRESSIVE": "Tax",
    # Amortization
    "OPERATION_TYPE_BOND_REPAYMENT": "Amortization",
    "OPERATION_TYPE_BOND_REPAYMENT_FULL": "Amortization",
    "OPERATION_TYPE_DFA_REDEMPTION": "Amortization",
    # Other
    "OPERATION_TYPE_ACCRUING_VARMARGIN": "Other",
    "OPERATION_TYPE_FUTURE_EXPIRATION": "Other",
    "OPERATION_TYPE_OPTION_EXPIRATION": "Other",
    "OPERATION_TYPE_OTHER": "Other",
    "OPERATION_TYPE_OVERNIGHT": "Other",
    "OPERATION_TYPE_OVER_INCOME": "Other",
    "OPERATION_TYPE_OVER_PLACEMENT": "Other",
    "OPERATION_TYPE_PRIMARY_ORDER": "Other",
    "OPERATION_TYPE_TRANS_BS_BS": "Other",
    "OPERATION_TYPE_TRANS_IIS_BS": "Other",
    "OPERATION_TYPE_UNSPECIFIED": "Other",
    "OPERATION_TYPE_WRITING_OFF_VARMARGIN": "Other",
}

IMPORT_CANONICAL_TYPES = frozenset(OPERATION_CLASSIFICATION.values())


def classify_tinkoff_operation(operation_type_name: str) -> str:
    """Возвращает внутренний тип операции; при отсутствии в маппинге — Other."""
    return OPERATION_CLASSIFICATION.get(operation_type_name, "Other")


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


def _money_value_to_dict(mv) -> dict | None:
    if mv is None:
        return None
    return {
        "currency": mv.currency,
        "units": int(mv.units),
        "nano": int(mv.nano),
    }


def tinkoff_operation_to_raw_dict(op, client, instrument_cache: dict) -> dict:
    """
    Сериализация ответа get_operations в JSON-совместимый словарь (поля protobuf/dataclass API).
    Добавляет ticker / instrument_name / isin по FIGI через resolve_instrument.
    """
    figi = getattr(op, "figi", None) or None
    if figi == "":
        figi = None
    inst = resolve_instrument(client, figi, instrument_cache) if figi else None

    ot = getattr(op, "operation_type", None)
    operation_type_name = ot.name if ot is not None and hasattr(ot, "name") else str(ot)

    st = getattr(op, "state", None)
    state_name = st.name if st is not None and hasattr(st, "name") else (str(st) if st is not None else None)

    trades_out = []
    for tr in getattr(op, "trades", None) or []:
        trades_out.append({
            "trade_id": getattr(tr, "trade_id", None),
            "date_time": tr.date_time.isoformat() if getattr(tr, "date_time", None) else None,
            "quantity": getattr(tr, "quantity", None),
            "price": _money_value_to_dict(getattr(tr, "price", None)),
        })

    child_ops = []
    for ch in getattr(op, "child_operations", None) or []:
        child_ops.append({
            "instrument_uid": getattr(ch, "instrument_uid", None),
            "payment": _money_value_to_dict(getattr(ch, "payment", None)),
        })

    return {
        "id": getattr(op, "id", None),
        "parent_operation_id": getattr(op, "parent_operation_id", None),
        "currency": getattr(op, "currency", None),
        "payment": _money_value_to_dict(getattr(op, "payment", None)),
        "price": _money_value_to_dict(getattr(op, "price", None)),
        "state": state_name,
        "quantity": getattr(op, "quantity", None),
        "quantity_rest": getattr(op, "quantity_rest", None),
        "figi": figi,
        "instrument_type": getattr(op, "instrument_type", None),
        "date": op.date.isoformat() if getattr(op, "date", None) else None,
        "type": getattr(op, "type", None),
        "operation_type": operation_type_name,
        "trades": trades_out,
        "asset_uid": getattr(op, "asset_uid", None),
        "position_uid": getattr(op, "position_uid", None),
        "instrument_uid": getattr(op, "instrument_uid", None),
        "child_operations": child_ops,
        "ticker": inst["ticker"] if inst else None,
        "instrument_name": inst["name"] if inst else None,
        "isin": inst["isin"] if inst else None,
    }


def get_tinkoff_portfolio(token, *, include_raw_operations: bool = False):
    """
    Получает данные портфеля от брокера Tinkoff.

    include_raw_operations: добавить в каждый счёт ключ operations_raw — список словарей
    с максимально полным снимком операций из get_operations (удобно для отладки импорта).
    """
    logger.info("Tinkoff portfolio import start")

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
            logger.info("Tinkoff account name=%s", acc_name)

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
                        logger.warning("Tinkoff account not found, skip name=%s", acc_name)
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
                        logger.warning(
                            "Tinkoff operations unavailable (Account not found), empty ops name=%s",
                            acc_name,
                        )
                        ops_raw = []
                    else:
                        raise

                transactions = []
                transactions_skipped = []

                # Создаем индекс операций Tax по дате и активу (figi) для быстрого поиска
                # Ключ: (дата операции, figi), значение: список сумм налогов
                tax_by_date_figi = {}
                for op in ops_raw:
                    tax_classified = classify_tinkoff_operation(op.operation_type.name)
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

                    classified = classify_tinkoff_operation(op.operation_type.name)
                    
                    # Проверяем, является ли это операцией выплаты дивидендов на карту
                    is_div_ext = op.operation_type.name == "OPERATION_TYPE_DIV_EXT"

                    tx = {
                        "figi": figi,
                        "ticker": inst["ticker"] if inst else None,
                        "name": inst["name"] if inst else None,
                        "isin": inst["isin"] if inst else None,
                        "date": op.date.isoformat() if op.date else None,
                        "type": classified,
                        "tinkoff_operation_type": op.operation_type.name,
                    }

                    # BUY / SELL / AMORTIZATION (транзакции, которые изменяют количество актива)
                    if classified in ("Buy", "Sell", "Amortization"):
                        op_quantity = (quantity or 0) - (quantity_rest or 0)
                        
                        # Пропускаем операции с quantity = 0 (неисполненные заявки)
                        if classified in ("Buy", "Sell") and op_quantity == 0:
                            pay_skip = op.payment.units + op.payment.nano / 1e9 if op.payment else 0
                            transactions_skipped.append({
                                "date": op.date.isoformat() if op.date else None,
                                "tinkoff_operation_type": op.operation_type.name,
                                "type": classified,
                                "reason": "buy_sell_zero_executed_quantity",
                                "figi": figi,
                                "ticker": inst["ticker"] if inst else None,
                                "name": inst["name"] if inst else None,
                                "quantity_api": quantity,
                                "quantity_rest": quantity_rest,
                                "executed_quantity": op_quantity,
                                "payment": pay_skip,
                                "currency": op.currency,
                            })
                            continue
                        
                        if classified == "Amortization":
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
                            "tinkoff_operation_type": "SYNTHETIC_DIV_EXT_WITHDRAW",
                            "price": None,
                            "quantity": None,
                            "payment": withdraw_amount,  # Отрицательное значение для вывода средств (учитывает налог)
                            "currency": op.currency,
                        }
                        transactions.append(withdraw_tx)

                entry = {
                    "account_id": acc_id,
                    "positions": positions,
                    "transactions": transactions,
                    "transactions_skipped": transactions_skipped,
                    "operations_raw_count": len(ops_raw),
                }
                if include_raw_operations:
                    entry["operations_raw"] = [
                        tinkoff_operation_to_raw_dict(op, client, instrument_cache) for op in ops_raw
                    ]
                result[acc_name] = entry
            except RequestError as e:
                # Обработка других ошибок RequestError
                logger.error(
                    "Tinkoff account error name=%s code=%s details=%s",
                    acc_name,
                    e.code.name,
                    e.details,
                )
                # Пропускаем этот счет и продолжаем обработку остальных
                continue
            except Exception as e:
                # Обработка любых других неожиданных ошибок
                logger.error("Tinkoff account unexpected error name=%s err=%s", acc_name, e, exc_info=True)
                # Пропускаем этот счет и продолжаем обработку остальных
                continue

    return result

