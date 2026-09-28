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
    python scripts/test_tinkoff_import.py --gui   # GUI: окно (по умолчанию с operations_raw)
    python scripts/test_tinkoff_import.py --skip-raw-operations   # без operations_raw (сводка «Слито ком.» = —)

Токен: аргумент --token / -t или переменная окружения TINKOFF_TOKEN (приоритет у аргумента).
По умолчанию CLI запрашивает operations_raw, чтобы в сводке учесть дочерние комиссии, вшитые в родительскую операцию.
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
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.external.brokers.tinkoff import get_tinkoff_portfolio
from app.infrastructure.external.brokers.tinkoff.import_service import (
    OPERATION_CLASSIFICATION,
    classify_tinkoff_operation,
    _normalize_tinkoff_operation_id,
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


def _position_is_cash_balance(pos: dict) -> bool:
    """Текущая позиция — валютный остаток (не бумага)."""
    ticker = (pos.get("ticker") or "").upper()
    name = (pos.get("name") or "").lower()
    return ticker.startswith("RUB") or ticker.startswith("RUR") or "рубль" in name


def collect_instruments_not_in_portfolio(broker_data: dict) -> List[dict]:
    """
    Тикеры с Buy/Sell/Amortization в выгрузке, которых нет среди текущих позиций get_portfolio
    (типично полностью проданные бумаги). API портфеля отдаёт только открытые позиции.
    """
    rows: List[dict] = []
    if not broker_data:
        return rows

    for acc_name, acc in broker_data.items():
        pos_tickers: Set[str] = set()
        for p in acc.get("positions", []):
            if _position_is_cash_balance(p):
                continue
            t = (p.get("ticker") or "").strip().upper()
            if t:
                pos_tickers.add(t)

        by_ticker: Dict[str, Dict[str, Any]] = {}
        for tx in acc.get("transactions", []):
            if tx.get("type") not in ("Buy", "Sell", "Amortization"):
                continue
            t = (tx.get("ticker") or "").strip().upper()
            if not t or t.startswith("RUB") or t.startswith("RUR"):
                continue
            if t in pos_tickers:
                continue
            if t not in by_ticker:
                by_ticker[t] = {
                    "last_date": "",
                    "name": "",
                    "isin": "",
                    "types": set(),
                }
            meta = by_ticker[t]
            d = tx.get("date") or ""
            if d > meta["last_date"]:
                meta["last_date"] = d
            nm = tx.get("name") or ""
            if nm and (not meta["name"] or len(nm) > len(meta["name"])):
                meta["name"] = nm
            isin = tx.get("isin") or ""
            if isin:
                meta["isin"] = isin
            meta["types"].add(tx.get("type") or "")

        for t in sorted(by_ticker.keys()):
            meta = by_ticker[t]
            types_sorted = sorted(x for x in meta["types"] if x)
            rows.append(
                {
                    "account": acc_name,
                    "ticker": t,
                    "name": meta["name"] or "—",
                    "isin": meta["isin"] or "—",
                    "last_date": (meta["last_date"] or "")[:19],
                    "types": ", ".join(types_sorted) or "—",
                }
            )

    rows.sort(key=lambda r: (r["account"], r["ticker"]))
    return rows


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


def _tx_commission_float(tx: dict) -> float:
    try:
        return float(tx.get("commission") or 0)
    except (TypeError, ValueError):
        return 0.0


def _tx_cash_flow_for_balance(tx: dict) -> float:
    """Поток по строке выгрузки для сверки с кэшем в позициях: payment + commission (в валюте строки)."""
    try:
        p = float(tx.get("payment") or 0)
    except (TypeError, ValueError):
        p = 0.0
    return p + _tx_commission_float(tx)


def _sum_cash_flow_by_currency(transactions: List[dict]) -> Dict[str, float]:
    by_curr: Dict[str, float] = defaultdict(float)
    for tx in transactions:
        raw = tx.get("currency")
        if raw is None and tx.get("type") in ("Buy", "Sell", "Amortization"):
            c = "rub"
        else:
            c = raw or "rub"
        c = _fmt_currency(c).lower().strip() or "rub"
        by_curr[c] += _tx_cash_flow_for_balance(tx)
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


def _raw_op_zero_executed_quantity(op: dict) -> bool:
    """Как _tinkoff_buy_sell_zero_executed_quantity в import_service, для словаря operations_raw."""
    q = op.get("quantity")
    qr = op.get("quantity_rest")
    try:
        executed = float(q or 0) - float(qr or 0)
    except (TypeError, ValueError):
        return False
    return executed == 0


def tinkoff_commission_child_skip_ids_from_raw(ops_raw: Optional[List[dict]]) -> Set[str]:
    """
    id операций-комиссий, которые import_service не добавляет в transactions отдельной строкой:
    сумма уходит в commission родителя (см. _tinkoff_commission_by_parent).
    """
    if not ops_raw:
        return set()
    ids_in_batch: Set[str] = set()
    ops_by_id: Dict[str, dict] = {}
    for op in ops_raw:
        if not isinstance(op, dict):
            continue
        kid = _normalize_tinkoff_operation_id(op.get("id"))
        if kid:
            ids_in_batch.add(kid)
            ops_by_id[kid] = op
    skip_ids: Set[str] = set()
    for op in ops_raw:
        if not isinstance(op, dict):
            continue
        otn = str(op.get("operation_type") or "")
        if classify_tinkoff_operation(otn) != "Commission":
            continue
        parent_key = _normalize_tinkoff_operation_id(op.get("parent_operation_id"))
        if not parent_key or parent_key not in ids_in_batch:
            continue
        parent_op = ops_by_id.get(parent_key)
        if parent_op is not None and _raw_op_zero_executed_quantity(parent_op):
            continue
        cid = _normalize_tinkoff_operation_id(op.get("id"))
        if cid:
            skip_ids.add(cid)
    return skip_ids


def _merged_commission_children_count(acc: dict) -> Optional[int]:
    """Число слитых дочерних комиссий; None, если нет operations_raw (посчитать нельзя)."""
    raw = acc.get("operations_raw")
    if raw is None:
        return None
    return len(tinkoff_commission_child_skip_ids_from_raw(raw))


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
        n_merged = _merged_commission_children_count(acc)
        if n_merged is not None:
            merged_cell = str(n_merged)
            delta_cmp = n_tx - n_api + n_merged
        else:
            merged_cell = "—"
            delta_cmp = n_tx - n_api
        summary_rows.append([
            acc_name[:28],
            str(acc.get("account_id", ""))[:36],
            len(acc.get("positions", [])),
            n_tx,
            raw_c,
            merged_cell,
            n_skip,
            delta_cmp,
        ])
    print_table(
        [
            "Счёт",
            "account_id",
            "Позиций",
            "В выгрузке",
            "В API",
            "Слито ком.",
            "Пропущено",
            "Δ сопост.",
        ],
        summary_rows,
    )
    print(
        "Δ сопост.: выгрузка − API + слитые комиссии (ожидаемо ≈ 0 с учётом синтетики и пропусков). "
        "Без operations_raw «Слито ком.» = —, Δ совпадает с «сырой» разницей выгрузка−API."
    )

    print("\n" + "=" * 100)
    print("БАЛАНС: ПОЗИЦИИ (брокер) vs Σ(payment + commission) ПО ОПЕРАЦИЯМ ВЫГРУЗКИ")
    print("=" * 100)
    balance_rows = []
    for acc_name, acc in filtered.items():
        positions = acc.get("positions", [])
        txs = acc.get("transactions", [])
        pos_cash = _cash_balances_from_positions(positions)
        flow_by = _sum_cash_flow_by_currency(txs)
        all_curr = sorted(set(pos_cash.keys()) | set(flow_by.keys()))
        if not all_curr:
            all_curr = ["rub"]
        for curr in all_curr:
            p_bal = pos_cash.get(curr, 0.0)
            o_bal = flow_by.get(curr, 0.0)
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
        ["Счёт", "Валюта", "Позиция (кэш)", "Σ pay+comm", "Δ (поз − опер.)", ""],
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
        comm_sum = sum(
            float(x.get("commission") or 0)
            for x in all_tx
            if (x.get("type") or "—") == t
        )
        type_rows.append([t, c, f"{pay_sum:,.2f}", f"{comm_sum:,.2f}"])
    print_table(["type", "шт.", "Σ payment", "Σ commission"], type_rows)

    print("\n" + "=" * 100)
    print("ОПЕРАЦИИ ВЫГРУЗКИ (payment и вложенная commission по строке)")
    print("=" * 100)
    _detail_limit = 600
    detail_rows = []
    for tx in sorted(all_tx, key=lambda x: (x.get("date") or ""), reverse=True):
        try:
            c_raw = float(tx.get("commission")) if tx.get("commission") is not None else None
        except (TypeError, ValueError):
            c_raw = None
        if c_raw is not None and abs(c_raw) >= 1e-12:
            comm_s = f"{c_raw:,.6f}".rstrip("0").rstrip(".").rstrip(",")
        else:
            comm_s = "—"
        detail_rows.append(
            [
                (tx.get("date") or "")[:19],
                (tx.get("account_name") or "")[:14],
                str(tx.get("type") or "")[:12],
                (tx.get("ticker") or "—")[:10],
                f"{float(tx.get('payment') or 0):,.2f}",
                comm_s,
                _fmt_currency(tx.get("currency"))[:8],
                str(tx.get("operation_id") or "")[:22],
            ]
        )
    print_table(
        ["Дата", "Счёт", "type", "Тикер", "payment", "commission", "currency", "operation_id"],
        detail_rows[:_detail_limit],
    )
    if len(detail_rows) > _detail_limit:
        print(f"... показано {_detail_limit} из {len(detail_rows)} строк")

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
    merged_list = [_merged_commission_children_count(a) for a in filtered.values()]
    if all(x is not None for x in merged_list):
        merged_total = sum(int(x) for x in merged_list)  # type: ignore[arg-type]
        raw_api_cmp = raw_api - merged_total
        delta_cmp = raw_exported - raw_api_cmp
        merged_note = str(merged_total)
    else:
        raw_api_cmp = None
        delta_cmp = None
        merged_note = "— (нужен include_raw_operations / operations_raw)"
    print("\n" + "=" * 100)
    print("СЧЁТЧИКИ ОПЕРАЦИЙ: API vs ВЫГРУЗКА")
    print("=" * 100)
    counter_rows = [
        ["Сырых операций в API (Σ по счетам)", raw_api, "ответ get_operations, все строки"],
        [
            "Дочерних комиссий, слитых в родителя (Σ)",
            merged_note,
            "отдельные строки в transactions не создаются; commission у родителя",
        ],
    ]
    if raw_api_cmp is not None:
        counter_rows.append(
            ["API для сравнения с выгрузкой (Σ)", raw_api_cmp, "сырой API − слитые комиссии"],
        )
    counter_rows.extend(
        [
            ["Записей в transactions после обработки", raw_exported, "вкл. синтетику DIV_EXT"],
            [
                "Разница (выгрузка − сырой API)",
                raw_exported - raw_api,
                "отрицательна при слиянии комиссий — это норма",
            ],
        ]
    )
    if delta_cmp is not None:
        counter_rows.append(
            [
                "Разница (выгрузка − API сопоставимый)",
                delta_cmp,
                "≈ −пропуски + синтетика; мелкие расхождения — см. пропуски по счетам",
            ],
        )
    print_table(["Метрика", "Значение", "Комментарий"], counter_rows)

    # Пропущенные при импорте (не попали в transactions) — при выгрузке < API обязательны; показываем всегда, если есть
    for acc_name, acc in filtered.items():
        n_api = int(acc.get("operations_raw_count") or 0)
        n_exp = len(acc.get("transactions", []))
        n_merged_acc = _merged_commission_children_count(acc)
        skipped = acc.get("transactions_skipped") or []
        if not skipped:
            if n_api > n_exp:
                if n_merged_acc is None:
                    print("\n" + "=" * 100)
                    print(
                        f"⚠️  Счёт «{acc_name}»: в API {n_api} операций, в выгрузке {n_exp}, "
                        "но transactions_skipped пуст (без operations_raw не видно, слиты ли комиссии)."
                    )
                    print("=" * 100)
                else:
                    n_syn = sum(
                        1
                        for tx in acc.get("transactions", [])
                        if str(tx.get("tinkoff_operation_type") or "").startswith("SYNTHETIC")
                    )
                    # n_exp ≈ n_api − слитые комиссии − пропуски + синтетика
                    residual = (n_api - n_exp) - n_merged_acc + n_syn
                    if residual != 0:
                        print("\n" + "=" * 100)
                        print(
                            f"⚠️  Счёт «{acc_name}»: в API {n_api} операций, в выгрузке {n_exp}, "
                            "transactions_skipped пуст, остаток после учёта слитых комиссий и синтетики не 0 "
                            f"({residual}: слито ком. {n_merged_acc}, синтетика {n_syn})."
                        )
                        print("=" * 100)
            continue
        hint = ""
        if n_api > n_exp:
            gap = n_api - n_exp
            hint = f" (сырой API больше выгрузки на {gap}"
            if n_merged_acc is not None and n_merged_acc > 0:
                hint += f"; из них слитых дочерних комиссий {n_merged_acc}"
            hint += ")"
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
        n_merged_syn = _merged_commission_children_count(acc)
        n_api_cmp = n_api - (n_merged_syn or 0) if n_merged_syn is not None else n_api
        synthetic = [
            tx for tx in acc.get("transactions", [])
            if str(tx.get("tinkoff_operation_type") or "").startswith("SYNTHETIC")
        ]
        if not synthetic:
            if n_exp > n_api_cmp:
                print("\n" + "=" * 100)
                print(
                    f"⚠️  Счёт «{acc_name}»: выгрузка {n_exp} > сопоставимый API {n_api_cmp} (сырой API {n_api}), "
                    "но синтетических строк (SYNTHETIC*) нет — проверьте логику импорта."
                )
                print("=" * 100)
            continue
        hint = ""
        if n_exp > n_api_cmp:
            hint = (
                f" (выгрузка {n_exp} > сопоставимый API {n_api_cmp}: +{n_exp - n_api_cmp}; "
                f"сырой API {n_api})"
            )
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
            currency = _fmt_currency(tx.get("currency", "rub")).lower()
            if currency and currency not in ("rub", "rur", "руб"):
                continue
            balance_from_operations += _tx_cash_flow_for_balance(tx)

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


def _money_dict_to_float(d: Any) -> Optional[float]:
    if not isinstance(d, dict):
        return None
    try:
        u = int(d.get("units") or 0)
        n = int(d.get("nano") or 0)
        return float(u) + float(n) / 1e9
    except (TypeError, ValueError):
        return None


def _raw_op_exec_quantity_price_payment(op: dict) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    q = op.get("quantity")
    qr = op.get("quantity_rest")
    exec_q: Optional[float] = None
    try:
        if q is not None and qr is not None:
            exec_q = float(q) - float(qr)
        elif q is not None:
            exec_q = float(q)
    except (TypeError, ValueError):
        pass
    return (
        _money_dict_to_float(op.get("price")),
        exec_q,
        _money_dict_to_float(op.get("payment")),
    )


def _commission_sum_from_raw_children(op: dict) -> Optional[float]:
    """Сумма payment у дочерних операций класса Commission (как в import_service._tinkoff_commission_by_parent)."""
    total = 0.0
    n = 0
    for ch in op.get("child_operations") or []:
        if not isinstance(ch, dict):
            continue
        otn = ch.get("operation_type")
        if classify_tinkoff_operation(str(otn or "")) != "Commission":
            continue
        v = _money_dict_to_float(ch.get("payment"))
        if v is not None:
            total += v
            n += 1
    return total if n else None


def merge_account_operations_for_gui(acc_name: str, acc_data: dict) -> List[dict]:
    """
    Сводная лента для вкладки «Операции»:
    - transactions — то, что уйдёт в portfolio_import_service;
    - transactions_skipped — в т.ч. Buy/Sell с исполненным qty=0 (не попали в выгрузку);
    - сырые операции API с id: Buy/Sell/Amort, которых нет в выгрузке и не в skipped (аномалии).
    """
    rows: List[dict] = []

    for tx in acc_data.get("transactions") or []:
        r = dict(tx)
        r["account_name"] = acc_name
        r["_gui_src"] = "выгрузка"
        r["_gui_reason"] = ""
        rows.append(r)

    for sk in acc_data.get("transactions_skipped") or []:
        r = dict(sk)
        r["account_name"] = acc_name
        r["_gui_src"] = "пропуск"
        reason = str(sk.get("reason") or "")
        qa, qr = sk.get("quantity_api"), sk.get("quantity_rest")
        if qa is not None or qr is not None:
            reason = f"{reason} qty_api={qa} rest={qr}"
        r["_gui_reason"] = reason[:200]
        if r.get("quantity") is None and sk.get("executed_quantity") is not None:
            r["quantity"] = sk.get("executed_quantity")
        rows.append(r)

    raw_list = acc_data.get("operations_raw")
    if raw_list:
        exp_ids = {
            str(x["operation_id"])
            for x in acc_data.get("transactions") or []
            if x.get("operation_id") not in (None, "")
        }
        skip_ids = {
            str(x["operation_id"])
            for x in (acc_data.get("transactions_skipped") or [])
            if x.get("operation_id") not in (None, "")
        }
        for op in raw_list:
            if _raw_op_qty_equals_rest(op):
                continue
            oid = op.get("id")
            if oid is None or oid == "":
                continue
            sid = str(oid)
            if sid in exp_ids or sid in skip_ids:
                continue
            otn = op.get("operation_type") or ""
            cls = classify_tinkoff_operation(otn)
            if cls not in ("Buy", "Sell", "Amortization"):
                continue
            pf, eq, payf = _raw_op_exec_quantity_price_payment(op)
            comm_ch = _commission_sum_from_raw_children(op)
            row_api = {
                "account_name": acc_name,
                "date": op.get("date"),
                "type": cls,
                "ticker": op.get("ticker"),
                "isin": op.get("isin"),
                "price": pf,
                "quantity": eq,
                "payment": payf,
                "currency": op.get("currency"),
                "tinkoff_operation_type": otn,
                "operation_id": oid,
                "_gui_src": "только_API",
                "_gui_reason": "есть в get_operations, нет строки в transactions (сверка по operation_id)",
                "_raw_snapshot": op,
            }
            if comm_ch is not None:
                row_api["commission"] = comm_ch
            rows.append(row_api)

    return rows


def iter_merged_operations_for_gui(
    broker_data: dict,
    account_substr: Optional[str] = None,
    account_index: Optional[int] = None,
) -> List[dict]:
    """Все строки вкладки «Операции» (выгрузка + пропуски + только_API) с учётом фильтра счёта."""
    filtered, _ = filter_broker_accounts(broker_data, account_substr, account_index)
    out: List[dict] = []
    for acc_name, acc_data in filtered.items():
        out.extend(merge_account_operations_for_gui(acc_name, acc_data))
    out.sort(key=lambda x: x.get("date", "") or "", reverse=True)
    return out


def _position_matches_query(pos: dict, account_name: str, q: str) -> bool:
    if not q:
        return True
    parts = [
        account_name,
        str(pos.get("ticker") or ""),
        str(pos.get("name") or ""),
        str(pos.get("isin") or ""),
    ]
    blob = " ".join(p.lower() for p in parts)
    return q in blob


def _sold_row_matches_query(row: dict, q: str) -> bool:
    if not q:
        return True
    blob = " ".join(
        str(row.get(k) or "").lower()
        for k in ("account", "ticker", "name", "isin", "types", "last_date")
    )
    return q in blob


def operations_to_json_serializable(tx: dict) -> dict:
    """Словарь для JSON/экспорта: служебные ключи _*, кроме _gui_* и _raw_snapshot, отбрасываются."""
    out: Dict[str, Any] = {}
    for k, v in tx.items():
        if k == "_raw_snapshot":
            out[k] = v
        elif str(k).startswith("_") and k not in ("_gui_src", "_gui_reason"):
            continue
        else:
            out[k] = v
    return out


def run_gui(initial_token: str = "") -> None:
    """Окно: Позиции (поиск) | Аналитика (текст, файл, буфер + сырые API) | Операции (фильтры, экспорт)."""
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk

    ALL_ACCOUNTS = "Все счета"
    OP_SRC_ALL = "(все источники)"
    OP_SRC_VALUES = (OP_SRC_ALL, "выгрузка", "пропуск", "только_API")

    class TinkoffImportGui:
        def __init__(self, root: tk.Tk, token_hint: str) -> None:
            self.root = root
            self.root.title("Tinkoff import")
            self.root.minsize(1100, 700)
            self.broker_data: Optional[dict] = None
            self._row_ops: Dict[str, dict] = {}
            self._row_tx: Dict[str, dict] = {}
            self._row_i = 0
            self._position_trees: Dict[str, Any] = {}
            self._sold_tree: Optional[Any] = None
            self.positions_nb_holder: Optional[ttk.Frame] = None
            self._last_filtered_ops: List[dict] = []
            self.pos_search_var = tk.StringVar()

            main = ttk.Frame(self.root, padding=6)
            main.pack(fill=tk.BOTH, expand=True)

            top = ttk.Frame(main)
            top.pack(fill=tk.X, pady=(0, 6))

            ttk.Label(top, text="Токен:").pack(side=tk.LEFT)
            hint = (token_hint or "").strip() or (os.getenv("TINKOFF_TOKEN") or "")
            self.token_var = tk.StringVar(value=hint)
            self.token_entry = ttk.Entry(top, textvariable=self.token_var, width=44, show="*")
            self.token_entry.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
            self._bind_token_paste_shortcuts()
            ttk.Button(top, text="Вставить", command=self.paste_token_from_clipboard).pack(
                side=tk.LEFT, padx=(0, 4)
            )
            self.btn_load = ttk.Button(top, text="Загрузить с API", command=self.on_load)
            self.btn_load.pack(side=tk.LEFT)

            filt_top = ttk.Frame(main)
            filt_top.pack(fill=tk.X, pady=(0, 4))
            ttk.Label(filt_top, text="Фильтр счёта (аналитика, сырые API, выгрузка операций):").pack(side=tk.LEFT)
            self.account_var = tk.StringVar(value=ALL_ACCOUNTS)
            self.combo_acc = ttk.Combobox(filt_top, textvariable=self.account_var, width=36, state="readonly")
            self.combo_acc.pack(side=tk.LEFT, padx=6)
            self.combo_acc.bind("<<ComboboxSelected>>", lambda _e: self.on_account_combo_change())

            self.main_nb = ttk.Notebook(main)
            self.main_nb.pack(fill=tk.BOTH, expand=True)

            # ----- Вкладка 1: позиции (подвкладки = портфели) -----
            self.tab_positions = ttk.Frame(self.main_nb, padding=4)
            self.main_nb.add(self.tab_positions, text="Позиции")
            ttk.Label(
                self.tab_positions,
                text=(
                    "Подвкладки: сводка и счета — текущий портфель API; «Нет в портфеле» — бумаги с Buy/Sell/амортизации "
                    "в выгрузке, которых сейчас нет в позициях (часто полностью проданные). "
                    "Фильтр счёта сверху — для «Аналитики», «Операций» и сырых API; поиск ниже фильтрует таблицы позиций."
                ),
                foreground="#555",
            ).pack(anchor=tk.W, pady=(0, 4))
            pos_filt = ttk.Frame(self.tab_positions)
            pos_filt.pack(fill=tk.X, pady=(0, 4))
            ttk.Label(pos_filt, text="Поиск по позициям (тикер / название / ISIN / счёт):").pack(side=tk.LEFT)
            e_pos = ttk.Entry(pos_filt, textvariable=self.pos_search_var, width=36)
            e_pos.pack(side=tk.LEFT, padx=6)
            e_pos.bind("<KeyRelease>", lambda _e: self.refresh_positions())
            ttk.Button(pos_filt, text="Сброс", command=self._clear_pos_search).pack(side=tk.LEFT, padx=4)
            self.positions_nb_holder = ttk.Frame(self.tab_positions)
            self.positions_nb_holder.pack(fill=tk.BOTH, expand=True)

            # ----- Вкладка 2: аналитика + сырые операции -----
            self.tab_analytics = ttk.Frame(self.main_nb, padding=4)
            self.main_nb.add(self.tab_analytics, text="Аналитика")
            paned_an = ttk.Panedwindow(self.tab_analytics, orient=tk.VERTICAL)
            paned_an.pack(fill=tk.BOTH, expand=True)

            fr_an_text = ttk.Frame(paned_an, padding=2)
            paned_an.add(fr_an_text, weight=3)
            an_tool = ttk.Frame(fr_an_text)
            an_tool.pack(fill=tk.X, pady=(0, 4))
            ttk.Label(an_tool, text="Сводка и проверки (emit_full_statistics)").pack(side=tk.LEFT)
            ttk.Button(an_tool, text="Обновить", command=self.refresh_analytics).pack(side=tk.LEFT, padx=8)
            ttk.Button(an_tool, text="Сохранить в файл…", command=self.save_analytics_file).pack(side=tk.LEFT, padx=4)
            ttk.Button(an_tool, text="Копировать всё", command=self.copy_analytics_clipboard).pack(side=tk.LEFT, padx=4)
            self.txt_analytics = scrolledtext.ScrolledText(fr_an_text, wrap=tk.WORD, font=("Consolas", 9))
            self.txt_analytics.pack(fill=tk.BOTH, expand=True)
            self.txt_analytics.insert(tk.END, "Нажмите «Загрузить с API».\n")

            fr_raw_block = ttk.Frame(paned_an, padding=2)
            paned_an.add(fr_raw_block, weight=4)

            filt = ttk.LabelFrame(fr_raw_block, text="Сырые операции API (фильтры)", padding=8)
            filt.pack(fill=tk.X)

            r2 = ttk.Frame(filt)
            r2.pack(fill=tk.X)
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

            ttk.Button(filt, text="Обновить список сырых", command=self.refresh_raw_only).pack(anchor=tk.W)

            raw_paned = ttk.Panedwindow(fr_raw_block, orient=tk.HORIZONTAL)
            raw_paned.pack(fill=tk.BOTH, expand=True, pady=6)

            tree_fr = ttk.Frame(raw_paned, padding=2)
            raw_paned.add(tree_fr, weight=5)

            cols = ("date", "account", "ticker", "op_type", "state", "qty", "qty_rest", "payment", "id")
            self.tree = ttk.Treeview(tree_fr, columns=cols, show="headings", height=12)
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

            json_fr = ttk.Frame(raw_paned, padding=2)
            raw_paned.add(json_fr, weight=3)
            ttk.Label(json_fr, text="JSON выбранной сырой операции").pack(anchor=tk.W)
            self.txt_json = scrolledtext.ScrolledText(json_fr, wrap=tk.NONE, font=("Consolas", 8))
            self.txt_json.pack(fill=tk.BOTH, expand=True)

            # ----- Вкладка 3: операции выгрузки (classify) -----
            self.tab_ops = ttk.Frame(self.main_nb, padding=4)
            self.main_nb.add(self.tab_ops, text="Операции")
            op_filt = ttk.LabelFrame(self.tab_ops, text="Фильтры объединённой ленты (выгрузка + пропуски + только API)", padding=8)
            op_filt.pack(fill=tk.X, pady=(0, 6))
            r1 = ttk.Frame(op_filt)
            r1.pack(fill=tk.X)
            ttk.Label(r1, text="Тикер содержит:").pack(side=tk.LEFT)
            self.op_ticker_var = tk.StringVar()
            e_op_t = ttk.Entry(r1, textvariable=self.op_ticker_var, width=12)
            e_op_t.pack(side=tk.LEFT, padx=4)
            ttk.Label(r1, text="Класс type содержит:").pack(side=tk.LEFT, padx=(10, 0))
            self.op_class_substr_var = tk.StringVar()
            ttk.Entry(r1, textvariable=self.op_class_substr_var, width=12).pack(side=tk.LEFT, padx=4)
            ttk.Label(r1, text="ISIN содержит:").pack(side=tk.LEFT, padx=(10, 0))
            self.op_isin_var = tk.StringVar()
            ttk.Entry(r1, textvariable=self.op_isin_var, width=14).pack(side=tk.LEFT, padx=4)
            ttk.Label(r1, text="Источник:").pack(side=tk.LEFT, padx=(10, 0))
            self.op_src_var = tk.StringVar(value=OP_SRC_ALL)
            ttk.Combobox(
                r1, textvariable=self.op_src_var, values=OP_SRC_VALUES, width=16, state="readonly",
            ).pack(side=tk.LEFT, padx=4)

            r2 = ttk.Frame(op_filt)
            r2.pack(fill=tk.X, pady=(6, 0))
            ttk.Label(r2, text="operation_type (сырой) содержит:").pack(side=tk.LEFT)
            self.op_raw_type_var = tk.StringVar()
            e_raw = ttk.Entry(r2, textvariable=self.op_raw_type_var, width=28)
            e_raw.pack(side=tk.LEFT, padx=4)
            ttk.Label(r2, text="Макс. строк в таблице:").pack(side=tk.LEFT, padx=(12, 0))
            self.op_max_rows_var = tk.StringVar(value="8000")
            ttk.Spinbox(r2, from_=500, to=50000, increment=500, width=8, textvariable=self.op_max_rows_var).pack(
                side=tk.LEFT, padx=4
            )
            ttk.Button(r2, text="Применить", command=self.refresh_operations).pack(side=tk.LEFT, padx=12)
            ttk.Button(r2, text="Экспорт JSON…", command=self.export_operations_json).pack(side=tk.LEFT, padx=4)
            ttk.Button(r2, text="Экспорт CSV…", command=self.export_operations_csv).pack(side=tk.LEFT, padx=4)
            for w in (e_op_t, e_raw):
                w.bind("<Return>", lambda _e: self.refresh_operations())

            self.lbl_ops_stats = ttk.Label(op_filt, text="", foreground="#444")
            self.lbl_ops_stats.pack(anchor=tk.W, pady=(6, 0))

            ttk.Label(
                self.tab_ops,
                text=(
                    "Строки: «выгрузка» = transactions (импорт в БД); «пропуск» = не вошли (часто qty−qty_rest=0); "
                    "«только_API» = сырой Buy/Sell с id, которого нет в выгрузке. Экспорт сохраняет все строки, "
                    "прошедшие фильтры (без лимита таблицы)."
                ),
                foreground="#555",
                wraplength=1040,
            ).pack(anchor=tk.W, pady=(0, 4))

            op_tree_fr = ttk.Frame(self.tab_ops)
            op_tree_fr.pack(fill=tk.BOTH, expand=True)

            ocols = (
                "date",
                "account",
                "src",
                "op_id",
                "type",
                "ticker",
                "isin",
                "price",
                "qty",
                "payment",
                "commission",
                "cur",
                "raw_type",
                "reason",
            )
            self.tree_ops = ttk.Treeview(op_tree_fr, columns=ocols, show="headings", height=18)
            op_htext = {
                "date": "Дата",
                "account": "Счёт",
                "src": "Источник",
                "op_id": "id API",
                "type": "type",
                "ticker": "Тикер",
                "isin": "ISIN",
                "price": "Цена",
                "qty": "Кол-во",
                "payment": "Сумма",
                "commission": "Комиссия",
                "cur": "Вал.",
                "raw_type": "operation_type",
                "reason": "Примечание",
            }
            for c in ocols:
                self.tree_ops.heading(c, text=op_htext[c])
                w = 72
                if c == "date":
                    w = 136
                elif c == "account":
                    w = 100
                elif c == "src":
                    w = 88
                elif c == "op_id":
                    w = 96
                elif c == "raw_type":
                    w = 168
                elif c == "isin":
                    w = 100
                elif c == "commission":
                    w = 88
                elif c == "reason":
                    w = 220
                self.tree_ops.column(c, width=w, stretch=(c in ("raw_type", "reason")))
            vsb_o = ttk.Scrollbar(op_tree_fr, orient=tk.VERTICAL, command=self.tree_ops.yview)
            hsb_o = ttk.Scrollbar(op_tree_fr, orient=tk.HORIZONTAL, command=self.tree_ops.xview)
            self.tree_ops.configure(yscrollcommand=vsb_o.set, xscrollcommand=hsb_o.set)
            self.tree_ops.grid(row=0, column=0, sticky="nsew")
            vsb_o.grid(row=0, column=1, sticky="ns")
            hsb_o.grid(row=1, column=0, sticky="ew")
            op_tree_fr.grid_rowconfigure(0, weight=1)
            op_tree_fr.grid_columnconfigure(0, weight=1)

            self.tree_ops.bind("<<TreeviewSelect>>", self.on_tree_ops_select)

            ttk.Label(self.tab_ops, text="JSON выбранной операции выгрузки").pack(anchor=tk.W, pady=(4, 0))
            self.txt_ops_json = scrolledtext.ScrolledText(self.tab_ops, height=8, wrap=tk.NONE, font=("Consolas", 8))
            self.txt_ops_json.pack(fill=tk.BOTH, expand=False)

            self.token_entry.focus_set()

        def _bind_token_paste_shortcuts(self) -> None:
            """На Windows Ctrl+V в ttk.Entry часто не вставляет; вешаем явную вставку из CLIPBOARD."""

            def on_paste(_event: Any = None) -> str:
                try:
                    clip = self.root.clipboard_get()
                except tk.TclError:
                    return "break"
                w = self.token_entry
                try:
                    if w.selection_present():
                        w.delete("sel.first", "sel.last")
                    w.insert("insert", clip)
                except tk.TclError:
                    self.token_var.set((self.token_var.get() or "") + str(clip))
                return "break"

            for seq in ("<Control-v>", "<Control-V>", "<Shift-Insert>"):
                self.token_entry.bind(seq, on_paste)

        def paste_token_from_clipboard(self) -> None:
            try:
                clip = self.root.clipboard_get()
            except tk.TclError:
                messagebox.showwarning("Буфер обмена", "Не удалось прочитать буфер обмена.")
                return
            w = self.token_entry
            try:
                if w.selection_present():
                    w.delete("sel.first", "sel.last")
                w.insert("insert", clip)
            except tk.TclError:
                self.token_var.set((self.token_var.get() or "") + str(clip))
            w.focus_set()

        def _pos_kind(self, pos: dict) -> str:
            ticker = (pos.get("ticker") or "").upper()
            name = (pos.get("name") or "").lower()
            if ticker.startswith("RUB") or ticker.startswith("RUR") or "рубль" in name:
                return "Кэш"
            return "Бумага"

        def _make_positions_tree(self, parent: Any, with_account_col: bool) -> Any:
            from tkinter import ttk

            fr = ttk.Frame(parent)
            fr.pack(fill=tk.BOTH, expand=True)

            cols = (
                "account",
                "ticker",
                "name",
                "isin",
                "kind",
                "qty",
                "avg",
                "cur_price",
                "value",
            )
            if not with_account_col:
                cols = cols[1:]
            tree = ttk.Treeview(fr, columns=cols, show="headings", height=18)
            titles = {
                "account": "Счёт",
                "ticker": "Тикер",
                "name": "Название",
                "isin": "ISIN",
                "kind": "Вид",
                "qty": "Кол-во",
                "avg": "Ср. цена",
                "cur_price": "Тек. цена",
                "value": "Оценка",
            }
            for c in cols:
                tree.heading(c, text=titles[c])
                tw = 88
                if c == "name":
                    tw = 200
                elif c == "account":
                    tw = 140
                elif c == "isin":
                    tw = 120
                elif c == "ticker":
                    tw = 100
                tree.column(c, width=tw, stretch=(c == "name"))
            vsb = ttk.Scrollbar(fr, orient=tk.VERTICAL, command=tree.yview)
            hsb = ttk.Scrollbar(fr, orient=tk.HORIZONTAL, command=tree.xview)
            tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            tree.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")
            fr.grid_rowconfigure(0, weight=1)
            fr.grid_columnconfigure(0, weight=1)
            return tree

        def _make_sold_tree(self, parent: Any) -> Any:
            from tkinter import ttk

            fr = ttk.Frame(parent)
            fr.pack(fill=tk.BOTH, expand=True)
            cols = ("account", "ticker", "name", "isin", "last_date", "types")
            tree = ttk.Treeview(fr, columns=cols, show="headings", height=16)
            titles = {
                "account": "Счёт",
                "ticker": "Тикер",
                "name": "Название",
                "isin": "ISIN",
                "last_date": "Последняя операция",
                "types": "Типы в истории",
            }
            for c in cols:
                tree.heading(c, text=titles[c])
                tw = 100
                if c == "name":
                    tw = 220
                elif c == "account":
                    tw = 140
                elif c == "last_date":
                    tw = 150
                elif c == "types":
                    tw = 160
                elif c == "isin":
                    tw = 120
                tree.column(c, width=tw, stretch=(c in ("name", "types")))
            vsb = ttk.Scrollbar(fr, orient=tk.VERTICAL, command=tree.yview)
            hsb = ttk.Scrollbar(fr, orient=tk.HORIZONTAL, command=tree.xview)
            tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            tree.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")
            fr.grid_rowconfigure(0, weight=1)
            fr.grid_columnconfigure(0, weight=1)
            return tree

        def _fill_positions_tree(self, tree: Any, positions: List[dict], account_name: str, with_account: bool) -> None:
            for x in tree.get_children():
                tree.delete(x)
            for pos in sorted(positions, key=lambda p: ((p.get("ticker") or ""), (p.get("name") or ""))):
                qty = float(pos.get("quantity") or 0)
                ap = float(pos.get("average_price") or 0)
                cp = float(pos.get("current_price") or 0)
                val = qty * cp
                row = [
                    (account_name or "")[:36],
                    (pos.get("ticker") or "—")[:16],
                    (pos.get("name") or "—")[:60],
                    (pos.get("isin") or "—")[:16],
                    self._pos_kind(pos),
                    f"{qty:,.6f}".rstrip("0").rstrip("."),
                    f"{ap:,.4f}",
                    f"{cp:,.4f}",
                    f"{val:,.2f}",
                ]
                if not with_account:
                    row = row[1:]
                tree.insert("", "end", values=tuple(row))

        def _rebuild_position_tabs(self) -> None:
            from tkinter import ttk

            self._position_trees.clear()
            self._sold_tree = None
            for w in self.positions_nb_holder.winfo_children():
                w.destroy()
            if not self.broker_data:
                ttk.Label(
                    self.positions_nb_holder,
                    text="Нет данных. Загрузите портфель.",
                    foreground="#666",
                ).pack(pady=20)
                return

            nb = ttk.Notebook(self.positions_nb_holder)
            nb.pack(fill=tk.BOTH, expand=True)

            fr_all = ttk.Frame(nb, padding=4)
            nb.add(fr_all, text="Сводка (все счета)")
            tree_all = self._make_positions_tree(fr_all, with_account_col=True)
            self._position_trees["__ALL__"] = (tree_all, True)

            for acc_name in sorted(self.broker_data.keys()):
                fr = ttk.Frame(nb, padding=4)
                tab_title = acc_name[:42] + ("…" if len(acc_name) > 42 else "")
                nb.add(fr, text=tab_title)
                tree = self._make_positions_tree(fr, with_account_col=False)
                self._position_trees[acc_name] = (tree, False)

            fr_sold = ttk.Frame(nb, padding=4)
            nb.add(fr_sold, text="Нет в портфеле")
            ttk.Label(
                fr_sold,
                text=(
                    "Тикеры с операциями Buy / Sell / Amortization в выгрузке, отсутствующие в текущем ответе get_portfolio "
                    "(не считая валютных остатков). Это не отдельный API — вывод из истории операций."
                ),
                foreground="#555",
            ).pack(anchor=tk.W, pady=(0, 4))
            self._sold_tree = self._make_sold_tree(fr_sold)

            self.refresh_positions()

        def _positions_search_q(self) -> str:
            return (self.pos_search_var.get() or "").strip().lower()

        def _clear_pos_search(self) -> None:
            self.pos_search_var.set("")
            self.refresh_positions()

        def refresh_positions(self) -> None:
            if not self.broker_data or not self._position_trees:
                return
            q = self._positions_search_q()
            all_rows: List[Tuple[str, dict]] = []
            for acc_name, acc in self.broker_data.items():
                for pos in acc.get("positions", []):
                    if _position_matches_query(pos, acc_name, q):
                        all_rows.append((acc_name, pos))
            tree_all, _ = self._position_trees.get("__ALL__", (None, None))
            if tree_all:
                for x in tree_all.get_children():
                    tree_all.delete(x)
                for acc_name, pos in sorted(all_rows, key=lambda t: (t[0], t[1].get("ticker") or "")):
                    qty = float(pos.get("quantity") or 0)
                    ap = float(pos.get("average_price") or 0)
                    cp = float(pos.get("current_price") or 0)
                    val = qty * cp
                    tree_all.insert(
                        "",
                        "end",
                        values=(
                            (acc_name or "")[:36],
                            (pos.get("ticker") or "—")[:16],
                            (pos.get("name") or "—")[:60],
                            (pos.get("isin") or "—")[:16],
                            self._pos_kind(pos),
                            f"{qty:,.6f}".rstrip("0").rstrip("."),
                            f"{ap:,.4f}",
                            f"{cp:,.4f}",
                            f"{val:,.2f}",
                        ),
                    )
            for acc_name, acc in self.broker_data.items():
                entry = self._position_trees.get(acc_name)
                if not entry:
                    continue
                tree, _ = entry
                positions = [p for p in acc.get("positions", []) if _position_matches_query(p, acc_name, q)]
                self._fill_positions_tree(tree, positions, acc_name, with_account=False)

            if self._sold_tree is not None:
                for x in self._sold_tree.get_children():
                    self._sold_tree.delete(x)
                for r in collect_instruments_not_in_portfolio(self.broker_data):
                    if not _sold_row_matches_query(r, q):
                        continue
                    self._sold_tree.insert(
                        "",
                        "end",
                        values=(
                            (r["account"] or "")[:36],
                            r["ticker"][:16],
                            (r["name"] or "—")[:55],
                            (r["isin"] or "—")[:16],
                            r["last_date"][:19],
                            (r["types"] or "—")[:40],
                        ),
                    )

        def _filter_merged_operation_row(self, tx: dict) -> bool:
            t_sub = self.op_ticker_var.get().strip().upper()
            tick_full = tx.get("ticker") or ""
            if t_sub and t_sub not in tick_full.upper():
                return False
            cls_sub = self.op_class_substr_var.get().strip().upper()
            if cls_sub and cls_sub not in (tx.get("type") or "").upper():
                return False
            isin_sub = self.op_isin_var.get().strip().upper()
            if isin_sub and isin_sub not in (tx.get("isin") or "").upper():
                return False
            raw_sub = self.op_raw_type_var.get().strip().upper()
            if raw_sub and raw_sub not in (str(tx.get("tinkoff_operation_type") or "")).upper():
                return False
            src_sel = self.op_src_var.get()
            if src_sel and src_sel != OP_SRC_ALL:
                if (tx.get("_gui_src") or "") != src_sel:
                    return False
            return True

        def refresh_operations(self) -> None:
            import tkinter as tk

            for x in self.tree_ops.get_children():
                self.tree_ops.delete(x)
            self._row_tx.clear()
            self.txt_ops_json.delete("1.0", tk.END)
            self._last_filtered_ops = []
            if not self.broker_data:
                self.lbl_ops_stats.config(text="")
                self.root.title("Tinkoff import")
                return
            acc_substr, acc_idx = self.account_filter_params()
            tx_list = iter_merged_operations_for_gui(self.broker_data, acc_substr, acc_idx)
            filtered = [tx for tx in tx_list if self._filter_merged_operation_row(tx)]
            self._last_filtered_ops = filtered

            try:
                max_rows = max(100, min(50000, int(self.op_max_rows_var.get().strip() or "8000")))
            except ValueError:
                max_rows = 8000

            shown = 0
            ri = 0
            n_src = Counter()
            for tx in filtered:
                if shown >= max_rows:
                    break
                iid = f"t{ri}"
                ri += 1
                self._row_tx[iid] = tx
                shown += 1
                n_src[tx.get("_gui_src") or "?"] += 1
                price = tx.get("price")
                qty = tx.get("quantity")
                pay = tx.get("payment")
                comm = tx.get("commission")
                oid = tx.get("operation_id")
                oid_s = str(oid)[:18] if oid is not None and oid != "" else "—"
                tick_full = tx.get("ticker") or ""
                tick = tick_full[:20]
                self.tree_ops.insert(
                    "",
                    "end",
                    iid=iid,
                    values=(
                        (tx.get("date") or "")[:19],
                        (tx.get("account_name") or "")[:28],
                        (tx.get("_gui_src") or "")[:12],
                        oid_s,
                        (tx.get("type") or "—")[:12],
                        tick,
                        (tx.get("isin") or "—")[:12],
                        f"{float(price):,.4f}" if price is not None else "—",
                        f"{float(qty):,.6f}" if qty is not None else "—",
                        f"{float(pay or 0):,.2f}",
                        f"{float(comm):,.4f}" if comm is not None else "—",
                        _fmt_currency(tx.get("currency"))[:8],
                        (str(tx.get("tinkoff_operation_type") or ""))[:48],
                        (str(tx.get("_gui_reason") or ""))[:90],
                    ),
                )
            total_f = len(filtered)
            extra = f" (лимит таблицы {max_rows})" if total_f > shown else ""
            src_h = ", ".join(f"{k}={v}" for k, v in sorted(n_src.items())) if n_src else ""
            self.lbl_ops_stats.config(
                text=f"В таблице: {shown} из {total_f} после фильтров; всего в ленте по счёту: {len(tx_list)}. {src_h}{extra}",
            )
            self.root.title(f"Tinkoff import — операции: {shown}/{total_f}")

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

        def save_analytics_file(self) -> None:
            if not self.txt_analytics.get("1.0", tk.END).strip():
                messagebox.showinfo("Аналитика", "Нет текста для сохранения.")
                return
            path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Текст", "*.txt"), ("Все файлы", "*.*")],
                title="Сохранить сводку",
            )
            if not path:
                return
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.txt_analytics.get("1.0", tk.END))
            except OSError as e:
                messagebox.showerror("Ошибка", str(e))
                return
            messagebox.showinfo("Сохранено", path)

        def copy_analytics_clipboard(self) -> None:
            txt = self.txt_analytics.get("1.0", tk.END)
            if not txt.strip():
                return
            self.root.clipboard_clear()
            self.root.clipboard_append(txt)
            self.root.update_idletasks()

        def export_operations_json(self) -> None:
            rows = self._last_filtered_ops
            if not rows:
                messagebox.showinfo("Экспорт", "Нет строк: загрузите данные и нажмите «Применить».")
                return
            path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON", "*.json"), ("Все файлы", "*.*")],
                title="Экспорт операций (JSON)",
            )
            if not path:
                return
            serializable = [operations_to_json_serializable(tx) for tx in rows]
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(serializable, f, ensure_ascii=False, indent=2, default=str)
            except OSError as e:
                messagebox.showerror("Ошибка", str(e))
                return
            messagebox.showinfo("Экспорт", f"Записано {len(serializable)} операций.\n{path}")

        def export_operations_csv(self) -> None:
            import csv

            rows = self._last_filtered_ops
            if not rows:
                messagebox.showinfo("Экспорт", "Нет строк: загрузите данные и нажмите «Применить».")
                return
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV", "*.csv"), ("Все файлы", "*.*")],
                title="Экспорт операций (CSV)",
            )
            if not path:
                return
            fieldnames = [
                "date",
                "account_name",
                "_gui_src",
                "operation_id",
                "type",
                "ticker",
                "isin",
                "price",
                "quantity",
                "payment",
                "commission",
                "currency",
                "tinkoff_operation_type",
                "_gui_reason",
            ]
            try:
                with open(path, "w", encoding="utf-8-sig", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                    w.writeheader()
                    for tx in rows:
                        row = {k: tx.get(k) for k in fieldnames}
                        row["currency"] = _fmt_currency(tx.get("currency"))
                        w.writerow(row)
            except OSError as e:
                messagebox.showerror("Ошибка", str(e))
                return
            messagebox.showinfo("Экспорт", f"Записано {len(rows)} строк.\n{path}")

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

        def on_account_combo_change(self) -> None:
            self.refresh_analytics()
            self.refresh_operations()
            self.refresh_raw_only()

        def refresh_after_load(self) -> None:
            self._rebuild_position_tabs()
            self.refresh_analytics()
            self.refresh_operations()
            self.refresh_raw_only()

        def on_tree_ops_select(self, _evt: Any = None) -> None:
            import tkinter as tk

            self.txt_ops_json.delete("1.0", tk.END)
            sel = self.tree_ops.selection()
            if not sel:
                return
            tx = self._row_tx.get(sel[0])
            if not tx:
                return
            out: Any = {k: v for k, v in tx.items() if not str(k).startswith("_") or k in ("_gui_src", "_gui_reason")}
            if tx.get("_raw_snapshot"):
                out["_raw_snapshot"] = tx["_raw_snapshot"]
            try:
                blob = json.dumps(out, ensure_ascii=False, indent=2, default=str)
            except TypeError:
                blob = json.dumps({k: str(v) for k, v in out.items()}, ensure_ascii=False, indent=2)
            self.txt_ops_json.insert(tk.END, blob)

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
                self.root.title("Tinkoff import")
                return
            self.broker_data = data or {}
            names = sorted(self.broker_data.keys())
            self.combo_acc["values"] = [ALL_ACCOUNTS] + names
            self.account_var.set(ALL_ACCOUNTS)
            self.refresh_after_load()
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
        help="Окно: позиции (поиск), аналитика (сохранить/копировать), операции (фильтры, экспорт JSON/CSV), сырые API.",
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
    parser.add_argument(
        "--skip-raw-operations",
        action="store_true",
        help="Не запрашивать operations_raw у API (быстрее; в сводке «Слито ком.» и сопоставимый API будут «—»).",
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
        need_raw_ticker = bool(args.raw_ticker and args.raw_ticker.strip())
        include_raw = need_raw_ticker or (not args.raw_only and not args.skip_raw_operations)
        print("\n📥 Получаем данные от брокера Tinkoff...")
        broker_data = get_tinkoff_portfolio(token, include_raw_operations=include_raw)

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

        if need_raw_ticker:
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
