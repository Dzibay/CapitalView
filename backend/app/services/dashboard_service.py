from collections import defaultdict
from time import time
from app.services.portfolio_service import get_user_portfolios_with_assets_and_history
from app.services.reference_service import get_reference_data_cached
# Транзакции загружаются отдельным запросом в фоне
# from app.services.transactions_service import get_transactions
from app.services.user_service import get_user_by_email
from app.services.broker_connections_service import get_user_portfolio_connections

def aggregate_and_sort_history_list(history_list):
    """Агрегирует историю по датам: стоимость + инвестиции, и сортирует"""
    combined = defaultdict(lambda: {"value": 0.0, "invested": 0.0, "payouts": 0.0, "pnl": 0.0})

    for h in history_list or []:
        date = h.get("date") or h.get("report_date")
        if not date:
            continue

        combined[date]["value"] += float(h.get("value") or 0)
        combined[date]["invested"] += float(h.get("invested") or 0)
        combined[date]["payouts"] += float(h.get("payouts") or 0)
        combined[date]["pnl"] += float(h.get("pnl") or 0)

    return [
        {"date": d, "value": round(v["value"], 2), "invested": round(v["invested"], 2), "payouts": round(v["payouts"], 2), "pnl": round(v["pnl"], 2)}
        for d, v in sorted(combined.items())
    ]



def sum_portfolio_totals_bottom_up(portfolio_id, portfolio_map):
    portfolio = portfolio_map[portfolio_id]

    # 1️⃣ Активы + история
    combined_assets = list(portfolio.get("assets") or [])
    combined_history = list(portfolio.get("history") or [])

    # 2️⃣ Аналитика текущего портфеля (если есть)
    analytics = portfolio.get("analytics") or {}
    combined_analytics = {
        "realized_pl": float(analytics.get("realized_pl", 0)),
        "unrealized_pl": float(analytics.get("unrealized_pl", 0)),
        "dividends": float(analytics.get("dividends", 0)),
        "coupons": float(analytics.get("coupons", 0)),
        "commissions": float(analytics.get("commissions", 0)),
        "taxes": float(analytics.get("taxes", 0)),
        "inflow": float((analytics.get("cash_flow") or {}).get("inflow", 0)),
        "outflow": float((analytics.get("cash_flow") or {}).get("outflow", 0)),
    }

    # 3️⃣ Рекурсивно добавляем данные дочерних портфелей
    children = [
        p for p in portfolio_map.values()
        if p.get("parent_portfolio_id") == portfolio_id
    ]

    for child in children:
        (
            child_value,
            child_invested,
            child_assets,
            child_history,
            child_analytics
        ) = sum_portfolio_totals_bottom_up(child["id"], portfolio_map)

        # История
        combined_history.extend(child_history)

        # Активы — объединение
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

        # 4️⃣ Аналитика — суммирование
        combined_analytics["realized_pl"] += child_analytics.get("realized_pl", 0)
        combined_analytics["unrealized_pl"] += child_analytics.get("unrealized_pl", 0)
        combined_analytics["dividends"] += child_analytics.get("dividends", 0)
        combined_analytics["coupons"] += child_analytics.get("coupons", 0)
        combined_analytics["commissions"] += child_analytics.get("commissions", 0)
        combined_analytics["taxes"] += child_analytics.get("taxes", 0)
        combined_analytics["inflow"] += child_analytics.get("inflow", 0)
        combined_analytics["outflow"] += child_analytics.get("outflow", 0)

    # 5️⃣ После объединения активов — пересчёт общей стоимости
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

    # 6️⃣ Пересчёт итоговой прибыли
    total_profit = (
        combined_analytics["realized_pl"] +
        combined_analytics["unrealized_pl"] +
        combined_analytics["dividends"] +
        combined_analytics["coupons"] +
        combined_analytics["commissions"] +
        combined_analytics["taxes"]
    )

    return_percent = (
        total_profit / total_invested
        if total_invested > 0 else 0
    )

    # 7️⃣ Сохраняем результат в текущем портфеле
    portfolio["total_value"] = round(total_value, 2)
    portfolio["total_invested"] = round(total_invested, 2)
    portfolio["combined_assets"] = combined_assets
    portfolio["history"] = aggregate_and_sort_history_list(combined_history)
    portfolio["asset_allocation"] = calculate_asset_allocation(combined_assets)

    portfolio["analytics"] = {
        "total_value": total_value,
        "total_invested": total_invested,
        "realized_pl": combined_analytics["realized_pl"],
        "unrealized_pl": combined_analytics["unrealized_pl"],
        "dividends": combined_analytics["dividends"],
        "coupons": combined_analytics["coupons"],
        "commissions": combined_analytics["commissions"],
        "taxes": combined_analytics["taxes"],
        "total_profit": total_profit,
        "return_percent": return_percent,
        "cash_flow": {
            "inflow": combined_analytics["inflow"],
            "outflow": combined_analytics["outflow"],
        }
    }

    return total_value, total_invested, combined_assets, combined_history, combined_analytics


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
    time1 = time()
    connections_by_pid = get_user_portfolio_connections(user_id)  # читает user_broker_connections
    for p in portfolios:
        p["connection"] = connections_by_pid.get(p["id"])
    print(f'Соединения: {time() - time1}')

    # === 1️⃣ Объединяем дочерние портфели и пересчитываем суммы ===
    portfolios = build_portfolio_hierarchy(portfolios)
    print(f'Иерархия: {time() - time1}')

    time1 = time()
    reference_data = get_reference_data_cached()
    print(f'Reference data: {time() - time1}')
    
    # Транзакции не загружаем при инициализации - они загружаются в фоне отдельным запросом
    transactions = []

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
            'data_value': [h['value'] for h in sorted_hist],
            'data_invested': [h['invested'] for h in sorted_hist],
            'data_payouts': [h['payouts'] for h in sorted_hist],
            'data_pnl': [h['pnl'] for h in sorted_hist]
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
