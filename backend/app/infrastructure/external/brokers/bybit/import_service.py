"""
Сервис импорта данных из Bybit.
Перенесено из services/integrations/bybit_import.py
"""
import sys
import time
from datetime import datetime, timedelta

try:
    from pybit.unified_trading import HTTP
except ImportError:
    print("Ошибка: библиотека pybit не установлена.", file=sys.stderr)
    print("Установите её командой: pip install pybit", file=sys.stderr)
    sys.exit(1)

# --- Дата старта ---
BYBIT_START_DATE = datetime(2025, 8, 1)

# --- Маппинг типов ---
TRANSACTION_TYPE_MAP = {
    ('TRADE', 'Buy'): 'buy',
    ('TRADE', 'Sell'): 'sell',
    ('SETTLEMENT', 'Buy'): 'pnl_plus',
    ('SETTLEMENT', 'Sell'): 'pnl_minus',
    ('FEE', 'Buy'): 'fee',
    ('FEE', 'Sell'): 'fee',
    ('FEE', ''): 'fee',
    ('AIRDROP', ''): 'airdrop',
    ('BONUS', ''): 'bonus',
}


def merge_by_tx_prefix(transactions):
    """Объединение дублей по ID."""
    merged = {}
    for tx in transactions:
        prefix = tx["tx_id"].split("_")[0]
        if prefix in merged:
            m = merged[prefix]
            total_qty = m["quantity"] + tx["quantity"]
            if total_qty != 0:
                m["price"] = (
                    (m["price"] * abs(m["quantity"]) + tx["price"] * abs(tx["quantity"]))
                    / (abs(m["quantity"]) + abs(tx["quantity"]))
                )
            m["quantity"] = total_qty
        else:
            merged[prefix] = tx.copy()
    return list(merged.values())


def _fetch_transaction_log(session, start_ms, end_ms, processed_tx_ids):
    """Unified account log"""
    transactions = []
    cursor = None
    while True:
        try:
            resp = session.get_transaction_log(
                accountType="UNIFIED", limit=50, cursor=cursor,
                startTime=start_ms, endTime=end_ms
            )
            if resp.get("retCode") != 0:
                print(f"⚠️ Ошибка Transaction Log: {resp.get('retMsg')}")
                break

            data = resp.get("result", {}).get("list", [])
            for t in data:
                tx_id = t.get("id")
                if not tx_id or tx_id in processed_tx_ids:
                    continue
                processed_tx_ids.add(tx_id)

                tx_type_str = t.get("type", "")
                tx_side = t.get("side", "")
                tx_type = TRANSACTION_TYPE_MAP.get((tx_type_str.upper(), tx_side)) or tx_type_str.lower()

                symbol = t.get("symbol") or t.get("currency")
                if not symbol:
                    continue

                qty = float(t.get("qty", 0))
                price = float(t.get("tradePrice", 1)) or 1
                ts = datetime.fromtimestamp(int(t.get("transactionTime", 0)) / 1000)

                transactions.append({
                    "figi": symbol,
                    "type": tx_type,
                    "price": price,
                    "quantity": qty,
                    "date": ts,
                    "tx_id": tx_id
                })

            cursor = resp.get("result", {}).get("nextPageCursor")
            if not cursor or not data:
                break
            time.sleep(0.2)
        except Exception as e:
            print(f"❌ Ошибка при получении Unified Log: {e}")
            break
    return transactions


def _fetch_executions(session, start_ms, end_ms, processed_tx_ids):
    """История исполнений (ордеров)"""
    transactions = []
    try:
        resp = session.get_executions(category="linear", limit=1000, startTime=start_ms, endTime=end_ms)
        if resp.get("retCode") != 0:
            return []
        for t in resp.get("result", {}).get("list", []):
            tx_id = t.get("execId")
            if not tx_id or tx_id in processed_tx_ids:
                continue
            processed_tx_ids.add(tx_id)

            side = t.get("side", "").lower()
            qty = float(t.get("execQty", 0))
            price = float(t.get("execPrice", 0))
            if side == "sell": qty = -abs(qty)

            ts = datetime.fromtimestamp(int(t["execTime"]) / 1000)
            symbol = t.get("symbol")

            transactions.append({
                "figi": symbol,
                "type": side,
                "price": price,
                "quantity": qty,
                "date": ts,
                "tx_id": tx_id
            })
    except Exception as e:
        print(f"❌ Ошибка при получении исполнений: {e}")
    return transactions


