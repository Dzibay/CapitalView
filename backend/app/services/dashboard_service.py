from collections import defaultdict
from app.services.portfolio_service import get_portfolios_with_assets_and_history
from app.services.reference_service import get_reference_data
from app.services.transactions_service import get_transactions
from app.services.user_service import get_user_by_email


def calculate_asset_allocation(assets):
    """
    Считает распределение активов для ОДНОГО портфеля 
    (на основе переданного списка всех его активов, вкл. дочерние).
    """
    allocation = {}
    for asset in assets:
        atype = asset.get("type")
        if not atype:
            continue
        quantity = float(asset.get("quantity") or 0.0)
        price = float(asset.get("last_price") or 0.0)
        currency_multiplier = float(asset.get("currency_rate_to_rub") or 1.0)
        allocation[atype] = allocation.get(atype, 0) + quantity * price * currency_multiplier / float(asset.get("leverage") or 1.0)

    return {
        "labels": list(allocation.keys()),
        "datasets": [{
            "backgroundColor": ['#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#10b981', '#f472b6', '#60a5fa', '#fbbf24', '#a78bfa'],
            "data": list(allocation.values())
        }]
    }


def aggregate_and_sort_history_list(history_list):
    """
    Агрегирует ПЛОСКИЙ СПИСОК точек истории и возвращает 
    отсортированный список словарей в формате [{'date': ..., 'value': ...}].
    Используется для КАЖДОГО портфеля.
    """
    combined = defaultdict(float)
    for h in history_list or []:
        date = h.get("report_date")
        value = float(h.get("total_value") or 0)
        if date:
            combined[date] += value

    # Сортируем по дате (ключу)
    sorted_items = sorted(combined.items())
    
    # Возвращаем в требуемом формате
    return [
        {"date": d, "value": round(v, 2)}
        for d, v in sorted_items
    ]


def sum_portfolio_totals_bottom_up(portfolio_id, portfolio_map, asset_map, history_map):
    """
    Рекурсивная функция для суммирования.
    Модифицирует `portfolio` в `portfolio_map` НА МЕСТЕ,
    добавляя в него 'asset_allocation' и 'history'.
    """
    portfolio = portfolio_map[portfolio_id]
    
    # 1. Берем собственные активы и историю портфеля
    combined_assets = asset_map.get(portfolio_id, []).copy()
    combined_history_list = history_map.get(portfolio_id, []).copy() 

    total_value = portfolio.get("total_value") or 0
    total_invested = portfolio.get("total_invested") or 0

    # 2. Рекурсивно обрабатываем дочерние портфели
    children = [p for p in portfolio_map.values() if p.get("parent_portfolio_id") == portfolio_id]
    for child in children:
        # Рекурсивный вызов вернет СУММАРНЫЕ данные ребенка
        child_value, child_invested, child_assets, child_history_list = sum_portfolio_totals_bottom_up(
            child["id"], portfolio_map, asset_map, history_map
        )
        
        # 3. Добавляем данные ребенка к текущему портфелю
        total_value += child_value
        total_invested += child_invested
        combined_assets.extend(child_assets) # Добавляем активы ребенка
        asset_map[portfolio_id] = combined_assets
        combined_history_list.extend(child_history_list) # Добавляем точки истории ребенка

    # 4. Обновляем сам портфель в portfolio_map (in-place)
    portfolio["total_value"] = round(total_value, 2)
    portfolio["total_invested"] = round(total_invested, 2)
    
    # Считаем аллокацию на основе ПОЛНОГО списка активов (своих + дочерних)
    portfolio["asset_allocation"] = calculate_asset_allocation(combined_assets)
    
    # Агрегируем и форматируем ПОЛНЫЙ список истории в нужный вам формат
    portfolio["history"] = aggregate_and_sort_history_list(combined_history_list)

    # 5. Возвращаем сырые данные для родителя
    return total_value, total_invested, combined_assets, combined_history_list


def build_portfolio_hierarchy(portfolios, histories):
    """
    Эта функция запускает 'sum_portfolio_totals_bottom_up' для каждого портфеля,
    гарантируя, что 'asset_allocation' и 'history' посчитаны для каждого.
    """
    
    portfolio_map = {p['id']: p for p in portfolios}

    asset_map = defaultdict(list)
    
    for p in portfolios:
        asset_map[p["id"]] = p["assets"]

    history_map = defaultdict(list)
    for pid, hlist in histories.items():
        history_map[pid] = hlist or []

    root_portfolios = [p for p in portfolios if not p.get('parent_portfolio_id')]
    for root in root_portfolios:
        sum_portfolio_totals_bottom_up(root['id'], portfolio_map, asset_map, history_map)


    return list(portfolio_map.values())


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
    """
    (ИЗМЕНЕНА)
    Убрана функция combine_histories и поле combined_history из ответа.
    """
    user = get_user_by_email(user_email)
    if not user:
        return None

    user_id = user['id']

    portfolios, assets, histories = await get_portfolios_with_assets_and_history(user_email)
    if not portfolios:
        return {
            "portfolios": [],
            "transactions": [],
            "referenceData": {}
        }

    portfolios = build_portfolio_hierarchy(portfolios, histories)
    
    reference_data = get_reference_data()
    transactions = get_transactions(user_id) or []

    for p in portfolios:
        hist = p.get('history', [])
        
        # сортируем по дате
        sorted_hist = sorted(hist, key=lambda x: x['date'])
        
        p['history'] = {
            'labels': [item['date'] for item in sorted_hist],
            'data': [item['value'] for item in sorted_hist]
        }

        # добавляем monthly_change
        p['monthly_change'] = calculate_monthly_change(sorted_hist)

    return {
        "portfolios": portfolios,
        "transactions": transactions,
        "referenceData": reference_data
    }