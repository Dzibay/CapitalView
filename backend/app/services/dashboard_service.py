from collections import defaultdict
from app.services.portfolio_service import get_user_portfolios_with_assets_and_history
from app.services.reference_service import get_reference_data_cached
from app.services.transactions_service import get_transactions
from app.services.user_service import get_user_by_email
from app.services.supabase_service import table_select
from collections import defaultdict
from time import time

def aggregate_and_sort_history_list(history_list):
    """Агрегирует историю по датам и сортирует"""
    combined = defaultdict(float)
    for h in history_list or []:
        date = h.get("date") or h.get("report_date")
        value = float(h.get("value") or h.get("total_value") or 0)
        if date:
            combined[date] += value
    return [{"date": d, "value": round(v, 2)} for d, v in sorted(combined.items())]


def sum_portfolio_totals_bottom_up(portfolio_id, portfolio_map):
    portfolio = portfolio_map[portfolio_id]

    # Берём активы текущего портфеля
    combined_assets = list(portfolio.get("assets") or [])
    combined_history = list(portfolio.get("history") or [])

    # 🔹 Добавляем данные дочерних портфелей
    children = [p for p in portfolio_map.values() if p.get("parent_portfolio_id") == portfolio_id]
    for child in children:
        _, _, child_assets, child_history = sum_portfolio_totals_bottom_up(child["id"], portfolio_map)
        combined_history.extend(child_history)

        # 🧩 Объединяем активы без дублирования
        existing = {a["asset_id"]: a for a in combined_assets}
        for ca in child_assets:
            aid = ca["asset_id"]
            if aid in existing:
                old = existing[aid]
                q1, q2 = float(old["quantity"] or 0), float(ca["quantity"] or 0)
                if q2 > 0:
                    new_qty = q1 + q2
                    new_avg_price = (
                        (q1 * float(old.get("average_price") or 0)) +
                        (q2 * float(ca.get("average_price") or 0))
                    ) / new_qty if new_qty else 0
                    old["quantity"] = new_qty
                    old["average_price"] = new_avg_price
                if ca.get("last_price") and not old.get("last_price"):
                    old["last_price"] = ca["last_price"]
            else:
                combined_assets.append(ca)

    # 🔹 Теперь считаем стоимость только по объединённым активам (ОДИН раз)
    total_value = sum(
        float(a.get("quantity") or 0)
        * float(a.get("last_price") or 0)
        * float(a.get("currency_rate_to_rub") or 1)
        / float(a.get("leverage") or 1)
        for a in combined_assets
    )

    total_invested = sum(
        float(a.get("quantity") or 0)
        * float(a.get("average_price") or 0)
        * float(a.get("currency_rate_to_rub") or 1)
        / float(a.get("leverage") or 1)
        for a in combined_assets
    )

    portfolio["total_value"] = round(total_value, 2)
    portfolio["total_invested"] = round(total_invested, 2)
    portfolio["combined_assets"] = combined_assets
    portfolio["asset_allocation"] = calculate_asset_allocation(combined_assets)
    portfolio["history"] = aggregate_and_sort_history_list(combined_history)

    return total_value, total_invested, combined_assets, combined_history



def build_portfolio_hierarchy(portfolios):
    """
    Запускает рекурсивное суммирование для всех портфелей.
    """
    portfolio_map = {p["id"]: p for p in portfolios}
    root_portfolios = [p for p in portfolios if not p.get("parent_portfolio_id")]

    for root in root_portfolios:
        sum_portfolio_totals_bottom_up(root["id"], portfolio_map)

    return list(portfolio_map.values())


def calculate_asset_allocation(assets):
    """
    Считает распределение активов для ОДНОГО портфеля 
    (на основе переданного списка всех его активов, вкл. дочерние).
    """
    if not assets:
        return {"labels": [], "datasets": [{"backgroundColor": [], "data": []}]}
    
    allocation = {}
    for asset in assets or []:  # ← безопасно
        atype = asset.get("type")
        if not atype:
            continue
        quantity = float(asset.get("quantity") or 0.0)
        price = float(asset.get("last_price") or 0.0)
        currency_multiplier = float(asset.get("currency_rate_to_rub") or 1.0)
        allocation[atype] = allocation.get(atype, 0) + (
            quantity * price * currency_multiplier / float(asset.get("leverage") or 1.0)
        )

    return {
        "labels": list(allocation.keys()),
        "datasets": [{
            "backgroundColor": [
                '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6',
                '#10b981', '#f472b6', '#60a5fa', '#fbbf24', '#a78bfa'
            ],
            "data": list(allocation.values())
        }]
    }


def calculate_monthly_change(history):
    if len(history) >= 2:
        try:
            return history[-1]['value'] - history[-30]['value']
        except:
            return history[-1]['value']
    elif len(history) == 1:
        return history[0]['value']
    else:
        return 0


def get_user_portfolio_connections(user_id):
    """
    Возвращает dict: { portfolio_id: {'broker_id': ..., 'api_key': ...} }
    Берём самую свежую запись по last_sync_at для каждого портфеля.
    """
    rows = table_select(
        "user_broker_connections",
        select="portfolio_id, broker_id, api_key, last_sync_at",
        filters={"user_id": user_id},
        order={"column": "last_sync_at", "desc": True},
        limit=1000
    ) or []  # table_select из supabase_service.py
    # rows уже отсортированы по last_sync_at DESC — первое попадание и есть самое свежее
    by_portfolio = {}
    for r in rows:
        pid = r.get("portfolio_id")
        if pid and pid not in by_portfolio:
            by_portfolio[pid] = {
                "broker_id": r.get("broker_id"),
                "api_key": r.get("api_key"),
            }
    return by_portfolio


async def get_dashboard_data(user_email: str):
    user = get_user_by_email(user_email)
    if not user:
        return None

    user_id = user['id']
    time1 = time()
    # Получаем всё сразу из PostgreSQL
    portfolios = get_user_portfolios_with_assets_and_history(user_id) or []
    print(f'SQL RPC: {time() - time1}')
    time1 = time()

    # ⬇️ подмешиваем connection к каждому портфелю
    connections_by_pid = get_user_portfolio_connections(user_id)  # читает user_broker_connections
    for p in portfolios:
        p["connection"] = connections_by_pid.get(p["id"])

    # === 1️⃣ Объединяем дочерние портфели и пересчитываем суммы ===
    portfolios = build_portfolio_hierarchy(portfolios)
    print(f'Иерархия: {time() - time1}')

    time1 = time()
    reference_data = get_reference_data_cached()
    print(f'Reference data: {time() - time1}')
    time1 = time()
    transactions = get_transactions(user_id, limit=1000) or []
    print(f'Транзакции: {time() - time1}')

    time1 = time()
    # Обрабатываем историю и считаем динамику
    for p in portfolios:
        hist = p.get('history')
        if not isinstance(hist, list):
            hist = []

        sorted_hist = sorted(
            [h for h in hist if isinstance(h, dict) and 'date' in h and 'value' in h],
            key=lambda x: x['date']
        )

        p['history'] = {
            'labels': [h['date'] for h in sorted_hist],
            'data': [h['value'] for h in sorted_hist]
        }
        p['monthly_change'] = calculate_monthly_change(sorted_hist)
        p['asset_allocation'] = calculate_asset_allocation(p.get('combined_assets') or p.get('assets', []))
    print(f'Форматирование: {time() - time1}')

    # Сортировка по стоимости
    portfolios = sorted(portfolios, key=lambda x: x.get('total_value', 0), reverse=True)

    return {
        "portfolios": portfolios,
        "transactions": transactions,
        "referenceData": reference_data
    }
