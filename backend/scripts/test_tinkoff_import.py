"""
Скрипт для ручного тестирования импорта портфелей от Tinkoff.

Использование:
    python scripts/test_tinkoff_import.py --token YOUR_TOKEN   # токен в аргументе (или -t)
    python scripts/test_tinkoff_import.py                      # токен из TINKOFF_TOKEN
    python scripts/test_tinkoff_import.py --account-index 1  # только счёт №1 (сортировка имён по алфавиту)
    python scripts/test_tinkoff_import.py --account ИИС      # счета, в имени которых есть подстрока
    python scripts/test_tinkoff_import.py --interactive      # меню + полный отчёт
    python scripts/test_tinkoff_import.py --raw-ticker SBER --account-index 1   # сырые операции API по тикеру и счёту
    python scripts/test_tinkoff_import.py --raw-ticker GAZP --raw-only -t TOKEN  # только блок сырых операций
    python scripts/test_tinkoff_import.py --gui   # окно: аналитика + сырые операции с фильтрами

Токен: аргумент --token / -t или переменная окружения TINKOFF_TOKEN (приоритет у аргумента).
"""
import argparse
import io
import json
import os
import sys
import threading
from contextlib import redirect_stdout
from pathlib import Path
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.external.brokers.tinkoff import get_tinkoff_portfolio
from app.infrastructure.external.brokers.tinkoff.import_service import (
    OPERATION_CLASSIFICATION,
    classify_tinkoff_operation,
)


def _fmt_currency(c: Any) -> str:
    if c is None:
        return ""
    if hasattr(c, "name"):
        return str(c.name)
    return str(c)


def filter_broker_accounts(
    broker_data: dict,
    account_substr: Optional[str] = None,
    account_index: Optional[int] = None,
) -> Tuple[dict, Optional[str]]:
    """Фильтр по счетам брокера: подстрока в имени или 1-based индекс в отсортированном списке имён."""
    if not broker_data:
        return broker_data, None
    names = sorted(broker_data.keys())
    if account_index is not None:
        i = account_index - 1
        if 0 <= i < len(names):
            k = names[i]
            return {k: broker_data[k]}, None
        return broker_data, (
            f"account-index {account_index} вне диапазона (счетов: {len(names)})"
        )
    if account_substr:
        s = account_substr.lower().strip()
        matched = {k: v for k, v in broker_data.items() if s in k.lower()}
        if matched:
            return matched, None
        return broker_data, f"Подстрока «{account_substr}» не найдена в именах счетов — показаны все"
    return broker_data, None


def print_table(headers: Sequence[str], rows: Sequence[Sequence[Any]], min_col_width: int = 8) -> None:
    """Простая текстовая таблица с выравниванием по ширине столбцов."""
    str_rows = [[("" if c is None else str(c)) for c in row] for row in rows]
    widths = [len(h) for h in headers]
    for row in str_rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell), min_col_width)
    sep = " | "

    def fmt_row(cells: Sequence[str]) -> str:
        return sep.join(c.ljust(widths[i]) for i, c in enumerate(cells))

    print(fmt_row(list(headers)))
    print(sep.join("-" * w for w in widths))
    for row in str_rows:
        padded = list(row) + [""] * (len(headers) - len(row))
        print(fmt_row(padded[: len(headers)]))


def _currency_key_from_position(pos: dict) -> Optional[str]:
    ticker = (pos.get("ticker") or "").upper()
    name = (pos.get("name") or "").lower()
    if ticker.startswith("RUB") or ticker.startswith("RUR") or "рубль" in name:
        return "rub"
    if ticker.startswith("USD") or "доллар" in name:
        return "usd"
    if ticker.startswith("EUR") or "евро" in name:
        return "eur"
    if ticker.startswith("CNY") or "юань" in name:
        return "cny"
    if ticker.startswith("GBP"):
        return "gbp"
    if ticker.startswith("HKD"):
        return "hkd"
    if len(ticker) >= 8 and ticker[:3].isalpha():
        return ticker[:3].lower()
    return None


def _sum_payments_by_currency(transactions: List[dict]) -> Dict[str, float]:
    by_curr: Dict[str, float] = defaultdict(float)
    for tx in transactions:
        raw = tx.get("currency")
        if raw is None and tx.get("type") in ("Buy", "Sell", "Amortization"):
            c = "rub"
        else:
            c = raw or "rub"
        c = _fmt_currency(c).lower().strip() or "rub"
        by_curr[c] += float(tx.get("payment") or 0)
    return dict(by_curr)


def _cash_balances_from_positions(positions: List[dict]) -> Dict[str, float]:
    out: Dict[str, float] = defaultdict(float)
    for pos in positions:
        key = _currency_key_from_position(pos)
        if key:
            out[key] += float(pos.get("quantity") or 0)
    return dict(out)


def _iter_transactions(broker_data: dict) -> List[dict]:
    all_tx: List[dict] = []
    for account_name, account_data in broker_data.items():
        for tx in account_data.get("transactions", []):
            t = dict(tx)
            t["account_name"] = account_name
            all_tx.append(t)
    return all_tx


