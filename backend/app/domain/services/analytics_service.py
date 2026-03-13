import asyncio
from collections import defaultdict
from copy import deepcopy
from app.infrastructure.database.database_service import rpc_async
from app.core.logging import get_logger
from app.infrastructure.database.repositories.portfolio_repository import PortfolioRepository
from app.domain.services.portfolio_aggregation import (
    create_empty_analytics_maps,
    merge_analytics_arrays_into_maps,
    convert_analytics_maps_to_lists,
)

logger = get_logger(__name__)

# Создаем экземпляр репозитория для использования во всех функциях
_portfolio_repository = PortfolioRepository()

async def get_user_portfolios_analytics(user_id: str):
    """
    Асинхронно вызывает RPC get_user_portfolios_analytics(p_user_id)
    и агрегирует аналитику дочерних портфелей в родительские.
    """
    logger.info(f"Получаем аналитику для пользователя {user_id}")

    try:
        # === 1️⃣ Берём аналитику по всем портфелям ===
        result = await rpc_async("get_user_portfolios_analytics", {"p_user_id": user_id})
        
        # Обрабатываем результат: может быть массивом или объектом с ключом имени функции
        if isinstance(result, dict) and "get_user_portfolios_analytics" in result:
            portfolios_analytics = result["get_user_portfolios_analytics"] or []
        elif isinstance(result, list):
            portfolios_analytics = result
        else:
            portfolios_analytics = []

        # === 2️⃣ Получаем структуру портфелей (id, parent_id, name) ===
        # Используем синхронный метод через asyncio.to_thread для совместимости
        portfolios = await asyncio.to_thread(
            _portfolio_repository.get_user_portfolios_sync, user_id
        ) or []
        
        # Фильтруем только нужные поля
        portfolios = [
            {
                "id": p.get("id"),
                "parent_portfolio_id": p.get("parent_portfolio_id"),
                "name": p.get("name")
            }
            for p in portfolios
        ]

        id_to_parent = {p["id"]: p.get("parent_portfolio_id") for p in portfolios}
        parent_to_children = defaultdict(list)
        for p in portfolios:
            if p.get("parent_portfolio_id"):
                parent_to_children[p["parent_portfolio_id"]].append(p["id"])

        # === 3️⃣ Индексируем аналитику по id портфеля ===
        analytics_map = {a["portfolio_id"]: deepcopy(a) for a in portfolios_analytics}

        # === 4️⃣ Функция рекурсивного объединения ===
        def merge_child_into_parent(parent_id):
            if parent_id not in analytics_map:
                # создаём "пустой" шаблон для родителя
                analytics_map[parent_id] = {
                    "portfolio_id": parent_id,
                    "portfolio_name": next((p["name"] for p in portfolios if p["id"] == parent_id), f"Portfolio {parent_id}"),
                    "totals": defaultdict(float),
                    "operations_breakdown": [],
                    "monthly_flow": [],
                    "monthly_payouts": [],
                    "asset_distribution": [],
                    "payouts_by_asset": [],
                    "future_payouts": [],
                    "asset_returns": [],
                }

            parent_analytics = analytics_map[parent_id]
            totals = defaultdict(float, parent_analytics.get("totals", {}))
            maps = create_empty_analytics_maps()
            merge_analytics_arrays_into_maps(maps, parent_analytics)

            for child_id in parent_to_children.get(parent_id, []):
                merge_child_into_parent(child_id)
                child = analytics_map.get(child_id)
                if not child:
                    continue

                child_totals = child.get("totals") or {}
                for k, v in child_totals.items():
                    if k == "return_percent":
                        continue
                    if k == "total_profit":
                        totals[k] = (totals.get(k, 0) or 0) + (v or 0)
                        continue
                    totals[k] += v or 0

                merge_analytics_arrays_into_maps(maps, child)

            # Пересчитываем return_percent на основе средней доходности активов
            # Доходность уже вычислена в SQL на основе средней доходности за 5 лет (акции) или ставки купона (облигации)
            # Для объединенных портфелей считаем как средневзвешенную по инвестированным суммам
            # return_percent - взвешенная по текущей стоимости
            total_weighted_return = 0.0
            total_value_for_return = 0.0
            
            # return_percent_on_invested - взвешенная по вложенному капиталу
            total_weighted_return_on_invested = 0.0
            total_invested_for_return = 0.0
            
            # Добавляем данные родителя (если есть активы в самом портфеле)
            # Учитываем портфели с 0% доходностью тоже, так как они влияют на среднюю доходность
            parent_invested = totals.get("total_invested", 0) or 0
            parent_value = totals.get("total_value", 0) or 0
            parent_return = parent_analytics.get("totals", {}).get("return_percent", 0) or 0
            parent_return_on_invested = parent_analytics.get("totals", {}).get("return_percent_on_invested", 0) or 0
            
            if parent_value > 0 or parent_invested > 0:
                # Вычитаем инвестированную сумму дочерних портфелей, чтобы получить только собственные активы
                children_invested_sum = sum(
                    analytics_map.get(child_id, {}).get("totals", {}).get("total_invested", 0) or 0
                    for child_id in parent_to_children.get(parent_id, [])
                )
                children_value_sum = sum(
                    analytics_map.get(child_id, {}).get("totals", {}).get("total_value", 0) or 0
                    for child_id in parent_to_children.get(parent_id, [])
                )
                own_invested = max(0, parent_invested - children_invested_sum)
                own_value = max(0, parent_value - children_value_sum)
                
                if own_value > 0:
                    # Учитываем даже если доходность 0%, так как это влияет на среднюю
                    total_weighted_return += parent_return * own_value
                    total_value_for_return += own_value
                
                if own_invested > 0:
                    # Учитываем даже если доходность 0%, так как это влияет на среднюю
                    total_weighted_return_on_invested += parent_return_on_invested * own_invested
                    total_invested_for_return += own_invested
            
            # Собираем данные из дочерних портфелей для расчета средневзвешенной доходности
            # Учитываем портфели с 0% доходностью тоже, так как они влияют на среднюю доходность
            for child_id in parent_to_children.get(parent_id, []):
                child = analytics_map.get(child_id)
                if not child:
                    continue
                child_totals = child.get("totals") or {}
                child_invested = child_totals.get("total_invested", 0) or 0
                child_value = child_totals.get("total_value", 0) or 0
                child_return = child_totals.get("return_percent", 0) or 0
                child_return_on_invested = child_totals.get("return_percent_on_invested", 0) or 0
                
                if child_value > 0:
                    # Учитываем даже если доходность 0%, так как это влияет на среднюю
                    total_weighted_return += child_return * child_value
                    total_value_for_return += child_value
                
                if child_invested > 0:
                    # Учитываем даже если доходность 0%, так как это влияет на среднюю
                    total_weighted_return_on_invested += child_return_on_invested * child_invested
                    total_invested_for_return += child_invested
            
            # Пересчитываем средневзвешенную доходность
            if total_value_for_return > 0:
                totals["return_percent"] = total_weighted_return / total_value_for_return
            else:
                totals["return_percent"] = 0
            
            if total_invested_for_return > 0:
                totals["return_percent_on_invested"] = total_weighted_return_on_invested / total_invested_for_return
            else:
                totals["return_percent_on_invested"] = 0

            # Пересчитываем net_cashflow
            totals["net_cashflow"] = (
                totals.get("inflow", 0) + totals.get("dividends", 0) + totals.get("coupons", 0)
                - totals.get("outflow", 0) - totals.get("commissions", 0) - totals.get("taxes", 0)
            )
            
            # total_profit уже рассчитан в SQL функции get_user_portfolios_analytics из total_pnl
            # НЕ пересчитываем его здесь, используем значение из SQL функции
            # totals["total_profit"] уже заполнен из pa.total_profit (который берется из portfolio_daily_values.total_pnl)

            analytics_lists = convert_analytics_maps_to_lists(maps)
            analytics_map[parent_id]["totals"] = dict(totals)
            analytics_map[parent_id]["operations_breakdown"] = analytics_lists["operations_breakdown"]
            analytics_map[parent_id]["monthly_flow"] = analytics_lists["monthly_flow"]
            analytics_map[parent_id]["monthly_payouts"] = analytics_lists["monthly_payouts"]
            analytics_map[parent_id]["asset_distribution"] = analytics_lists["asset_distribution"]
            analytics_map[parent_id]["payouts_by_asset"] = analytics_lists["payouts_by_asset"]
            analytics_map[parent_id]["future_payouts"] = analytics_lists["future_payouts"]
            analytics_map[parent_id]["asset_returns"] = analytics_lists["asset_returns"]

        # === 5️⃣ Собираем итог ===
        # Определяем корневые портфели (без parent_portfolio_id)
        root_portfolios = [p["id"] for p in portfolios if not p.get("parent_portfolio_id")]

        for root_id in root_portfolios:
            merge_child_into_parent(root_id)

        aggregated = [analytics_map[i] for i in analytics_map.keys()]

        logger.info(f"Аналитика собрана: {len(aggregated)} портфелей (включая агрегированные)")
        return aggregated

    except Exception as e:
        logger.error(f"Ошибка при сборке аналитики: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
