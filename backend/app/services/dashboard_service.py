import asyncio
from collections import defaultdict
from app.services.portfolio_service import (get_user_portfolios, get_portfolio_assets, get_portfolio_value_history)
from app.services.reference_service import (get_asset_types, get_currencies, get_system_assets)

async def get_dashboard_data(user_email: str):
    portfolios = await get_user_portfolios(user_email) or []

    if not portfolios:
        return {
            "portfolios": [],
            "assets": [],
            "histories": {},
            "combined_history": [],
            "summary": {"total_value": 0, "total_profit": 0, "profit_percent": 0},
            "asset_allocation": {"labels": [], "datasets": [{"backgroundColor": [], "data": []}]}
        }

    # Параллельная загрузка активов и историй
    portfolio_ids = [p["id"] for p in portfolios]
    assets_tasks = [asyncio.create_task(get_portfolio_assets(pid)) for pid in portfolio_ids]
    histories_tasks = [asyncio.create_task(get_portfolio_value_history(pid)) for pid in portfolio_ids]

    assets_results = await asyncio.gather(*assets_tasks, return_exceptions=True)
    histories_results = await asyncio.gather(*histories_tasks, return_exceptions=True)

    # Сбор всех активов
    assets = []
    for portfolio, result in zip(portfolios, assets_results):
        if isinstance(result, Exception):
            portfolio["assets"] = []
            continue
        if result:
            portfolio["assets"] = result
            assets.extend(result)

    # Итоговая сводка
    total_value = round(sum([p.get("total_value") or 0 for p in portfolios]), 2)
    total_profit = round(sum([p.get("total_profit") or 0 for p in portfolios]), 2)
    profit_percent = round((total_profit / total_value * 100) if total_value else 0, 2)

    summary = {
        "total_value": total_value,
        "total_profit": total_profit,
        "profit_percent": profit_percent,
        "portfolio_count": len(portfolios),
        "asset_count": len(assets)
    }

    # Распределение активов
    allocation = {}
    for asset in assets:
        atype = asset.get("type")
        if not atype:
            continue
        quantity = float(asset.get("quantity") or 0.0)
        price = float(asset.get("last_price") or 0.0)
        currency_multiplier = float(asset.get("currency_rate_to_rub") or 1.0)
        allocation[atype] = allocation.get(atype, 0) + quantity * price * currency_multiplier

    asset_allocation = {
        "labels": list(allocation.keys()),
        "datasets": [{
            "backgroundColor": ['#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#10b981', '#f472b6', '#60a5fa', '#fbbf24', '#a78bfa'],
            "data": list(allocation.values())
        }]
    }

    # Собираем истории в словарь
    histories = {
        str(pid): histories_results[i] if not isinstance(histories_results[i], Exception) else []
        for i, pid in enumerate(portfolio_ids)
    }

    # === 🔥 Объединение всех историй ===
    combined = defaultdict(float)
    for hlist in histories.values():
        for h in hlist or []:
            date = h.get("report_date")
            value = float(h.get("total_value") or 0)
            if date:
                combined[date] += value

    # Сортируем по дате
    sorted_items = sorted(combined.items())

    combined_history = {
        "labels": [d for d, v in sorted_items],
        "data": [round(v, 2) for d, v in sorted_items]
    }


    # === 🧩 Добавляем referenceData ===
    # эти функции синхронные, вызываем их параллельно через asyncio.to_thread
    asset_types, currencies, system_assets = await asyncio.gather(
        asyncio.to_thread(get_asset_types),
        asyncio.to_thread(get_currencies),
        asyncio.to_thread(get_system_assets),
    )

    reference_data = {
        "asset_types": asset_types,
        "currencies": currencies,
        "assets": system_assets
    }

    return {
        "portfolios": portfolios,
        "assets": assets,
        "histories": histories,
        "combined_history": combined_history,
        "summary": summary,
        "asset_allocation": asset_allocation,
        "referenceData": reference_data  # ✅ добавлено сюда
    }


