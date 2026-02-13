from collections import defaultdict
from datetime import datetime, timedelta
from time import time
import copy
from app.domain.services.reference_service import get_reference_data_cached
from app.domain.services.user_service import get_user_by_email
from app.infrastructure.database.supabase_service import rpc
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
    # Агрегация массивов аналитики будет сделана через get_user_portfolios_analytics
    # Здесь только суммируем totals для расчета total_value и total_invested
    analytics = portfolio.get("analytics") or {}
    totals = analytics.get("totals") or {}
    combined_analytics = {
        "realized_pl": float(totals.get("realized_pl", analytics.get("realized_pl", 0))),
        "unrealized_pl": float(totals.get("unrealized_pl", analytics.get("unrealized_pl", 0))),
        "dividends": float(totals.get("dividends", analytics.get("dividends", 0))),
        "coupons": float(totals.get("coupons", analytics.get("coupons", 0))),
        "commissions": float(totals.get("commissions", analytics.get("commissions", 0))),
        "taxes": float(totals.get("taxes", analytics.get("taxes", 0))),
        "inflow": float(totals.get("inflow", (analytics.get("cash_flow") or {}).get("inflow", 0))),
        "outflow": float(totals.get("outflow", (analytics.get("cash_flow") or {}).get("outflow", 0))),
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
        # child_analytics может быть dict (старый формат) или содержать totals (новый формат)
        child_totals = child_analytics.get("totals", {}) if isinstance(child_analytics, dict) else {}
        if not child_totals and isinstance(child_analytics, dict):
            # Если totals нет, используем прямые поля (старый формат)
            child_totals = child_analytics
        
        combined_analytics["realized_pl"] += float(child_totals.get("realized_pl", 0) or 0)
        combined_analytics["unrealized_pl"] += float(child_totals.get("unrealized_pl", 0) or 0)
        combined_analytics["dividends"] += float(child_totals.get("dividends", 0) or 0)
        combined_analytics["coupons"] += float(child_totals.get("coupons", 0) or 0)
        combined_analytics["commissions"] += float(child_totals.get("commissions", 0) or 0)
        combined_analytics["taxes"] += float(child_totals.get("taxes", 0) or 0)
        combined_analytics["inflow"] += float(child_totals.get("inflow", 0) or 0)
        combined_analytics["outflow"] += float(child_totals.get("outflow", 0) or 0)

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

    # 6️⃣ Пересчёт доходностей для родительских портфелей
    # Для портфелей без дочерних используем значения из аналитики напрямую
    # Для родительских портфелей доходности должны быть средневзвешенными значениями дочерних портфелей
    if len(child_data_list) == 0:
        # Портфель без дочерних - используем значения из аналитики
        return_percent = float(totals.get("return_percent", 0) or 0)
        return_percent_on_invested = float(totals.get("return_percent_on_invested", 0) or 0)
    else:
        # Портфель с дочерними - пересчитываем как средневзвешенную
        # return_percent - взвешенная по текущей стоимости
        # return_percent_on_invested - взвешенная по вложенному капиталу
        total_weighted_return = 0.0
        total_value_for_return = 0.0
        total_weighted_return_on_invested = 0.0
        total_invested_for_return = 0.0
        
        # Добавляем данные текущего портфеля (если есть активы в самом портфеле)
        current_portfolio_return = float(totals.get("return_percent", 0) or 0)
        current_portfolio_return_on_invested = float(totals.get("return_percent_on_invested", 0) or 0)
        
        # Вычитаем инвестированную сумму дочерних портфелей, чтобы получить только собственные активы
        # Используем данные из portfolio_map, которые уже обновлены рекурсивно
        children_invested_sum = 0.0
        children_value_sum = 0.0
        for child_data in child_data_list:
            child_id = child_data["child"]["id"]
            child_portfolio = portfolio_map.get(child_id)
            if child_portfolio:
                children_invested_sum += float(child_portfolio.get("total_invested", child_data["invested"]) or 0)
                children_value_sum += float(child_portfolio.get("total_value", child_data["value"]) or 0)
            else:
                children_invested_sum += float(child_data["invested"])
                children_value_sum += float(child_data["value"])
        
        own_invested = max(0, total_invested - children_invested_sum)
        own_value = max(0, total_value - children_value_sum)
        
        if own_value > 0:
            total_weighted_return += current_portfolio_return * own_value
            total_value_for_return += own_value
        
        if own_invested > 0:
            total_weighted_return_on_invested += current_portfolio_return_on_invested * own_invested
            total_invested_for_return += own_invested
        
        # Собираем данные из дочерних портфелей для расчета средневзвешенной доходности
        # Используем данные из portfolio_map, которые уже обновлены рекурсивно
        for child_data in child_data_list:
            child_id = child_data["child"]["id"]
            child_portfolio = portfolio_map.get(child_id)
            
            # Используем аналитику из portfolio_map, которая уже обновлена рекурсивно
            if child_portfolio and child_portfolio.get("analytics"):
                child_analytics = child_portfolio["analytics"]
                child_totals = child_analytics.get("totals", {}) if isinstance(child_analytics, dict) else {}
            else:
                # Fallback на данные из child_data
                child_analytics = child_data["analytics"]
                child_totals = child_analytics.get("totals", {}) if isinstance(child_analytics, dict) else {}
                if not child_totals and isinstance(child_analytics, dict):
                    child_totals = child_analytics
            
            # Используем значения из portfolio_map, которые уже обновлены
            if child_portfolio:
                child_value = float(child_portfolio.get("total_value", child_data["value"]) or 0)
                child_invested = float(child_portfolio.get("total_invested", child_data["invested"]) or 0)
            else:
                child_value = float(child_data["value"])
                child_invested = float(child_data["invested"])
            
            child_return = float(child_totals.get("return_percent", 0) or 0)
            child_return_on_invested = float(child_totals.get("return_percent_on_invested", 0) or 0)
            
            if child_value > 0:
                total_weighted_return += child_return * child_value
                total_value_for_return += child_value
            
            if child_invested > 0:
                total_weighted_return_on_invested += child_return_on_invested * child_invested
                total_invested_for_return += child_invested
        
        # Пересчитываем средневзвешенную доходность
        if total_value_for_return > 0:
            return_percent = total_weighted_return / total_value_for_return
        else:
            return_percent = 0
        
        if total_invested_for_return > 0:
            return_percent_on_invested = total_weighted_return_on_invested / total_invested_for_return
        else:
            return_percent_on_invested = 0

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

    # Сохраняем аналитику из SQL (полная структура с totals, monthly_flow, etc.)
    # Если аналитика уже есть в портфеле (из get_user_portfolios_analytics), используем её
    # Иначе создаем базовую структуру
    if portfolio.get("analytics") and isinstance(portfolio.get("analytics"), dict):
        # Обновляем totals в существующей аналитике
        if "totals" not in portfolio["analytics"]:
            portfolio["analytics"]["totals"] = {}
        portfolio["analytics"]["totals"].update({
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
            "return_percent_on_invested": return_percent_on_invested,
            "inflow": combined_analytics["inflow"],
            "outflow": combined_analytics["outflow"],
        })
        
        # Массивы аналитики будут обновлены через get_user_portfolios_analytics
    else:
        # Создаем базовую структуру, если аналитики нет
        portfolio["analytics"] = {
            "totals": {
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
                "return_percent_on_invested": return_percent_on_invested,
                "inflow": combined_analytics["inflow"],
                "outflow": combined_analytics["outflow"],
            },
            "monthly_flow": [],
            "monthly_payouts": [],
            "asset_distribution": [],
            "payouts_by_asset": [],
            "future_payouts": [],
            "asset_returns": [],
            "operations_breakdown": []
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
    """
    Вычисляет прибыль за месяц как разницу между текущей прибылью и прибылью месяц назад.
    Прибыль за месяц = текущая прибыль (pnl) - прибыль месяц назад (pnl)
    """
    if len(history) >= 2:
        try:
            # Получаем текущую прибыль (последняя запись)
            current_pnl = history[-1].get('pnl', 0) or 0
            
            # Получаем прибыль месяц назад (примерно 30 дней назад)
            # Ищем запись примерно месяц назад
            month_ago_index = max(0, len(history) - 30)
            month_ago_pnl = history[month_ago_index].get('pnl', 0) or 0
            
            # Прибыль за месяц = текущая прибыль - прибыль месяц назад
            monthly_profit = current_pnl - month_ago_pnl
            return monthly_profit
        except (KeyError, IndexError, TypeError):
            # Если нет данных о прибыли, возвращаем 0
            return 0
    elif len(history) == 1:
        # Если только одна запись, возвращаем текущую прибыль
        return history[0].get('pnl', 0) or 0
    else:
        return 0


def _normalize_analytics(analytics):
    """Нормализует аналитику: заменяет null на пустые массивы для полей-массивов."""
    if not analytics or not isinstance(analytics, dict):
        return analytics
    
    # Поля, которые должны быть массивами, а не null
    array_fields = [
        'monthly_flow', 'monthly_payouts', 'asset_distribution',
        'payouts_by_asset', 'future_payouts', 'asset_returns',
        'operations_breakdown'
    ]
    
    for field in array_fields:
        if field in analytics and analytics[field] is None:
            analytics[field] = []
    
    return analytics


async def get_dashboard_data(user_email: str):
    """
    Оптимизированная функция получения данных дашборда.
    Использует единый SQL запрос для всех данных + правильную агрегацию аналитики.
    """
    user = get_user_by_email(user_email)
    if not user:
        return None

    user_id = user['id']
    time1 = time()
    
    # Один SQL запрос получает все данные: портфели, активы, историю, аналитику, транзакции, connections
    data = rpc("get_dashboard_data_complete", {"p_user_id": user_id})
    logger.debug(f'SQL RPC (complete): {time() - time1:.2f} сек')
    
    if not data:
        return {
            "portfolios": [],
            "transactions": [],
            "referenceData": get_reference_data_cached()
        }
    
    portfolios = data.get("portfolios", []) or []
    transactions = data.get("transactions", []) or []
    
    # Нормализуем аналитику: заменяем null на пустые массивы
    for portfolio in portfolios:
        if portfolio.get("analytics"):
            portfolio["analytics"] = _normalize_analytics(portfolio["analytics"])
    
    # Объединяем дочерние портфели и пересчитываем суммы (активы, история, аналитика)
    # Аналитика уже приходит из get_dashboard_data_complete и агрегируется в build_portfolio_hierarchy
    time1 = time()
    portfolios = build_portfolio_hierarchy(portfolios)
    logger.debug(f'Иерархия: {time() - time1:.2f} сек')
    
    # Убеждаемся, что total_profit рассчитан в totals для всех портфелей
    for portfolio in portfolios:
        if portfolio.get("analytics") and portfolio["analytics"].get("totals"):
            totals = portfolio["analytics"]["totals"]
            if "total_profit" not in totals or totals.get("total_profit") is None:
                # Рассчитываем total_profit как сумму всех компонентов прибыли
                total_profit = (
                    float(totals.get("realized_pl", 0) or 0) +
                    float(totals.get("unrealized_pl", 0) or 0) +
                    float(totals.get("dividends", 0) or 0) +
                    float(totals.get("coupons", 0) or 0) +
                    float(totals.get("commissions", 0) or 0) +
                    float(totals.get("taxes", 0) or 0)
                )
                totals["total_profit"] = total_profit
    
    # Обрабатываем историю и считаем динамику
    time1 = time()
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
        "referenceData": get_reference_data_cached()  # Из кеша (загружено при старте)
    }