def _skipped_qty_equals_rest(entry: dict) -> bool:
    """True, если quantity_api совпадает с quantity_rest (заявка целиком не исполнена)."""
    qa = entry.get("quantity_api")
    qr = entry.get("quantity_rest")
    if qa is None or qr is None:
        return False
    try:
        return abs(float(qa) - float(qr)) < 1e-9
    except (TypeError, ValueError):
        return False


def _raw_op_qty_equals_rest(op: dict) -> bool:
    """Сырые операции API: quantity и quantity_rest в корне словаря (как в tinkoff_operation_to_raw_dict)."""
    qa = op.get("quantity")
    qr = op.get("quantity_rest")
    if qa is None or qr is None:
        return False
    try:
        return abs(float(qa) - float(qr)) < 1e-9
    except (TypeError, ValueError):
        return False


def emit_full_statistics(
    broker_data: dict,
    account_substr: Optional[str] = None,
    account_index: Optional[int] = None,
) -> None:
    """Таблицы: балансы, счётчики API/выгрузка, пропущенные и синтетические операции, типы, Other."""
    filtered, warn = filter_broker_accounts(broker_data, account_substr, account_index)

    print("\n" + "=" * 100)
    print("СВОДКА ПО СЧЕТАМ (брокер)")
    print("=" * 100)
    if warn:
        print(f"⚠️  {warn}")
    summary_rows = []
    for acc_name, acc in filtered.items():
        raw_c = acc.get("operations_raw_count")
        if raw_c is None:
            raw_c = "—"
        n_skip = len(acc.get("transactions_skipped") or [])
        n_tx = len(acc.get("transactions", []))
        n_api = int(acc.get("operations_raw_count") or 0)
        summary_rows.append([
            acc_name[:28],
            str(acc.get("account_id", ""))[:36],
            len(acc.get("positions", [])),
            n_tx,
            raw_c,
            n_skip,
            n_tx - n_api,
        ])
    print_table(
        ["Счёт", "account_id", "Позиций", "В выгрузке", "В API", "Пропущено", "Δ выг−API"],
        summary_rows,
    )

    print("\n" + "=" * 100)
    print("БАЛАНС: ПОЗИЦИИ (брокер) vs СУММА payment ПО ОПЕРАЦИЯМ")
    print("=" * 100)
    balance_rows = []
    for acc_name, acc in filtered.items():
        positions = acc.get("positions", [])
        txs = acc.get("transactions", [])
        pos_cash = _cash_balances_from_positions(positions)
        pay_by = _sum_payments_by_currency(txs)
        all_curr = sorted(set(pos_cash.keys()) | set(pay_by.keys()))
        if not all_curr:
            all_curr = ["rub"]
        for curr in all_curr:
            p_bal = pos_cash.get(curr, 0.0)
            o_bal = pay_by.get(curr, 0.0)
            diff = p_bal - o_bal
            ok = abs(diff) < 0.02
            balance_rows.append([
                acc_name[:20],
                curr.upper(),
                f"{p_bal:,.2f}",
                f"{o_bal:,.2f}",
                f"{diff:+,.2f}",
                "✓" if ok else "≠",
            ])
    print_table(
        ["Счёт", "Валюта", "Позиция (кэш)", "Σ payment опер.", "Δ (поз − опер.)", ""],
        balance_rows,
    )

    all_tx = _iter_transactions(filtered)
    print("\n" + "=" * 100)
    print("ОПЕРАЦИИ ПО КЛАССУ (type после classify)")
    print("=" * 100)
    by_type = Counter(tx.get("type") or "—" for tx in all_tx)
    type_rows = []
    for t, c in by_type.most_common():
        pay_sum = sum(float(x.get("payment") or 0) for x in all_tx if (x.get("type") or "—") == t)
        type_rows.append([t, c, f"{pay_sum:,.2f}"])
    print_table(["type", "шт.", "Σ payment"], type_rows)

    print("\n" + "=" * 100)
    print("СЫРОЙ ТИП TINKOFF → КЛАСС (частоты)")
    print("=" * 100)
    raw_to_class_rows = []
    raw_counter: Counter = Counter()
    for tx in all_tx:
        raw = tx.get("tinkoff_operation_type") or "—"
        raw_counter[raw] += 1
    for raw_name, cnt in raw_counter.most_common():
        if str(raw_name).startswith("SYNTHETIC"):
            internal = "Withdraw (синт.)"
        elif raw_name == "—":
            internal = "—"
        else:
            internal = classify_tinkoff_operation(raw_name)
        raw_to_class_rows.append([raw_name[:45], internal, cnt])
    print_table(["tinkoff_operation_type", "→ класс", "шт."], raw_to_class_rows)

    raw_exported = sum(len(a.get("transactions", [])) for a in filtered.values())
    raw_api = sum(int(a.get("operations_raw_count") or 0) for a in filtered.values())
    print("\n" + "=" * 100)
    print("СЧЁТЧИКИ ОПЕРАЦИЙ: API vs ВЫГРУЗКА")
    print("=" * 100)
    print_table(
        ["Метрика", "Значение", "Комментарий"],
        [
            ["Сырых операций в API (Σ по счетам)", raw_api, "ответ get_operations"],
            ["Записей в transactions после обработки", raw_exported, "вкл. синтетику DIV_EXT"],
            ["Разница (выгрузка − API)", raw_exported - raw_api, "< 0: пропуски; > 0: синтетика"],
        ],
    )

    # Пропущенные при импорте (не попали в transactions) — при выгрузке < API обязательны; показываем всегда, если есть
    for acc_name, acc in filtered.items():
        n_api = int(acc.get("operations_raw_count") or 0)
        n_exp = len(acc.get("transactions", []))
        skipped = acc.get("transactions_skipped") or []
        if not skipped:
            if n_api > n_exp:
                print("\n" + "=" * 100)
                print(
                    f"⚠️  Счёт «{acc_name}»: в API {n_api} операций, в выгрузке {n_exp}, "
                    "но transactions_skipped пуст (нужен актуальный import_service с записью пропусков)."
                )
                print("=" * 100)
            continue
        hint = ""
        if n_api > n_exp:
            hint = f" (API {n_api} > выгрузка {n_exp}: не хватает {n_api - n_exp} относительно «сырых»)"
        skipped_eq_rest = [s for s in skipped if _skipped_qty_equals_rest(s)]
        skipped_detail = [s for s in skipped if not _skipped_qty_equals_rest(s)]

        print("\n" + "=" * 100)
        print(f"НЕ В ВЫГРУЗКЕ — пропущенные операции: счёт «{acc_name}» ({len(skipped)} шт.){hint}")
        print("=" * 100)
        if skipped_eq_rest:
            print(
                f"Операций с qty = qty_rest (неисполненные заявки, только количество): {len(skipped_eq_rest)} шт."
            )
        if skipped_detail:
            rows = []
            for s in sorted(skipped_detail, key=lambda x: (x.get("date") or ""), reverse=True):
                rows.append([
                    (s.get("date") or "")[:19],
                    (s.get("tinkoff_operation_type") or "")[:36],
                    s.get("type"),
                    s.get("reason"),
                    (s.get("ticker") or "—")[:10],
                    f"{float(s.get('payment') or 0):,.2f}",
                    _fmt_currency(s.get("currency"))[:8],
                    str(s.get("quantity_api")),
                    str(s.get("quantity_rest")),
                ])
            print_table(
                ["Дата", "tinkoff_operation_type", "class", "reason", "Тикер", "payment", "cur.", "qty", "qty_rest"],
                rows,
            )

    # Синтетические строки (DIV_EXT → Withdraw и т.п.) — при выгрузке > API; показываем всегда, если есть
    for acc_name, acc in filtered.items():
        n_api = int(acc.get("operations_raw_count") or 0)
        n_exp = len(acc.get("transactions", []))
        synthetic = [
            tx for tx in acc.get("transactions", [])
            if str(tx.get("tinkoff_operation_type") or "").startswith("SYNTHETIC")
        ]
        if not synthetic:
            if n_exp > n_api:
                print("\n" + "=" * 100)
                print(
                    f"⚠️  Счёт «{acc_name}»: выгрузка {n_exp} > API {n_api}, "
                    "но синтетических строк (SYNTHETIC*) нет — проверьте логику импорта."
                )
                print("=" * 100)
            continue
        hint = ""
        if n_exp > n_api:
            hint = f" (выгрузка {n_exp} > API {n_api}: лишних {n_exp - n_api} относительно «сырых»)"
        print("\n" + "=" * 100)
        print(f"ДОБАВЛЕНО В ВЫГРУЗКУ — синтетические операции: счёт «{acc_name}» ({len(synthetic)} шт.){hint}")
        print("=" * 100)
        rows = []
        for tx in sorted(synthetic, key=lambda x: (x.get("date") or ""), reverse=True):
            rows.append([
                (tx.get("date") or "")[:19],
                (tx.get("tinkoff_operation_type") or "")[:28],
                tx.get("type"),
                f"{float(tx.get('payment') or 0):,.2f}",
                _fmt_currency(tx.get("currency"))[:8],
            ])
        print_table(
            ["Дата", "tinkoff_operation_type", "type", "payment", "currency"],
            rows,
        )

    other_tx = [tx for tx in all_tx if (tx.get("type") == "Other")]
    print("\n" + "=" * 100)
    print(f"ОПЕРАЦИИ С type=Other ({len(other_tx)} шт.)")
    print("=" * 100)
    if not other_tx:
        print("(нет)")
    else:
        other_sorted = sorted(other_tx, key=lambda x: (x.get("date") or ""), reverse=True)
        other_rows = []
        for tx in other_sorted:
            other_rows.append([
                (tx.get("date") or "")[:19],
                (tx.get("account_name") or "")[:14],
                (tx.get("tinkoff_operation_type") or "")[:32],
                (tx.get("ticker") or "—")[:10],
                f"{float(tx.get('payment') or 0):,.2f}",
                _fmt_currency(tx.get("currency"))[:8],
            ])
        print_table(
            ["Дата", "Счёт", "tinkoff_operation_type", "Тикер", "payment", "currency"],
            other_rows,
        )

    unmapped_raw = [
        tx.get("tinkoff_operation_type")
        for tx in all_tx
        if tx.get("tinkoff_operation_type")
        and tx.get("tinkoff_operation_type") not in OPERATION_CLASSIFICATION
        and not str(tx.get("tinkoff_operation_type", "")).startswith("SYNTHETIC")
    ]
    if unmapped_raw:
        print("\n" + "=" * 100)
        print("НОВЫЕ ТИПЫ API (нет в OPERATION_CLASSIFICATION → класс Other)")
        print("=" * 100)
        uc = Counter(unmapped_raw)
        print_table(["tinkoff_operation_type", "шт."], [[k[:50], v] for k, v in uc.most_common()])

    print("\n" + "=" * 100)
    print("ПРОВЕРКА payment (Buy/Sell/Amortization)")
    print("=" * 100)
    bad_pay = []
    for tx in all_tx:
        if tx.get("type") not in ("Buy", "Sell", "Amortization"):
            continue
        if tx.get("payment") is None:
            bad_pay.append((tx, "нет payment"))
        elif float(tx.get("payment") or 0) == 0 and tx.get("type") != "Amortization":
            bad_pay.append((tx, "payment=0"))
    if not bad_pay:
        print("Подозрительных записей не найдено.")
    else:
        br = []
        for tx, reason in bad_pay[:50]:
            br.append([
                reason,
                (tx.get("date") or "")[:16],
                tx.get("type"),
                tx.get("ticker"),
            ])
        print_table(["Проблема", "Дата", "type", "ticker"], br)
        if len(bad_pay) > 50:
            print(f"... ещё {len(bad_pay) - 50}")

    dates = [tx.get("date") for tx in all_tx if tx.get("date")]
    if dates:
        print("\n" + "=" * 100)
        print("ДИАПАЗОН ДАТ В ВЫГРУЗКЕ")
        print("=" * 100)
        print_table(
            ["Минимум", "Максимум", "Всего операций"],
            [[min(dates)[:10], max(dates)[:10], len(dates)]],
        )


