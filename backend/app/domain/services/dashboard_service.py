from collections import defaultdict
from datetime import datetime, timedelta
from time import time
import copy
from app.domain.services.portfolio_service import get_user_portfolios_with_assets_and_history
from app.domain.services.reference_service import get_reference_data_cached
from app.domain.services.user_service import get_user_by_email
from app.domain.services.broker_connections_service import get_user_portfolio_connections
from app.core.logging import get_logger
from app.utils.date import normalize_date_to_day_string

logger = get_logger(__name__)

def _get_aggregated_history(portfolio_map, portfolio_id, fallback_history=None):
    """Получает агрегированную историю из портфеля или возвращает fallback"""
    portfolio = portfolio_map.get(portfolio_id)
    return (portfolio.get("history") if portfolio else None) or fallback_history or []


def forward_fill_history(history_list):
    """
    Заполняет пропущенные даты последним известным значением (forward fill).
    Это необходимо для корректного объединения истории дочерних портфелей,
    у которых могут быть разные диапазоны дат.
    """
    if not history_list:
        return []
    
    # Сортируем по датам
    sorted_history = sorted(
        history_list,
        key=lambda h: normalize_date_to_day_string(h.get("date") or h.get("report_date")) or ""
    )
    
    if not sorted_history:
        return []
    
    # Находим диапазон дат: от первой до последней
    first_date_str = normalize_date_to_day_string(
        sorted_history[0].get("date") or sorted_history[0].get("report_date")
    )
    last_date_str = normalize_date_to_day_string(
        sorted_history[-1].get("date") or sorted_history[-1].get("report_date")
    )
    
    if not first_date_str or not last_date_str:
        return sorted_history
    
    first_date = datetime.strptime(first_date_str, "%Y-%m-%d").date()
    last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
    
    # Создаем словарь для быстрого доступа по датам
    history_by_date = {}
    for h in sorted_history:
        date_str = normalize_date_to_day_string(h.get("date") or h.get("report_date"))
        if date_str:
            history_by_date[date_str] = h
    
    # Заполняем пропущенные даты
    filled_history = []
    current_values = {
        "value": 0.0,
        "invested": 0.0,
        "payouts": 0.0,
        "pnl": 0.0
    }
    
    current_date = first_date
    while current_date <= last_date:
        date_str = current_date.isoformat()
        
        if date_str in history_by_date:
            # Есть запись на эту дату - обновляем текущие значения
            h = history_by_date[date_str]
            current_values = {
                "value": float(h.get("value") or 0),
                "invested": float(h.get("invested") or 0),
                "payouts": float(h.get("payouts") or 0),
                "pnl": float(h.get("pnl") or 0)
            }
        # Иначе используем последние известные значения (forward fill)
        
        filled_history.append({
            "date": date_str,
            "value": current_values["value"],
            "invested": current_values["invested"],
            "payouts": current_values["payouts"],
            "pnl": current_values["pnl"]
        })
        
        current_date += timedelta(days=1)
    
    return filled_history


def aggregate_and_sort_history_list(history_list):
    """Агрегирует историю по датам: стоимость + инвестиции, и сортирует"""
    combined = defaultdict(lambda: {"value": 0.0, "invested": 0.0, "payouts": 0.0, "pnl": 0.0})

    for h in history_list or []:
        date_raw = h.get("date") or h.get("report_date")
        if not date_raw:
            continue
        
        date = normalize_date_to_day_string(date_raw)
        if not date:
            logger.warning(f"Не удалось нормализовать дату: {date_raw} (тип: {type(date_raw)})")
            continue

        combined[date]["value"] += float(h.get("value") or 0)
        combined[date]["invested"] += float(h.get("invested") or 0)
        combined[date]["payouts"] += float(h.get("payouts") or 0)
        combined[date]["pnl"] += float(h.get("pnl") or 0)

    return [
        {"date": d, "value": round(v["value"], 2), "invested": round(v["invested"], 2), 
         "payouts": round(v["payouts"], 2), "pnl": round(v["pnl"], 2)}
        for d, v in sorted(combined.items())
    ]



