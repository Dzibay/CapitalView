import asyncio
from collections import defaultdict
from app.services.portfolio_service import get_portfolios_with_assets_and_history, get_user_portfolio_parent
from app.services.reference_service import get_reference_data
from app.services.transactions_service import get_transactions
from app.services.user_service import get_user_by_email
from time import time


def calculate_summary(portfolios, assets):
    """Вычисляет итоговую сводку по портфелям и активам."""
    for p in portfolios:
        if not p.get("parent_portfolio_id"):
            total_value = round(p["total_value"], 2)
            total_profit = round(p["total_profit"], 2)
            profit_percent = round((total_profit / total_value * 100) if total_value else 0, 2)

            return {
                "total_value": total_value,
                "total_profit": total_profit,
                "profit_percent": profit_percent,
                "portfolio_count": len(portfolios),
                "asset_count": len(assets)
            }
    return None


def calculate_asset_allocation(assets):
    """Вычисляет распределение активов по типам."""
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


def combine_histories(histories):
    """Объединяет истории всех портфелей в одну."""
    combined = defaultdict(float)
    for hlist in histories.values():
        for h in hlist or []:
            date = h.get("report_date")
            value = float(h.get("total_value") or 0)
            if date:
                combined[date] += value

    sorted_items = sorted(combined.items())
    return {
        "labels": [d for d, v in sorted_items],
        "data": [round(v, 2) for d, v in sorted_items]
    }


def sum_portfolio_total_value(portfolio_id: int, portfolio_map: dict):
    """
    Рекурсивно суммирует total_value и total_profit для портфеля
    с учётом всех дочерних портфелей и перезаписывает исходные поля.
    """
    portfolio = portfolio_map[portfolio_id]
    total_value = portfolio.get("total_value") or 0
    total_profit = portfolio.get("total_profit") or 0

    # находим дочерние портфели
    children = [p for p in portfolio_map.values() if p.get("parent_portfolio_id") == portfolio_id]
    for child in children:
        child_value, child_profit = sum_portfolio_total_value(child["id"], portfolio_map)
        total_value += child_value
        total_profit += child_profit

    # перезаписываем исходные поля
    portfolio["total_value"] = total_value
    portfolio["total_profit"] = total_profit

    return total_value, total_profit


async def get_dashboard_data(user_email: str):
    """Основная функция сборки данных для дашборда."""
    user_id = get_user_by_email(user_email)["id"]

    # 1️⃣ Портфели, активы и истории
    start = time()
    portfolios, assets, histories = await get_portfolios_with_assets_and_history(user_email)
    print('1. Портфели, активы и истории: ', time() - start)
    if not portfolios:
        return {
            "portfolios": [],
            "assets": [],
            "transactions": [],
            "combined_history": [],
            "summary": {"total_value": 0, "total_profit": 0, "profit_percent": 0},
            "asset_allocation": {"labels": [], "datasets": [{"backgroundColor": [], "data": []}]},
            "referenceData": {}
        }

    start = time()
    # 2️⃣ Суммируем стоимость дочерних портфелей в родительские
    portfolio_map = {p["id"]: p for p in portfolios}
    for p in portfolios:
        if not p.get("parent_portfolio_id"):  # только корневые портфели
            sum_portfolio_total_value(p["id"], portfolio_map)
    print('2. Суммируем стоимость дочерних портфелей в родительские: ', time() - start)

    start = time()
    # 4️⃣ Распределение активов
    asset_allocation = calculate_asset_allocation(assets)
    print('4. Распределение активов: ', time() - start)

    start = time()
    # 5️⃣ Объединяем истории
    combined_history = combine_histories(histories)
    print('5. Объединяем истории: ', time() - start)

    start = time()
    # 6️⃣ Справочные данные
    reference_data = get_reference_data()
    print('6. Справочные данные: ', time() - start)

    start = time()
    # 8️⃣ Получаем описание главного портфеля
    main_portfolio_description = None
    for p in portfolios:
        if not p["parent_portfolio_id"]:
            main_portfolio_description = p.get("description")
    print('8. Получаем описание главного портфеля: ', time() - start)

    start = time()
    # 7️⃣ Транзакции пользователя
    transactions = get_transactions(user_id, limit=20) or []
    print('7. Транзакции пользователя: ', time() - start)

    start = time()
    # 3️⃣ Итоговая сводка
    summary = calculate_summary(portfolios, assets)
    print('3. Итоговая сводка: ', time() - start)

    return {
        "portfolios": portfolios,
        "assets": assets,
        "transactions": transactions,
        "combined_history": combined_history,
        "summary": summary,
        "asset_allocation": asset_allocation,
        "referenceData": reference_data,
        "main_portfolio_description": main_portfolio_description
    }