def format_full_statistics(
    broker_data: dict,
    account_substr: Optional[str] = None,
    account_index: Optional[int] = None,
) -> str:
    """Текст полной сводки (как emit_full_statistics), для вывода в GUI."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        emit_full_statistics(broker_data, account_substr, account_index)
    return buf.getvalue()


def show_balance_analysis(broker_data: dict, account_substr: Optional[str] = None, account_index: Optional[int] = None):
    """Анализ балансов RUB по данным брокера."""
    print("\n" + "=" * 80)
    print("АНАЛИЗ БАЛАНСОВ")
    print("=" * 80)

    filtered_broker_data, warn = filter_broker_accounts(broker_data, account_substr, account_index)
    if warn:
        print(f"\n⚠️  {warn}")

    for account_name, account_data in filtered_broker_data.items():
        positions = account_data.get("positions", [])
        transactions = account_data.get("transactions", [])

        print(f"\n📁 Счёт: {account_name}")

        balance_from_operations = 0.0
        for tx in transactions:
            payment = tx.get("payment", 0)
            currency = _fmt_currency(tx.get("currency", "rub")).lower()
            if currency and currency not in ("rub", "rur", "руб"):
                continue
            balance_from_operations += float(payment)

        print(f"💰 Баланс из операций: {balance_from_operations:,.2f} RUB")

        balance_from_positions = 0.0
        for pos in positions:
            ticker = (pos.get("ticker") or "").upper()
            name = (pos.get("name") or "").lower()
            if (ticker.startswith("RUB") or ticker.startswith("RUR")) or "рубль" in name:
                balance_from_positions = float(pos.get("quantity", 0))
                break

        if balance_from_positions > 0:
            print(f"💰 Баланс из позиций: {balance_from_positions:,.2f} RUB")
            diff = abs(balance_from_operations - balance_from_positions)
            if diff < 0.01:
                print("   ✅ Балансы совпадают")
            else:
                print(f"   ❌ Расхождение: {diff:,.2f} RUB")
        else:
            print("   ⚠️  Позиция RUB не найдена")


def show_positions_broker_only(broker_data: dict, account_substr: Optional[str] = None, account_index: Optional[int] = None):
    """Позиции от брокера (без БД)."""
    print("\n" + "=" * 80)
    print("ПОЗИЦИИ ОТ БРОКЕРА")
    print("=" * 80)

    filtered_broker_data, warn = filter_broker_accounts(broker_data, account_substr, account_index)
    if warn:
        print(f"\n⚠️  {warn}")

    broker_positions = {}
    for account_name, account_data in filtered_broker_data.items():
        for pos in account_data.get("positions", []):
            ticker = (pos.get("ticker") or "").upper()
            name = (pos.get("name") or "").lower()
            if (ticker.startswith("RUB") or ticker.startswith("RUR")) or "рубль" in name:
                continue

            if ticker not in broker_positions:
                broker_positions[ticker] = {
                    "name": pos.get("name", "N/A"),
                    "quantity": float(pos.get("quantity", 0)),
                    "current_price": float(pos.get("current_price", 0)),
                    "value": float(pos.get("quantity", 0)) * float(pos.get("current_price", 0)),
                }
            else:
                broker_positions[ticker]["quantity"] += float(pos.get("quantity", 0))
                broker_positions[ticker]["value"] += float(pos.get("quantity", 0)) * float(pos.get("current_price", 0))

    print(f"\n📊 Позиций (без валютных остатков): {len(broker_positions)}")
    print(f"\n{'Тикер':<15} | {'Название':<35} | {'Количество':>12} | {'Цена':>12} | {'Стоимость':>15}")
    print("-" * 95)
    for ticker, pos in sorted(broker_positions.items()):
        print(
            f"{ticker:<15} | {pos['name'][:35]:<35} | {pos['quantity']:>12.2f} | "
            f"{pos['current_price']:>12.2f} | {pos['value']:>15,.2f}"
        )


def show_operations(
    broker_data: dict,
    account_substr: Optional[str] = None,
    account_index: Optional[int] = None,
    limit: Optional[int] = 10,
):
    """Операции от брокера."""
    print("\n" + "=" * 80)
    print("ОПЕРАЦИИ ОТ БРОКЕРА")
    print("=" * 80)

    filtered_broker_data, warn = filter_broker_accounts(broker_data, account_substr, account_index)
    if warn:
        print(f"\n⚠️  {warn}")

    all_transactions = []
    for account_name, account_data in filtered_broker_data.items():
        for tx in account_data.get("transactions", []):
            tx_with_account = tx.copy()
            tx_with_account["account_name"] = account_name
            all_transactions.append(tx_with_account)

    all_transactions.sort(key=lambda x: x.get("date", ""), reverse=True)

    one_account = len(filtered_broker_data) == 1
    transactions_to_show = (
        all_transactions if (one_account and limit is None) else (all_transactions[:limit] if limit else all_transactions)
    )

    print(f"\n📋 Показано операций: {len(transactions_to_show)} из {len(all_transactions)}")
    print(f"\n{'Дата':<20} | {'Счёт':<20} | {'Тип':<15} | {'Тикер':<15} | {'Цена':>12} | {'Количество':>12} | {'Сумма':>15}")
    print("-" * 125)

    for tx in transactions_to_show:
        date_str = tx.get("date", "N/A")[:19] if tx.get("date") else "N/A"
        account = (tx.get("account_name", "N/A") or "N/A")[:20]
        tx_type = tx.get("type", "N/A")[:15]
        ticker = (tx.get("ticker") or "—")[:15]
        price = tx.get("price")
        price_str = f"{price:>12,.2f}" if price is not None else f"{'—':>12}"
        quantity = tx.get("quantity")
        qty_str = f"{quantity:>10.2f} шт." if quantity is not None else f"{'':>12}"
        payment = tx.get("payment", 0)
        payment_str = f"{payment:>15,.2f}"

        print(f"{date_str:<20} | {account:<20} | {tx_type:<15} | {ticker:<15} | {price_str:>12} | {qty_str:>12} | {payment_str:>15}")


def show_raw_operations_for_ticker(
    broker_data: dict,
    ticker: str,
    account_substr: Optional[str] = None,
    account_index: Optional[int] = None,
) -> None:
    """Сырые операции get_operations (сериализация полей API), отфильтрованные по тикеру и счёту."""
    filtered, warn = filter_broker_accounts(broker_data, account_substr, account_index)
    t = ticker.strip().upper()
    print("\n" + "=" * 100)
    print(f"СЫРЫЕ ОПЕРАЦИИ API (get_operations), тикер {t!r}")
    print("=" * 100)
    if warn:
        print(f"⚠️  {warn}")

    any_raw = False
    any_match = False
    for acc_name, acc in filtered.items():
        raw_list = acc.get("operations_raw")
        if raw_list is None:
            print(
                f"\n⚠️  Счёт «{acc_name}»: нет operations_raw — запустите скрипт с флагом --raw-ticker "
                "(данные запрашиваются при его наличии)."
            )
            continue
        any_raw = True
        matched = [r for r in raw_list if (r.get("ticker") or "").upper() == t]
        print(f"\n—— Счёт «{acc_name}» (account_id={acc.get('account_id')}) ——")
        print(f"    по тикеру {t!r}: {len(matched)} из {len(raw_list)} сырых операций на счёте")
        if not matched:
            continue
        any_match = True
        for i, r in enumerate(sorted(matched, key=lambda x: x.get("date") or "", reverse=True), 1):
            print(f"\n--- #{i} ---")
            print(json.dumps(r, ensure_ascii=False, indent=2))

    if any_raw and not any_match:
        print(f"\nОпераций с тикером {t!r} среди выбранных счетов не найдено.")


def _payment_raw_display(op: dict) -> str:
    p = op.get("payment")
    if p is None:
        return ""
    if isinstance(p, dict):
        u = int(p.get("units") or 0)
        n = int(p.get("nano") or 0)
        cur = p.get("currency") or ""
        val = float(u) + float(n) / 1e9
        return f"{val:,.4f} {cur}".strip()
    return str(p)


def run_gui(initial_token: str = "") -> None:
    """Двухпанельное окно: аналитика и сырые операции (обязательно без qty = qty_rest)."""
    import tkinter as tk
    from tkinter import messagebox, scrolledtext, ttk

    ALL_ACCOUNTS = "Все счета"

    class TinkoffImportGui:
        def __init__(self, root: tk.Tk, token_hint: str) -> None:
            self.root = root
            self.root.title("Tinkoff import — аналитика и сырые операции")
            self.root.minsize(1080, 660)
            self.broker_data: Optional[dict] = None
            self._row_ops: Dict[str, dict] = {}
            self._row_i = 0

            main = ttk.Frame(self.root, padding=6)
            main.pack(fill=tk.BOTH, expand=True)

            top = ttk.Frame(main)
            top.pack(fill=tk.X, pady=(0, 6))

            ttk.Label(top, text="Токен:").pack(side=tk.LEFT)
            hint = (token_hint or "").strip() or (os.getenv("TINKOFF_TOKEN") or "")
            self.token_var = tk.StringVar(value=hint)
            ttk.Entry(top, textvariable=self.token_var, width=44, show="*").pack(
                side=tk.LEFT, padx=6, fill=tk.X, expand=True
            )
            self.btn_load = ttk.Button(top, text="Загрузить с API", command=self.on_load)
            self.btn_load.pack(side=tk.LEFT)

            paned = ttk.Panedwindow(main, orient=tk.HORIZONTAL)
            paned.pack(fill=tk.BOTH, expand=True)

            left = ttk.Frame(paned, padding=2)
            paned.add(left, weight=5)
            ttk.Label(left, text="Аналитика").pack(anchor=tk.W)
            self.txt_analytics = scrolledtext.ScrolledText(left, wrap=tk.WORD, font=("Consolas", 9))
            self.txt_analytics.pack(fill=tk.BOTH, expand=True)
            self.txt_analytics.insert(tk.END, "Нажмите «Загрузить с API». Запрашиваются позиции, выгрузка и сырые операции.\n")

            right = ttk.Frame(paned, padding=2)
            paned.add(right, weight=4)

            filt = ttk.LabelFrame(right, text="Сырые операции (фильтры)", padding=8)
            filt.pack(fill=tk.X)

            r1 = ttk.Frame(filt)
            r1.pack(fill=tk.X)
            ttk.Label(r1, text="Счёт:").pack(side=tk.LEFT)
            self.account_var = tk.StringVar(value=ALL_ACCOUNTS)
            self.combo_acc = ttk.Combobox(r1, textvariable=self.account_var, width=32, state="readonly")
            self.combo_acc.pack(side=tk.LEFT, padx=6)
            self.combo_acc.bind("<<ComboboxSelected>>", lambda _e: self.refresh_all_views())

            r2 = ttk.Frame(filt)
            r2.pack(fill=tk.X, pady=6)
            ttk.Label(r2, text="Тикер содержит:").pack(side=tk.LEFT)
            self.ticker_var = tk.StringVar()
            e_ticker = ttk.Entry(r2, textvariable=self.ticker_var, width=14)
            e_ticker.pack(side=tk.LEFT, padx=4)
            ttk.Label(r2, text="Тип API содержит:").pack(side=tk.LEFT, padx=(14, 0))
            self.type_var = tk.StringVar()
            e_type = ttk.Entry(r2, textvariable=self.type_var, width=22)
            e_type.pack(side=tk.LEFT, padx=4)
            for w in (e_ticker, e_type):
                w.bind("<Return>", lambda _e: self.refresh_raw_only())

            ttk.Label(
                filt,
                text="Неисполненные заявки (quantity = quantity_rest) всегда исключены из списка.",
                foreground="#555",
            ).pack(anchor=tk.W, pady=(0, 4))

            ttk.Button(filt, text="Обновить список", command=self.refresh_raw_only).pack(anchor=tk.W)

            tree_fr = ttk.Frame(right)
            tree_fr.pack(fill=tk.BOTH, expand=True, pady=6)

            cols = ("date", "account", "ticker", "op_type", "state", "qty", "qty_rest", "payment", "id")
            self.tree = ttk.Treeview(tree_fr, columns=cols, show="headings", height=16)
            htext = {
                "date": "Дата",
                "account": "Счёт",
                "ticker": "Тикер",
                "op_type": "operation_type",
                "state": "state",
                "qty": "qty",
                "qty_rest": "qty_rest",
                "payment": "payment",
                "id": "id",
            }
            for c in cols:
                self.tree.heading(c, text=htext[c])
                self.tree.column(c, width=88, stretch=(c == "op_type"))
            self.tree.column("date", width=140)
            self.tree.column("account", width=110)
            self.tree.column("op_type", width=220)
            self.tree.column("payment", width=120)
            self.tree.column("id", width=100)

            vsb = ttk.Scrollbar(tree_fr, orient=tk.VERTICAL, command=self.tree.yview)
            hsb = ttk.Scrollbar(tree_fr, orient=tk.HORIZONTAL, command=self.tree.xview)
            self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            self.tree.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")
            tree_fr.grid_rowconfigure(0, weight=1)
            tree_fr.grid_columnconfigure(0, weight=1)

            self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

            ttk.Label(right, text="Полный JSON выбранной строки").pack(anchor=tk.W)
            self.txt_json = scrolledtext.ScrolledText(right, height=11, wrap=tk.NONE, font=("Consolas", 8))
            self.txt_json.pack(fill=tk.BOTH, expand=True)

        def account_filter_params(self) -> Tuple[Optional[str], Optional[int]]:
            sel = self.account_var.get()
            if sel == ALL_ACCOUNTS or not sel:
                return None, None
            return sel, None

        def refresh_analytics(self) -> None:
            self.txt_analytics.delete("1.0", tk.END)
            if not self.broker_data:
                self.txt_analytics.insert(tk.END, "Нет данных. Загрузите портфель.")
                return
            acc_substr, acc_idx = self.account_filter_params()
            try:
                text = format_full_statistics(self.broker_data, acc_substr, acc_idx)
            except Exception as e:
                text = f"Ошибка построения сводки:\n{e}\n"
            self.txt_analytics.insert(tk.END, text)

        def refresh_raw_only(self) -> None:
            for x in self.tree.get_children():
                self.tree.delete(x)
            self._row_ops.clear()
            self._row_i = 0
            self.txt_json.delete("1.0", tk.END)
            if not self.broker_data:
                return
            acc_substr, acc_idx = self.account_filter_params()
            filtered, _warn = filter_broker_accounts(self.broker_data, acc_substr, acc_idx)
            t_sub = self.ticker_var.get().strip().upper()
            type_sub = self.type_var.get().strip().upper()
            n_hidden_rest = 0
            n_shown = 0

            for acc_name, acc_data in filtered.items():
                raw_list = acc_data.get("operations_raw")
                if raw_list is None:
                    continue
                for op in raw_list:
                    if _raw_op_qty_equals_rest(op):
                        n_hidden_rest += 1
                        continue
                    tick = op.get("ticker") or ""
                    if t_sub and t_sub not in tick.upper():
                        continue
                    ot = op.get("operation_type") or ""
                    if type_sub and type_sub not in ot.upper():
                        continue
                    iid = f"r{self._row_i}"
                    self._row_i += 1
                    self._row_ops[iid] = op
                    n_shown += 1
                    self.tree.insert(
                        "",
                        "end",
                        iid=iid,
                        values=(
                            (op.get("date") or "")[:19],
                            (acc_name or "")[:28],
                            tick,
                            (str(ot))[:80],
                            op.get("state") or "",
                            op.get("quantity"),
                            op.get("quantity_rest"),
                            _payment_raw_display(op),
                            (op.get("id") or "")[:40],
                        ),
                    )

            status = f"Строк: {n_shown} (скрыто qty=qty_rest на выбранных счетах: {n_hidden_rest})"
            self.root.title(f"Tinkoff import — {status}")

        def refresh_all_views(self) -> None:
            self.refresh_analytics()
            self.refresh_raw_only()

        def on_tree_select(self, _evt: Any = None) -> None:
            self.txt_json.delete("1.0", tk.END)
            sel = self.tree.selection()
            if not sel:
                return
            op = self._row_ops.get(sel[0])
            if op:
                self.txt_json.insert(tk.END, json.dumps(op, ensure_ascii=False, indent=2))

        def on_load(self) -> None:
            tok = self.token_var.get().strip()
            if not tok:
                messagebox.showerror("Токен", "Введите токен Tinkoff Invest API.")
                return
            self.btn_load.config(state="disabled")
            self.root.title("Tinkoff import — загрузка…")

            def work() -> None:
                try:
                    data = get_tinkoff_portfolio(tok, include_raw_operations=True)
                    self.root.after(0, lambda d=data: self._load_done(d, None))
                except Exception as e:
                    self.root.after(0, lambda err=e: self._load_done(None, err))

            threading.Thread(target=work, daemon=True).start()

        def _load_done(self, data: Optional[dict], err: Optional[Exception]) -> None:
            self.btn_load.config(state="normal")
            if err is not None:
                messagebox.showerror("Ошибка загрузки", str(err))
                self.root.title("Tinkoff import — аналитика и сырые операции")
                return
            self.broker_data = data or {}
            names = sorted(self.broker_data.keys())
            self.combo_acc["values"] = [ALL_ACCOUNTS] + names
            self.account_var.set(ALL_ACCOUNTS)
            self.refresh_all_views()
            if not self.broker_data:
                messagebox.showinfo("Пусто", "Нет доступных счетов.")

    root = tk.Tk()
    TinkoffImportGui(root, initial_token)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Тест импорта Tinkoff: статистика по данным API (без БД).")
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Окно: аналитика и сырые операции с фильтрами (qty=qty_rest всегда скрыты).",
    )
    parser.add_argument(
        "--token",
        "-t",
        type=str,
        default=None,
        metavar="TOKEN",
        help="Токен Tinkoff Invest API. Если не задан, используется переменная TINKOFF_TOKEN.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Интерактивное меню + полный отчёт.",
    )
    parser.add_argument(
        "--account-index",
        type=int,
        default=None,
        metavar="N",
        help="Номер счёта (1 … N) в списке имён по алфавиту.",
    )
    parser.add_argument(
        "--account",
        type=str,
        default=None,
        metavar="SUBSTR",
        help="Подстрока в имени счёта (без учёта регистра).",
    )
    parser.add_argument(
        "--raw-ticker",
        type=str,
        default=None,
        metavar="TICKER",
        help="Показать сырые операции API по тикеру (учитываются --account / --account-index).",
    )
    parser.add_argument(
        "--raw-only",
        action="store_true",
        help="Только блок сырых операций (--raw-ticker), без полной сводки и без интерактива.",
    )
    args = parser.parse_args()

    if args.raw_only and not (args.raw_ticker and args.raw_ticker.strip()):
        parser.error("--raw-only имеет смысл вместе с непустым --raw-ticker")

    if args.gui:
        run_gui((args.token or "").strip())
        return

    token = (args.token or "").strip() or os.getenv("TINKOFF_TOKEN")

    if not token:
        print("❌ ОШИБКА: не задан токен.")
        print("\nПередайте токен аргументом:")
        print("  python scripts/test_tinkoff_import.py --token YOUR_TOKEN")
        print("или установите переменную окружения:")
        print("  Windows PowerShell: $env:TINKOFF_TOKEN='your_token_here'")
        print("  Windows CMD: set TINKOFF_TOKEN=your_token_here")
        print("  Linux/Mac: export TINKOFF_TOKEN='your_token_here'")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("ТЕСТИРОВАНИЕ ИМПОРТА ПОРТФЕЛЯ TINKOFF")
    print("=" * 80)

    try:
        want_raw = bool(args.raw_ticker and args.raw_ticker.strip())
        print("\n📥 Получаем данные от брокера Tinkoff...")
        broker_data = get_tinkoff_portfolio(token, include_raw_operations=want_raw)

        if not broker_data:
            print("⚠️  Портфель пуст (нет доступных счетов)")
            return

        print(f"✅ Получено данных для {len(broker_data)} счетов")

        acc_substr: Optional[str] = args.account
        acc_index: Optional[int] = args.account_index

        if args.raw_only and args.interactive:
            print("⚠️  Режим --raw-only: интерактивное меню пропущено.")

        if not args.raw_only and args.interactive:
            print("\n" + "=" * 80)
            print("ВЫБОР ТИПА АНАЛИЗА")
            print("=" * 80)
            print("1. Баланс")
            print("2. Позиции")
            print("3. Операции")
            print("4. Краткая сводка")
            print("0. Выход")

            choice = input("\nВыберите тип анализа (Enter для всего кроме выхода): ").strip()

            if choice == "0":
                return

            names = sorted(broker_data.keys())
            if choice in ("1", "2", "3", "") and len(names) > 1:
                print("\n" + "-" * 80)
                print("ВЫБОР СЧЁТА")
                print("-" * 80)
                print("0. Все счета")
                for i, n in enumerate(names, 1):
                    print(f"{i}. {n}")
                pick = input("\nНомер счёта (Enter = все): ").strip()
                if pick and pick != "0":
                    try:
                        idx = int(pick)
                        if 1 <= idx <= len(names):
                            acc_index = idx
                            print(f"✅ Счёт: {names[idx - 1]}")
                    except ValueError:
                        pass

            if choice == "1" or choice == "":
                show_balance_analysis(broker_data, acc_substr, acc_index)

            if choice == "2" or choice == "":
                show_positions_broker_only(broker_data, acc_substr, acc_index)

            if choice == "3" or choice == "":
                lim = None if acc_index else 10
                show_operations(broker_data, acc_substr, acc_index, limit=lim)

            if choice == "4":
                print("\n" + "=" * 80)
                print("КРАТКАЯ СТАТИСТИКА")
                print("=" * 80)
                total_positions = sum(len(acc.get("positions", [])) for acc in broker_data.values())
                total_transactions = sum(len(acc.get("transactions", [])) for acc in broker_data.values())
                print(f"\n📊 Всего счетов: {len(broker_data)}")
                print(f"📊 Всего позиций: {total_positions}")
                print(f"📊 Всего операций в выгрузке: {total_transactions}")

        if want_raw:
            show_raw_operations_for_ticker(broker_data, args.raw_ticker.strip(), acc_substr, acc_index)

        if not args.raw_only:
            emit_full_statistics(broker_data, acc_substr, acc_index)

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
