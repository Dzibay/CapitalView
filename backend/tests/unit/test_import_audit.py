"""
Регрессионные тесты аудита импорта брокера (Т-Инвестиции / БКС).

Без сети и без боевой БД: Tinkoff SDK и слой БД подменяются моками.
Тесты, которым нужна настоящая PostgreSQL, — в test_import_audit_db.py
(запускаются только при CV_AUDIT_DB=1).
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from grpc import StatusCode
from t_tech.invest import OperationState
from t_tech.invest.exceptions import RequestError

from app.domain.services import portfolio_import_service as pis
from app.domain.services import portfolio_service, task_service
from app.infrastructure.external.brokers.tinkoff import import_service as tis

pytestmark = pytest.mark.unit

USD_ID = 2
STOCK_USD = 700
BOND_RUB = 10
OP_TYPES = {
    "buy": 1, "sell": 2, "dividend": 3, "coupon": 4, "deposit": 5,
    "withdraw": 6, "commission": 7, "tax": 8, "amortization": 9, "other": 10,
}


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Валидация ответа брокера до любых изменений
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("data", [None, {}, [], {"Брокерский": {"positions": []}}, {"Брокерский": None}])
def test_validate_broker_data_rejects_empty_or_broken(data):
    with pytest.raises(ValueError, match="данные портфеля не изменены"):
        pis._validate_broker_data(data)


def test_validate_broker_data_accepts_account_without_operations():
    pis._validate_broker_data({"ИИС": {"positions": [], "transactions": []}})


def test_import_with_empty_broker_data_touches_nothing():
    with patch.object(pis, "get_user_by_email", AsyncMock()) as get_user, \
         patch.object(pis, "db_transaction") as tx, \
         patch.object(pis, "rpc_async", AsyncMock()) as rpc:
        with pytest.raises(ValueError):
            run(pis.import_broker_portfolio("u@example.test", 1, {}, broker_id=1))
    get_user.assert_not_called()
    tx.assert_not_called()
    rpc.assert_not_called()


# ---------------------------------------------------------------------------
# Валюта: суммы в USD не делятся на курс второй раз, комиссия в рублях
# ---------------------------------------------------------------------------

RATES = {USD_ID: {"2024-03-01": 90.0}}
FX_MAP = {STOCK_USD: USD_ID}
QUOTE_CODES = {USD_ID: "usd"}


def test_fx_amounts_already_in_quote_currency_are_not_converted():
    price, payment = pis._convert_price_payment_to_rub_if_needed(
        STOCK_USD, FX_MAP, RATES, "2024-03-01T10:00:00", 150.0, -1500.0,
        price_currency="usd", payment_currency="USD", quote_code_by_id=QUOTE_CODES,
    )
    assert (price, payment) == (150.0, -1500.0)


def test_fx_amounts_in_rub_are_converted_to_quote():
    price, payment = pis._convert_price_payment_to_rub_if_needed(
        STOCK_USD, FX_MAP, RATES, "2024-03-01T10:00:00", 13500.0, -135000.0,
        price_currency="rub", payment_currency="rub", quote_code_by_id=QUOTE_CODES,
    )
    assert (price, payment) == (150.0, -1500.0)


def test_commission_in_rub_for_fx_asset_keeps_rub_amount():
    comm, comm_rub = pis._commission_quote_and_rub(
        STOCK_USD, FX_MAP, RATES, "2024-03-01T10:00:00", -45.0, "rub", QUOTE_CODES,
    )
    assert comm == pytest.approx(-0.5)
    assert comm_rub == pytest.approx(-45.0)


def test_commission_in_usd_for_fx_asset_converted_to_rub():
    comm, comm_rub = pis._commission_quote_and_rub(
        STOCK_USD, FX_MAP, RATES, "2024-03-01T10:00:00", -0.5, "usd", QUOTE_CODES,
    )
    assert comm == pytest.approx(-0.5)
    assert comm_rub == pytest.approx(-45.0)


def test_commission_for_rub_asset_unchanged():
    assert pis._commission_quote_and_rub(
        BOND_RUB, FX_MAP, RATES, "2024-03-01", -3.0, "rub", QUOTE_CODES,
    ) == (-3.0, -3.0)


# ---------------------------------------------------------------------------
# Tinkoff: отменённые операции, пагинация, справочник инструментов, имена счетов
# ---------------------------------------------------------------------------

def _op(op_id, state):
    return SimpleNamespace(id=op_id, state=state)


def test_canceled_operations_are_dropped_and_all_pages_read():
    pages = {
        "": SimpleNamespace(
            items=[_op("1", OperationState.OPERATION_STATE_EXECUTED),
                   _op("2", OperationState.OPERATION_STATE_CANCELED)],
            has_next=True, next_cursor="c2",
        ),
        "c2": SimpleNamespace(
            items=[_op("3", OperationState.OPERATION_STATE_PROGRESS)],
            has_next=False, next_cursor="",
        ),
    }
    client = MagicMock()
    client.operations.get_operations_by_cursor.side_effect = lambda req: pages[req.cursor]
    ops = tis._get_all_tinkoff_operations(client, "acc")
    assert [o.id for o in ops] == ["1", "3"]


def test_pagination_stops_on_repeated_cursor():
    page = SimpleNamespace(items=[_op("1", OperationState.OPERATION_STATE_EXECUTED)],
                           has_next=True, next_cursor="same")
    client = MagicMock()
    client.operations.get_operations_by_cursor.return_value = page
    ops = tis._get_all_tinkoff_operations(client, "acc")
    assert client.operations.get_operations_by_cursor.call_count == 2
    assert len(ops) == 2


def _instrument_client(*effects):
    client = MagicMock()
    client.instruments.get_instrument_by.side_effect = list(effects)
    return client


def _instrument():
    return SimpleNamespace(instrument=SimpleNamespace(ticker="SBER", name="Сбербанк", isin="RU0009029540", lot=10))


def test_resolve_instrument_not_found_is_cached_as_unknown():
    cache = {}
    client = _instrument_client(RequestError(StatusCode.NOT_FOUND, "nf", None))
    assert tis.resolve_instrument(client, "FIGI1", cache) is None
    assert cache == {"FIGI1": None}


def test_resolve_instrument_retries_rate_limit():
    cache = {}
    client = _instrument_client(
        RequestError(StatusCode.RESOURCE_EXHAUSTED, "limit", None),
        RequestError(StatusCode.UNAVAILABLE, "net", None),
        _instrument(),
    )
    with patch.object(tis.time, "sleep") as sleep:
        info = tis.resolve_instrument(client, "FIGI1", cache)
    assert info["ticker"] == "SBER"
    assert sleep.call_count == 2


def test_resolve_instrument_other_errors_fail_import_instead_of_skipping_asset():
    cache = {}
    client = _instrument_client(RequestError(StatusCode.PERMISSION_DENIED, "token", None))
    with pytest.raises(RequestError):
        tis.resolve_instrument(client, "FIGI1", cache)
    assert "FIGI1" not in cache


def test_accounts_with_same_name_do_not_overwrite_each_other():
    taken = {"Брокерский счёт": {}}
    assert tis._unique_account_name("ИИС", "2000111", taken) == "ИИС"
    assert tis._unique_account_name("Брокерский счёт", "2000123456", taken) == "Брокерский счёт (3456)"
    taken["Брокерский счёт (3456)"] = {}
    assert tis._unique_account_name("Брокерский счёт", "9993456", taken) == "Брокерский счёт (3456-2)"


# ---------------------------------------------------------------------------
# Сборка батча и атомарность импорта (БД замокана)
# ---------------------------------------------------------------------------

def _broker_data(*transactions):
    return {"Брокерский счёт": {"positions": [], "transactions": list(transactions)}}


BUY_BOND = {
    "type": "Buy", "date": "2024-03-01T10:00:00", "isin": "RU000ABOND01",
    "price": 1000.0, "quantity": 10, "payment": -10000.0, "commission": -5.0, "currency": "rub",
}


def _patched_import(
    apply_result=None, apply_error=None, portfolio_assets=None,
    children=None, suppressions=None, kept_manual=None, market_price=None,
):
    """Патчи вокруг _import_broker_portfolio_locked.

    children — дочерние портфели прошлой синхронизации, suppressions — {portfolio_id: [external_id]}
    (удалённое пользователем), kept_manual — ручные записи, которые вернула очистка.
    """
    m = SimpleNamespace(rpc_calls=[])
    m.apply = AsyncMock(return_value=apply_result or {"inserted_count": 1, "failed_count": 0})
    if apply_error is not None:
        m.apply.side_effect = apply_error
    m.upsert = AsyncMock()
    m.insert = AsyncMock(return_value=[{"id": 501}])
    m.update = AsyncMock(return_value=[{}])

    async def fake_rpc(name, params=None):
        m.rpc_calls.append((name, params))
        if name == "batch_create_portfolio_assets":
            return {str(aid): 900 + aid for aid in params["p_asset_ids"]}
        if name == "clear_broker_portfolio_data":
            kept = kept_manual or {}
            return {"kept_manual": kept, "kept_manual_count": sum(len(v) for v in kept.values())}
        return None

    async def fake_select(table, select="*", filters=None, *args, **kwargs):
        if table == "portfolios":
            return [dict(c) for c in children or []]
        if table == "broker_operation_suppressions":
            return [{"external_id": e} for e in (suppressions or {}).get(filters["portfolio_id"], [])]
        if table == "portfolio_assets":
            return list(portfolio_assets or [])
        return []

    m.patches = [
        patch.object(pis, "rpc_async", AsyncMock(side_effect=fake_rpc)),
        patch.object(pis, "_load_reference_data_for_import", AsyncMock(return_value=(
            OP_TYPES, [], {"RU000ABOND01": BOND_RUB}, {}, {}, {},
        ))),
        patch.object(pis, "collect_broker_instruments", MagicMock(return_value={})),
        patch.object(pis, "_ensure_user_broker_assets", AsyncMock()),
        patch.object(pis, "_load_currency_rates", AsyncMock(return_value={})),
        patch.object(pis, "table_insert_async", m.insert),
        patch.object(pis, "table_update_async", m.update),
        patch.object(pis, "table_select_async", AsyncMock(side_effect=fake_select)),
        patch.object(pis, "_asset_ids_that_exist", AsyncMock(return_value={BOND_RUB})),
        patch.object(pis, "_market_price_on", AsyncMock(return_value=market_price)),
        patch.object(pis._operation_repository, "apply_operations_batch", m.apply),
        patch("app.domain.services.broker_connections_service.upsert_broker_connection", m.upsert),
    ]
    return m


def _run_import(broker_data, **kw):
    m = _patched_import(**kw)
    for p in m.patches:
        p.start()
    try:
        m.result = run(pis._import_broker_portfolio_locked("user-1", 100, broker_data, 1, "token"))
        return m
    finally:
        for p in reversed(m.patches):
            p.stop()


def _run_locked(broker_data, **kw):
    m = _run_import(broker_data, **kw)
    return m.result, m.apply, m.upsert


def test_partial_amortization_becomes_cash_payout_not_redemption():
    partial = {
        "type": "Amortization", "date": "2024-04-01T00:00:00", "isin": "RU000ABOND01",
        "quantity": 0, "payment": 5000.0, "currency": "rub",
        "tinkoff_operation_type": "OPERATION_TYPE_BOND_REPAYMENT",
    }
    _, apply_mock, _ = _run_locked(_broker_data(BUY_BOND, partial))
    batch = apply_mock.call_args.args[0]
    amort = [op for op in batch if op["operation_type"] == OP_TYPES["amortization"]]
    assert len(amort) == 1
    assert amort[0]["amount"] == 5000.0
    assert "quantity" not in amort[0]  # не транзакция: позиция не списывается


def test_full_redemption_stays_transaction():
    full = {
        "type": "Amortization", "date": "2024-05-01T00:00:00", "isin": "RU000ABOND01",
        "quantity": 10, "payment": 10000.0, "currency": "rub",
        "tinkoff_operation_type": "OPERATION_TYPE_BOND_REPAYMENT_FULL",
    }
    _, apply_mock, _ = _run_locked(_broker_data(BUY_BOND, full))
    batch = apply_mock.call_args.args[0]
    amort = [op for op in batch if op["operation_type"] == OP_TYPES["amortization"]]
    assert amort[0]["quantity"] == 10.0
    assert amort[0]["price"] == 1000.0


def test_bks_partial_amortization_flag():
    assert pis._is_partial_amortization({"amortization_kind": "partial"})
    assert not pis._is_partial_amortization({"amortization_kind": "full"})


def test_batch_failure_aborts_whole_import():
    with pytest.raises(RuntimeError, match="импорт отменён"):
        _run_locked(_broker_data(BUY_BOND), apply_error=Exception("duplicate key"))


def test_import_result_reports_skipped_and_failed_operations():
    unknown = dict(BUY_BOND, isin="RU000UNKNOWN", date="2024-03-02T10:00:00")
    failed = [{"operation": {}, "error": "Not enough quantity to sell"}]
    result, _, upsert = _run_locked(
        _broker_data(BUY_BOND, unknown),
        apply_result={"inserted_count": 1, "failed_count": 1, "failed_operations": failed},
    )
    acc = result["accounts"][0]
    assert result["failed_count"] == 1 and result["skipped_count"] == 1
    assert acc["skipped_operations"][0]["reason"] == "asset_not_found"
    assert acc["failed_operations"] == failed
    upsert.assert_awaited_once()


# ---------------------------------------------------------------------------
# Сверка остатков с позициями брокера
# ---------------------------------------------------------------------------

ASSETS = {
    BOND_RUB: {"id": BOND_RUB, "ticker": "BOND", "name": "ОФЗ", "asset_type_id": 2},
    USD_ID: {"id": USD_ID, "ticker": "USD", "name": "Доллар", "asset_type_id": 7},
    STOCK_USD: {"id": STOCK_USD, "ticker": "AAPL", "name": "Apple", "asset_type_id": 1},
}


def test_reconcile_all_positions_match():
    rec = pis._reconcile_positions(
        {BOND_RUB: {"quantity": 10.0}, STOCK_USD: {"quantity": 3.0}},
        [],
        [{"asset_id": BOND_RUB, "quantity": 10}, {"asset_id": STOCK_USD, "quantity": 3.0000000001}],
        ASSETS,
    )
    assert rec == {"checked": 2, "matched": 2, "mismatch_count": 0, "mismatches": []}


def test_reconcile_reports_quantity_difference_both_ways():
    rec = pis._reconcile_positions(
        {BOND_RUB: {"quantity": 10.0, "ticker": "SU26238"}},
        [],
        [{"asset_id": BOND_RUB, "quantity": 7}, {"asset_id": STOCK_USD, "quantity": 2}],
        ASSETS,
    )
    assert rec["mismatch_count"] == 2
    by_id = {m["asset_id"]: m for m in rec["mismatches"]}
    assert by_id[BOND_RUB]["ticker"] == "SU26238"  # тикер брокера приоритетнее справочника
    assert (by_id[BOND_RUB]["broker_quantity"], by_id[BOND_RUB]["portfolio_quantity"]) == (10.0, 7.0)
    # у нас осталась бумага, которой у брокера уже нет
    assert (by_id[STOCK_USD]["broker_quantity"], by_id[STOCK_USD]["portfolio_quantity"]) == (0.0, 2.0)
    assert by_id[STOCK_USD]["ticker"] == "AAPL"


def test_reconcile_skips_currencies_and_zero_positions():
    rec = pis._reconcile_positions(
        {USD_ID: {"quantity": 150.0}, BOND_RUB: {"quantity": 0}},
        [],
        [{"asset_id": USD_ID, "quantity": 12}, {"asset_id": BOND_RUB, "quantity": 0}],
        ASSETS,
    )
    assert rec["checked"] == 0 and rec["mismatch_count"] == 0


def test_reconcile_unresolved_broker_position_is_mismatch():
    rec = pis._reconcile_positions(
        {}, [{"isin": "RU000UNKNOWN", "ticker": "XXX", "quantity": 5}], [], ASSETS,
    )
    assert rec["mismatch_count"] == 1
    m = rec["mismatches"][0]
    assert m["reason"] == "asset_not_found" and m["isin"] == "RU000UNKNOWN"
    assert (m["broker_quantity"], m["portfolio_quantity"]) == (5.0, 0.0)


def test_reconcile_report_is_capped_but_count_is_full():
    broker = {i: {"quantity": 1.0} for i in range(1000, 1100)}
    rec = pis._reconcile_positions(broker, [], [], {})
    assert rec["mismatch_count"] == 100
    assert len(rec["mismatches"]) == pis._RECONCILIATION_REPORT_LIMIT


def test_import_result_contains_reconciliation():
    data = {"Брокерский счёт": {
        "positions": [
            {"isin": "RU000ABOND01", "ticker": "BOND", "quantity": 12, "average_price": 1000},
            {"isin": "RU000UNKNOWN", "ticker": "XXX", "quantity": 1},
        ],
        "transactions": [BUY_BOND],
    }}
    result, _, upsert = _run_locked(
        data, portfolio_assets=[{"asset_id": BOND_RUB, "quantity": 10}],
    )
    rec = result["accounts"][0]["reconciliation"]
    assert rec["mismatch_count"] == 2
    assert result["mismatch_count"] == 2
    summary = upsert.call_args.kwargs["sync_summary"]
    assert summary["mismatch_count"] == 2


def test_import_without_positions_skips_reconciliation():
    result, _, _ = _run_locked(_broker_data(BUY_BOND) | {"Брокерский счёт": {"transactions": [BUY_BOND]}})
    assert result["accounts"][0]["reconciliation"] is None
    assert result["mismatch_count"] == 0


# ---------------------------------------------------------------------------
# Ручные правки переживают синхронизацию
# ---------------------------------------------------------------------------

def _account(account_id, *transactions, name="ИИС"):
    return {name: {"account_id": account_id, "positions": [], "transactions": list(transactions)}}


def _batch(m):
    return m.apply.call_args.args[0] if m.apply.await_count else []


def test_sync_clears_only_broker_rows_and_keeps_children():
    m = _run_import(_account("acc-1", BUY_BOND), children=[
        {"id": 42, "name": "Мой ИИС", "broker_account_id": "acc-1"},
    ])
    names = [name for name, _ in m.rpc_calls]
    assert names[0] == "clear_broker_portfolio_data"
    assert "clear_portfolio_full" not in names
    # прежний портфель счёта, а не новый; пользовательское название не трогаем
    m.insert.assert_not_called()
    m.update.assert_not_called()
    assert m.result["imported_portfolio_ids"] == [42]
    assert {op["portfolio_id"] for op in _batch(m)} == {42}


def test_legacy_child_is_bound_to_account_by_name():
    m = _run_import(_account("acc-1", BUY_BOND), children=[
        {"id": 42, "name": "ИИС", "broker_account_id": None},
    ])
    m.insert.assert_not_called()
    m.update.assert_awaited_once()
    assert m.update.call_args.args[:2] == ("portfolios", {"broker_account_id": "acc-1"})
    assert m.update.call_args.kwargs["filters"] == {"id": 42}


def test_new_account_gets_child_with_account_id():
    m = _run_import(_account("acc-2", BUY_BOND))
    row = m.insert.call_args.args[1]
    assert row["broker_account_id"] == "acc-2" and row["parent_portfolio_id"] == 100
    assert m.result["imported_portfolio_ids"] == [501]


def test_vanished_account_deleted_only_without_manual_rows():
    manual = [{"kind": "cash", "type": 5, "date": "2024-01-01T00:00:00", "asset_id": None, "amount": 1000}]
    m = _run_import(
        _account("acc-1", BUY_BOND),
        children=[
            {"id": 42, "name": "ИИС", "broker_account_id": "acc-1"},
            {"id": 43, "name": "Закрытый счёт", "broker_account_id": "acc-old"},
            {"id": 44, "name": "Мои заметки", "broker_account_id": None},
        ],
        kept_manual={"44": manual},
    )
    deleted = [params for name, params in m.rpc_calls if name == "clear_portfolio_full"]
    assert deleted == [{"p_portfolio_id": 43, "p_delete_self": True}]
    assert m.result["kept_manual_count"] == 1


def test_operation_deleted_by_user_is_not_reimported():
    dividend = {"type": "Dividend", "date": "2024-04-01T00:00:00", "isin": "RU000ABOND01",
                "payment": 120.0, "currency": "rub", "operation_id": "d-1"}
    buy = dict(BUY_BOND, operation_id="b-1")
    m = _run_import(
        _account("acc-1", buy, dividend),
        children=[{"id": 42, "name": "ИИС", "broker_account_id": "acc-1"}],
        suppressions={42: ["op:d-1"]},
    )
    batch = _batch(m)
    assert [op["operation_type"] for op in batch] == [OP_TYPES["buy"]]
    acc = m.result["accounts"][0]
    assert acc["suppressed_count"] == 1
    assert m.upsert.call_args.kwargs["sync_summary"]["suppressed_count"] == 1


def test_operation_already_added_manually_is_not_duplicated():
    dividend = {"type": "Dividend", "date": "2024-04-01T09:30:00", "isin": "RU000ABOND01",
                "payment": 120.0, "currency": "rub"}
    manual = [
        # та же покупка, время и цена чуть другие (ввод руками)
        {"kind": "tx", "type": 1, "date": "2024-03-01T00:00:00", "asset_id": BOND_RUB,
         "quantity": 10, "price": 1004.5},
        {"kind": "cash", "type": 3, "date": "2024-04-01T00:00:00", "asset_id": BOND_RUB, "amount": 120},
    ]
    m = _run_import(
        _account("acc-1", BUY_BOND, dividend),
        children=[{"id": 42, "name": "ИИС", "broker_account_id": "acc-1"}],
        kept_manual={"42": manual},
    )
    assert _batch(m) == []
    acc = m.result["accounts"][0]
    assert acc["matched_manual_count"] == 2 and acc["kept_manual_count"] == 2


def test_manual_row_closes_only_one_broker_operation():
    manual = [{"kind": "tx", "type": 1, "date": "2024-03-01T10:00:00", "asset_id": BOND_RUB,
               "quantity": 10, "price": 1000}]
    m = _run_import(
        _account("acc-1", BUY_BOND, dict(BUY_BOND)),
        children=[{"id": 42, "name": "ИИС", "broker_account_id": "acc-1"}],
        kept_manual={"42": manual},
    )
    assert len(_batch(m)) == 1
    assert m.result["accounts"][0]["matched_manual_count"] == 1


def test_manual_row_with_other_price_is_not_a_duplicate():
    manual = [{"kind": "tx", "type": 1, "date": "2024-03-01T10:00:00", "asset_id": BOND_RUB,
               "quantity": 10, "price": 950}]
    m = _run_import(
        _account("acc-1", BUY_BOND),
        children=[{"id": 42, "name": "ИИС", "broker_account_id": "acc-1"}],
        kept_manual={"42": manual},
    )
    assert len(_batch(m)) == 1


def test_batch_rows_are_marked_as_broker_with_external_id():
    buy = dict(BUY_BOND, operation_id="b-1")
    deposit = {"type": "Deposit", "date": "2024-02-01T00:00:00", "payment": 50000.0, "currency": "rub"}
    m = _run_import(_account("acc-1", buy, deposit))
    batch = _batch(m)
    assert {op["source"] for op in batch} == {"broker"}
    by_type = {op["operation_type"]: op for op in batch}
    assert by_type[OP_TYPES["buy"]]["external_id"] == "op:b-1"
    assert by_type[OP_TYPES["deposit"]]["external_id"].startswith("fp:")


def test_external_ids_are_stable_and_unique():
    a = {"type": "Deposit", "date": "2024-02-01T00:00:00", "payment": 100.0, "currency": "rub"}
    ids = pis._broker_external_ids([a, dict(a), dict(a, payment=200.0), dict(BUY_BOND, operation_id=7)])
    assert len(set(ids)) == 4
    assert ids[1] == ids[0] + "#1"
    assert ids[3] == "op:7"
    # одинаковые данные — одинаковые id в следующей синхронизации (100 и 100.0 не различаем)
    assert pis._broker_external_ids([dict(a, payment=100)]) == ids[:1]


def test_bks_trade_number_is_operation_id():
    from app.infrastructure.external.brokers.bks import import_service as bks
    tx = bks._normalize_trade_to_transaction(
        {"direction": "BUY", "tradeNum": 123456, "isin": "RU000ABOND01", "quantity": 1, "price": 10},
    )
    assert tx["operation_id"] == "123456"
    no_id = bks._normalize_trade_to_transaction(
        {"direction": "SELL", "isin": "RU000ABOND01", "quantity": 1, "price": 10},
    )
    assert no_id["operation_id"] is None


# ---------------------------------------------------------------------------
# Перевод бумаг от другого брокера: себестоимость
# ---------------------------------------------------------------------------

TRANSFER_IN = {"type": "Buy", "transfer": "in", "date": "2024-03-01T10:00:00", "isin": "RU000ABOND01",
               "price": 0.0, "quantity": 10, "payment": 0.0, "currency": "rub", "operation_id": "t-in"}
TRANSFER_OUT = {"type": "Sell", "transfer": "out", "date": "2024-04-01T10:00:00", "isin": "RU000ABOND01",
                "price": 0.0, "quantity": 12, "payment": 0.0, "currency": "rub", "operation_id": "t-out"}


def _with_position(data, average_price, quantity=10):
    acc = next(iter(data.values()))
    acc["positions"] = [{"isin": "RU000ABOND01", "ticker": "BOND", "quantity": quantity,
                         "average_price": average_price, "current_price": average_price}]
    return data


def _ops(m, op_type):
    return [op for op in _batch(m) if op["operation_type"] == OP_TYPES[op_type]]


def test_transfer_in_takes_broker_average_price():
    m = _run_import(_with_position(_account("acc-1", TRANSFER_IN), 987.5))
    [buy] = _ops(m, "buy")
    assert buy["price"] == 987.5
    assert buy["payment"] == 0  # перевод — не покупка: деньги со счёта не списываются
    [t] = m.result["accounts"][0]["transfers"]
    assert t["direction"] == "in" and t["price_source"] == "broker_average" and t["quantity"] == 10
    assert m.upsert.call_args.kwargs["sync_summary"]["transfer_count"] == 1


def test_transfer_in_without_broker_price_uses_market_price():
    m = _run_import(_account("acc-1", TRANSFER_IN), market_price=1012.3)
    assert _ops(m, "buy")[0]["price"] == 1012.3
    assert m.result["accounts"][0]["transfers"][0]["price_source"] == "market"


def test_transfer_in_with_unknown_price_is_flagged():
    # и без пометки брокера: «покупка» без цены и денег — тоже перевод
    tx = {k: v for k, v in TRANSFER_IN.items() if k != "transfer"}
    m = _run_import(_with_position(_account("acc-1", tx), 0.0))
    assert _ops(m, "buy")[0]["price"] == 0
    assert m.result["accounts"][0]["transfers"][0]["price_source"] == "unknown"


def test_transfer_with_broker_price_is_kept_as_is():
    tx = dict(TRANSFER_IN, price=1500.0)
    m = _run_import(_with_position(_account("acc-1", tx), 987.5))
    assert _ops(m, "buy")[0]["price"] == 1500.0
    assert m.result["accounts"][0]["transfers"] == []


def test_transfer_out_is_priced_by_fifo_lots():
    buy2 = dict(BUY_BOND, date="2024-03-05T10:00:00", price=1100.0, quantity=5, payment=-5500.0)
    m = _run_import(_account("acc-1", BUY_BOND, buy2, TRANSFER_OUT))
    [sell] = _ops(m, "sell")
    # FIFO спишет 10 по 1000 и 2 по 1100 — без фиктивного убытка
    assert sell["price"] == round((10 * 1000 + 2 * 1100) / 12, 6)
    assert m.result["accounts"][0]["transfers"][0]["price_source"] == "fifo"


def test_transfer_out_counts_manual_lots():
    manual = [{"kind": "tx", "type": 1, "date": "2024-01-10T00:00:00", "asset_id": BOND_RUB,
               "quantity": 12, "price": 900}]
    m = _run_import(
        _account("acc-1", TRANSFER_OUT),
        children=[{"id": 42, "name": "ИИС", "broker_account_id": "acc-1"}],
        kept_manual={"42": manual},
    )
    assert _ops(m, "sell")[0]["price"] == 900


def test_transfer_in_matches_manual_lot_regardless_of_price():
    manual = [{"kind": "tx", "type": 1, "date": "2024-03-01T00:00:00", "asset_id": BOND_RUB,
               "quantity": 10, "price": 750}]
    m = _run_import(
        _with_position(_account("acc-1", TRANSFER_IN), 987.5),
        children=[{"id": 42, "name": "ИИС", "broker_account_id": "acc-1"}],
        kept_manual={"42": manual},
    )
    # пользователь уже завёл переведённые бумаги со своей ценой — не дублируем
    assert _batch(m) == []
    assert m.result["accounts"][0]["matched_manual_count"] == 1


def test_fifo_cost_price_edge_cases():
    ev = [("2024-01-01T00:00:00", 1, 5, 100.0), ("2024-02-01T00:00:00", 2, 3, 0.0),
          ("2024-03-01T00:00:00", 1, 5, 200.0), ("2024-09-01T00:00:00", 1, 5, 999.0)]
    # после продажи 3 остались 2 по 100 и 5 по 200; лот сентября позже даты вывода
    assert pis._fifo_cost_price(ev, "2024-06-01T00:00:00", 4) == round((2 * 100 + 2 * 200) / 4, 6)
    assert pis._fifo_cost_price(ev, "2023-12-01T00:00:00", 4) is None


def test_import_runs_inside_one_transaction_with_lock():
    conn = MagicMock()
    conn.execute = AsyncMock()
    conn.fetchval = AsyncMock(return_value="user-1")

    class FakeTx:
        async def __aenter__(self):
            return conn

        async def __aexit__(self, *exc):
            return False

    with patch.object(pis, "get_user_by_email", AsyncMock(return_value={"id": "user-1"})), \
         patch.object(pis, "db_transaction", MagicMock(return_value=FakeTx())), \
         patch.object(pis, "_import_broker_portfolio_locked", AsyncMock(return_value={"success": True})) as locked:
        run(pis.import_broker_portfolio("u@example.test", 100, _broker_data(BUY_BOND), broker_id=1))
    assert "pg_advisory_xact_lock" in conn.execute.call_args.args[0]
    locked.assert_awaited_once()


def test_import_into_foreign_portfolio_is_refused():
    conn = MagicMock()
    conn.execute = AsyncMock()
    conn.fetchval = AsyncMock(return_value="someone-else")

    class FakeTx:
        async def __aenter__(self):
            return conn

        async def __aexit__(self, *exc):
            return False

    with patch.object(pis, "get_user_by_email", AsyncMock(return_value={"id": "user-1"})), \
         patch.object(pis, "db_transaction", MagicMock(return_value=FakeTx())), \
         patch.object(pis, "_import_broker_portfolio_locked", AsyncMock()) as locked:
        with pytest.raises(ValueError):
            run(pis.import_broker_portfolio("u@example.test", 100, _broker_data(BUY_BOND), broker_id=1))
    locked.assert_not_called()


# ---------------------------------------------------------------------------
# Задачи импорта и выбор портфеля
# ---------------------------------------------------------------------------

def test_second_import_request_returns_active_task():
    active = {"id": 77, "status": "processing", "portfolio_id": 5}
    with patch.object(task_service._portfolio_repository, "get_by_id", AsyncMock(return_value={"user_id": "u1"})), \
         patch.object(task_service, "table_select_async", AsyncMock(return_value=[active])), \
         patch.object(task_service, "table_insert_async", AsyncMock()) as insert:
        task = run(task_service.create_import_task("u1", 1, "t", 5))
    assert task["id"] == 77 and task["already_active"] is True
    insert.assert_not_called()


def test_import_request_creates_task_when_none_active():
    with patch.object(task_service._portfolio_repository, "get_by_id", AsyncMock(return_value={"user_id": "u1"})), \
         patch.object(task_service, "table_select_async", AsyncMock(return_value=[])), \
         patch.object(task_service, "table_insert_async", AsyncMock(return_value=[{"id": 78, "status": "pending"}])):
        task = run(task_service.create_import_task("u1", 1, "t", 5))
    assert task["id"] == 78 and "already_active" not in task


def _ensure_portfolio(existing_by_name, reusable):
    async def find(parent_id, name):
        return existing_by_name.get(name)

    with patch.object(portfolio_service, "get_user_portfolio_parent", AsyncMock(return_value={"id": 1})), \
         patch.object(portfolio_service._portfolio_repository, "find_by_parent_and_name", AsyncMock(side_effect=find)), \
         patch.object(portfolio_service, "_portfolio_reusable_for_broker_import", AsyncMock(side_effect=reusable)), \
         patch.object(portfolio_service, "table_insert_async", AsyncMock(return_value=[{"id": 42}])) as insert:
        pid = run(portfolio_service.ensure_portfolio_for_broker_import("u1", "u@example.test", 1, "Мой портфель"))
    return pid, insert


def test_manual_portfolio_with_same_name_is_not_overwritten():
    pid, insert = _ensure_portfolio({"Мой портфель": {"id": 10}}, reusable=lambda pid, broker: False)
    assert pid == 42
    assert insert.call_args.args[1]["name"] == "Мой портфель (2)"


def test_empty_portfolio_with_same_name_is_reused():
    pid, insert = _ensure_portfolio({"Мой портфель": {"id": 10}}, reusable=lambda pid, broker: True)
    assert pid == 10
    insert.assert_not_called()