def sum_portfolio_totals_bottom_up(portfolio_id, portfolio_map):
    portfolio = portfolio_map[portfolio_id]

    # 1️⃣ Активы + история
    # Создаем глубокие копии, чтобы не модифицировать оригинальные данные
    combined_assets = [copy.deepcopy(a) for a in (portfolio.get("assets") or [])]
    combined_history = list(portfolio.get("history") or [])
    portfolio_name = portfolio.get("name", "N/A")

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
    
    # Собираем данные дочерних портфелей и находим максимальную дату
    child_data_list = []
    max_child_date = None
    
    def _get_max_date_from_history(history_list):
        """Вспомогательная функция для поиска максимальной даты в истории"""
        max_date = None
        for h in history_list or []:
            date_str = normalize_date_to_day_string(h.get("date") or h.get("report_date"))
            if date_str and (max_date is None or date_str > max_date):
                max_date = date_str
        return max_date
    
    for child in children:
        (
            child_value,
            child_invested,
            child_assets,
            child_history,
            child_analytics
        ) = sum_portfolio_totals_bottom_up(child["id"], portfolio_map)
        
        child_data_list.append({
            "child": child,
            "value": child_value,
            "invested": child_invested,
            "assets": child_assets,
            "history": child_history,
            "analytics": child_analytics
        })
        
        # Находим максимальную дату в агрегированной истории дочернего портфеля
        child_history_agg = _get_aggregated_history(portfolio_map, child["id"], child_history)
        child_max_date = _get_max_date_from_history(child_history_agg)
        if child_max_date and (max_child_date is None or child_max_date > max_child_date):
            max_child_date = child_max_date

    # Проверяем максимальную дату в собственной истории родителя
    parent_max_date = _get_max_date_from_history(combined_history)
    if parent_max_date and (max_child_date is None or parent_max_date > max_child_date):
        max_child_date = parent_max_date

    # Обрабатываем каждый дочерний портфель с учетом максимальной даты
    for child_data in child_data_list:
        child = child_data["child"]
        child_value = child_data["value"]
        child_invested = child_data["invested"]
        child_assets = child_data["assets"]
        child_analytics = child_data["analytics"]
        
        # Используем агрегированную историю из портфеля (уже обработана рекурсивно)
        child_history_aggregated = _get_aggregated_history(portfolio_map, child["id"], child_data["history"])

        if child_history_aggregated:
            # Применяем forward fill для дочернего портфеля до максимальной даты
            child_history_filled = forward_fill_history(child_history_aggregated)
            
            # Если есть максимальная дата среди всех портфелей, заполняем до неё
            if max_child_date and child_history_filled:
                last_filled_date_str = child_history_filled[-1].get("date")
                if last_filled_date_str and last_filled_date_str < max_child_date:
                    last_filled_date = datetime.strptime(last_filled_date_str, "%Y-%m-%d").date()
                    max_date = datetime.strptime(max_child_date, "%Y-%m-%d").date()
                    last_values = child_history_filled[-1]
                    
                    # Добавляем записи до максимальной даты
                    current_date = last_filled_date + timedelta(days=1)
                    while current_date <= max_date:
                        child_history_filled.append({
                            "date": current_date.isoformat(),
                            "value": last_values["value"],
                            "invested": last_values["invested"],
                            "payouts": last_values["payouts"],
                            "pnl": last_values["pnl"]
                        })
                        current_date += timedelta(days=1)
            
            combined_history.extend(child_history_filled)

        # Активы — объединение
        # Используем portfolio_asset_id как уникальный ключ, так как один и тот же asset_id
        # может быть в разных портфелях с разными количествами
        # portfolio_asset_id уникален для каждого портфеля, поэтому активы из разных портфелей
        # должны оставаться отдельными записями
        existing_by_portfolio_asset = {a.get("portfolio_asset_id"): a for a in combined_assets if a.get("portfolio_asset_id")}
        
        for ca in child_assets:
            # Создаем копию актива, чтобы не модифицировать оригинал
            ca_copy = copy.deepcopy(ca)
            portfolio_asset_id = ca_copy.get("portfolio_asset_id")
            
            # Если есть portfolio_asset_id, проверяем, не добавлен ли уже этот актив
            if portfolio_asset_id and portfolio_asset_id in existing_by_portfolio_asset:
                # Актив с таким portfolio_asset_id уже есть - это тот же актив из того же портфеля
                # Обновляем данные, но не суммируем количество (это один и тот же актив)
                old = existing_by_portfolio_asset[portfolio_asset_id]
                # Обновляем только если данные изменились
                if ca_copy.get("last_price") and not old.get("last_price"):
                    old["last_price"] = ca_copy["last_price"]
            else:
                # Новый актив (с другим portfolio_asset_id) - добавляем как отдельную запись
                # Это позволяет иметь один и тот же asset_id в разных портфелях с разными количествами
                combined_assets.append(ca_copy)
                if portfolio_asset_id:
                    existing_by_portfolio_asset[portfolio_asset_id] = ca_copy

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
    
    # Агрегируем историю
    aggregated_history = aggregate_and_sort_history_list(combined_history)
    
    # Проверяем аномалии в последних записях (только критичные случаи)
    if len(aggregated_history) >= 4:
        prev_value = aggregated_history[-4]['value']
        last_value = aggregated_history[-1]['value']
        if prev_value > 0:
            diff_percent = ((last_value - prev_value) / prev_value) * 100
            if diff_percent < -5:  # Если разница больше 5% в меньшую сторону
                logger.error(
                    f"Портфель {portfolio_id} ({portfolio_name}): "
                    f"последняя запись на {abs(diff_percent):.1f}% меньше предыдущей "
                    f"({prev_value} -> {last_value})"
                )
    
    portfolio["history"] = aggregated_history
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

    # Возвращаем combined_history (неагрегированную) для родительского портфеля
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
    logger.debug(f'SQL RPC: {time() - time1:.2f} сек')
    time1 = time()

    # ⬇️ подмешиваем connection к каждому портфелю
    time1 = time()
    connections_by_pid = get_user_portfolio_connections(user_id)  # читает user_broker_connections
    for p in portfolios:
        p["connection"] = connections_by_pid.get(p["id"])
    logger.debug(f'Соединения: {time() - time1:.2f} сек')

    # === 1️⃣ Объединяем дочерние портфели и пересчитываем суммы ===
    portfolios = build_portfolio_hierarchy(portfolios)
    logger.debug(f'Иерархия: {time() - time1:.2f} сек')

    time1 = time()
    reference_data = get_reference_data_cached()
    logger.debug(f'Reference data: {time() - time1:.2f} сек')
    
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
    logger.debug(f'Форматирование: {time() - time1:.2f} сек')

    # Сортировка по стоимости
    portfolios = sorted(portfolios, key=lambda x: x.get('total_value', 0), reverse=True)

    return {
        "portfolios": portfolios,
        "transactions": transactions,
        "referenceData": reference_data
    }