def _fetch_closed_pnl(session, start_ms, end_ms, processed_tx_ids):
    """История закрытых позиций (прибыль/убыток)"""
    transactions = []
    try:
        resp = session.get_closed_pnl(category="linear", limit=200, startTime=start_ms, endTime=end_ms)
        if resp.get("retCode") != 0:
            return []
        for t in resp.get("result", {}).get("list", []):
            tx_id = t.get("id")
            if not tx_id or tx_id in processed_tx_ids:
                continue
            processed_tx_ids.add(tx_id)

            symbol = t.get("symbol")
            pnl = float(t.get("closedPnl", 0))
            ts = datetime.fromtimestamp(int(t.get("updatedTime", 0)) / 1000)

            transactions.append({
                "figi": symbol,
                "type": "pnl",
                "price": 1.0,
                "quantity": pnl,
                "date": ts,
                "tx_id": tx_id
            })
    except Exception as e:
        print(f"❌ Ошибка при получении Closed PnL: {e}")
    return transactions


def _fetch_deposits(session, start_ms, end_ms, processed_tx_ids):
    transactions = []
    try:
        resp = session.get_deposit_records(limit=50, startTime=start_ms, endTime=end_ms)
        if resp.get("retCode") != 0:
            return []
        for t in resp.get("result", {}).get("rows", []):
            tx_id = t.get("txID")
            if not tx_id or tx_id in processed_tx_ids:
                continue
            processed_tx_ids.add(tx_id)

            if int(t.get("status", 0)) != 1:
                continue

            symbol = t.get("coin")
            amount = float(t.get("amount", 0))
            ts = datetime.fromtimestamp(int(t.get("updateTime", 0)) / 1000)

            transactions.append({
                "figi": symbol,
                "type": "deposit",
                "price": 1.0,
                "quantity": abs(amount),
                "date": ts,
                "tx_id": tx_id
            })
    except Exception as e:
        print(f"❌ Ошибка при получении депозитов: {e}")
    return transactions


def _fetch_withdrawals(session, start_ms, end_ms, processed_tx_ids):
    transactions = []
    try:
        resp = session.get_withdrawal_records(limit=50, startTime=start_ms, endTime=end_ms)
        if resp.get("retCode") != 0:
            return []
        for t in resp.get("result", {}).get("rows", []):
            tx_id = t.get("withdrawId")
            if not tx_id or tx_id in processed_tx_ids:
                continue
            processed_tx_ids.add(tx_id)

            status = t.get("status", "").lower()
            if status not in ["success", "completed", "ok", "securitycheckingsuccess"]:
                continue

            symbol = t.get("coin")
            amount = float(t.get("amount", 0))
            ts = datetime.fromtimestamp(int(t.get("createTime", 0)) / 1000)

            transactions.append({
                "figi": symbol,
                "type": "withdraw",
                "price": 1.0,
                "quantity": -abs(amount),
                "date": ts,
                "tx_id": tx_id
            })

            fee = float(t.get("withdrawFee", 0))
            if fee > 0:
                transactions.append({
                    "figi": symbol,
                    "type": "fee",
                    "price": 1.0,
                    "quantity": -abs(fee),
                    "date": ts,
                    "tx_id": f"{tx_id}_fee"
                })
    except Exception as e:
        print(f"❌ Ошибка при получении выводов: {e}")
    return transactions


def get_bybit_data(api_key, api_secret):
    """Получает данные портфеля от брокера Bybit."""
    try:
        session = HTTP(testnet=False, api_key=api_key, api_secret=api_secret)
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        return {}

    all_tx = []
    processed_tx_ids = set()
    start = BYBIT_START_DATE
    end = datetime.now()

    print(f"📥 Загрузка истории с {start.date()} по {end.date()}")

    while start < end:
        end_ = min(start + timedelta(days=7), end)
        s_ms, e_ms = int(start.timestamp() * 1000), int(end_.timestamp() * 1000)
        print(f"  → Период: {start.date()} → {end_.date()}")

        all_tx += _fetch_transaction_log(session, s_ms, e_ms, processed_tx_ids)
        all_tx += _fetch_executions(session, s_ms, e_ms, processed_tx_ids)
        all_tx += _fetch_closed_pnl(session, s_ms, e_ms, processed_tx_ids)
        all_tx += _fetch_deposits(session, s_ms, e_ms, processed_tx_ids)
        all_tx += _fetch_withdrawals(session, s_ms, e_ms, processed_tx_ids)

        start = end_ + timedelta(seconds=1)
        time.sleep(0.2)

    all_tx = merge_by_tx_prefix(all_tx)
    all_tx.sort(key=lambda x: x["date"])

    print(f"\n✅ Всего транзакций собрано: {len(all_tx)}")
    return {"Bybit (All)": {"transactions": all_tx}}
