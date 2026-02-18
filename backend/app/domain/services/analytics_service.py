import asyncio
from collections import defaultdict
from copy import deepcopy
from app.infrastructure.database.supabase_async import rpc_async, table_select_async
from app.core.logging import get_logger

logger = get_logger(__name__)

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
        portfolios = await table_select_async(
            "portfolios",
            select="id, parent_portfolio_id, name",
            filters={"user_id": user_id}
        ) or []

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
            op_map = defaultdict(float)
            month_map = defaultdict(lambda: {"inflow": 0.0, "outflow": 0.0})
            monthly_payouts_map = defaultdict(lambda: {"dividends": 0.0, "coupons": 0.0, "amortizations": 0.0, "total_payouts": 0.0})
            asset_distribution_map = defaultdict(lambda: {
                "asset_id": None,
                "asset_name": "",
                "asset_ticker": "",
                "total_value": 0.0
            })
            payouts_by_asset_map = defaultdict(lambda: {
                "asset_id": None,
                "asset_name": "",
                "asset_ticker": "",
                "total_dividends": 0.0,
                "total_coupons": 0.0,
                "total_payouts": 0.0
            })
            future_payouts_map = defaultdict(lambda: {"dividends": 0.0, "coupons": 0.0, "amortizations": 0.0, "total_amount": 0.0, "payout_count": 0})
            asset_returns_map = defaultdict(lambda: {
                "asset_id": None,
                "asset_name": "",
                "asset_ticker": "",
                "invested_amount": 0.0,
                "current_value": 0.0,
                "price_change": 0.0,
                "realized_profit": 0.0,
                "total_payouts": 0.0,
                "total_return": 0.0,
                "return_percent": 0.0,
                # Данные за год
                "value_year_ago": 0.0,
                "price_change_year": 0.0,
                "realized_profit_year": 0.0,
                "total_payouts_year": 0.0,
                "total_return_year": 0.0,
                "return_percent_year": 0.0,
                # Данные за месяц
                "value_month_ago": 0.0,
                "price_change_month": 0.0,
                "realized_profit_month": 0.0,
                "total_payouts_month": 0.0,
                "total_return_month": 0.0,
                "return_percent_month": 0.0
            })

            # учитываем текущие данные родителя
            for op in parent_analytics.get("operations_breakdown") or []:
                op_map[op["type"]] += op["sum"] or 0

            for m in parent_analytics.get("monthly_flow") or []:
                month_map[m["month"]]["inflow"] += m.get("inflow", 0)
                month_map[m["month"]]["outflow"] += m.get("outflow", 0)

            for mp in parent_analytics.get("monthly_payouts") or []:
                month_key = mp["month"]
                monthly_payouts_map[month_key]["dividends"] += mp.get("dividends", 0) or 0
                monthly_payouts_map[month_key]["coupons"] += mp.get("coupons", 0) or 0
                monthly_payouts_map[month_key]["amortizations"] += mp.get("amortizations", 0) or 0
                monthly_payouts_map[month_key]["total_payouts"] += mp.get("total_payouts", 0) or 0

            for ad in parent_analytics.get("asset_distribution") or []:
                asset_key = ad.get("asset_id") or ad.get("asset_ticker") or ad.get("asset_name", "")
                if asset_key:
                    if asset_key not in asset_distribution_map:
                        asset_distribution_map[asset_key] = {
                            "asset_id": ad.get("asset_id"),
                            "asset_name": ad.get("asset_name", ""),
                            "asset_ticker": ad.get("asset_ticker", ""),
                            "total_value": 0.0
                        }
                    asset_distribution_map[asset_key]["total_value"] += ad.get("total_value", 0)

            # Выплаты по активам - сначала учитываем собственные выплаты родителя
            for pba in parent_analytics.get("payouts_by_asset") or []:
                asset_key = pba.get("asset_id") or pba.get("asset_ticker", "")
                if asset_key:
                    if asset_key not in payouts_by_asset_map:
                        payouts_by_asset_map[asset_key] = {
                            "asset_id": pba.get("asset_id"),
                            "asset_name": pba.get("asset_name", ""),
                            "asset_ticker": pba.get("asset_ticker", ""),
                            "total_dividends": 0.0,
                            "total_coupons": 0.0,
                            "total_payouts": 0.0
                        }
                    payouts_by_asset_map[asset_key]["total_dividends"] += pba.get("total_dividends", 0)
                    payouts_by_asset_map[asset_key]["total_coupons"] += pba.get("total_coupons", 0)
                    payouts_by_asset_map[asset_key]["total_payouts"] += pba.get("total_payouts", 0)

            for fp in parent_analytics.get("future_payouts") or []:
                month_key = fp["month"]
                future_payouts_map[month_key]["dividends"] += fp.get("dividends", 0) or 0
                future_payouts_map[month_key]["coupons"] += fp.get("coupons", 0) or 0
                future_payouts_map[month_key]["amortizations"] += fp.get("amortizations", 0) or 0
                future_payouts_map[month_key]["total_amount"] += fp.get("total_amount", 0) or 0
                future_payouts_map[month_key]["payout_count"] += fp.get("payout_count", 0) or 0

            # Доходность по активам - учитываем собственные активы родителя
            for ar in parent_analytics.get("asset_returns") or []:
                asset_key = ar.get("asset_id") or ar.get("asset_ticker") or ar.get("asset_name", "")
                if asset_key:
                    if asset_key not in asset_returns_map:
                        asset_returns_map[asset_key] = {
                            "asset_id": ar.get("asset_id"),
                            "asset_name": ar.get("asset_name", ""),
                            "asset_ticker": ar.get("asset_ticker", ""),
                            "invested_amount": 0.0,
                            "current_value": 0.0,
                            "price_change": 0.0,
                            "realized_profit": 0.0,
                            "total_payouts": 0.0,
                            "total_return": 0.0,
                            "return_percent": 0.0,
                            # Данные за год
                            "value_year_ago": 0.0,
                            "price_change_year": 0.0,
                            "realized_profit_year": 0.0,
                            "total_payouts_year": 0.0,
                            "total_return_year": 0.0,
                            "return_percent_year": 0.0,
                            # Данные за месяц
                            "value_month_ago": 0.0,
                            "price_change_month": 0.0,
                            "realized_profit_month": 0.0,
                            "total_payouts_month": 0.0,
                            "total_return_month": 0.0,
                            "return_percent_month": 0.0
                        }
                    asset_returns_map[asset_key]["invested_amount"] += ar.get("invested_amount", 0) or 0
                    asset_returns_map[asset_key]["current_value"] += ar.get("current_value", 0) or 0
                    asset_returns_map[asset_key]["price_change"] += ar.get("price_change", 0) or 0
                    asset_returns_map[asset_key]["realized_profit"] += ar.get("realized_profit", 0) or 0
                    asset_returns_map[asset_key]["total_payouts"] += ar.get("total_payouts", 0) or 0
                    asset_returns_map[asset_key]["total_return"] += ar.get("total_return", 0) or 0
                    # Данные за год
                    asset_returns_map[asset_key]["value_year_ago"] += ar.get("value_year_ago", 0) or 0
                    asset_returns_map[asset_key]["price_change_year"] += ar.get("price_change_year", 0) or 0
                    asset_returns_map[asset_key]["realized_profit_year"] += ar.get("realized_profit_year", 0) or 0
                    asset_returns_map[asset_key]["total_payouts_year"] += ar.get("total_payouts_year", 0) or 0
                    asset_returns_map[asset_key]["total_return_year"] += ar.get("total_return_year", 0) or 0
                    # Данные за месяц
                    asset_returns_map[asset_key]["value_month_ago"] += ar.get("value_month_ago", 0) or 0
                    asset_returns_map[asset_key]["price_change_month"] += ar.get("price_change_month", 0) or 0
                    asset_returns_map[asset_key]["realized_profit_month"] += ar.get("realized_profit_month", 0) or 0
                    asset_returns_map[asset_key]["total_payouts_month"] += ar.get("total_payouts_month", 0) or 0
                    asset_returns_map[asset_key]["total_return_month"] += ar.get("total_return_month", 0) or 0
                    # Пересчитываем процент доходности на основе объединенных данных
                    if asset_returns_map[asset_key]["invested_amount"] > 0:
                        asset_returns_map[asset_key]["return_percent"] = (
                            asset_returns_map[asset_key]["total_return"] / 
                            asset_returns_map[asset_key]["invested_amount"]
                        ) * 100
                    if asset_returns_map[asset_key]["value_year_ago"] > 0:
                        asset_returns_map[asset_key]["return_percent_year"] = (
                            asset_returns_map[asset_key]["total_return_year"] / 
                            asset_returns_map[asset_key]["value_year_ago"]
                        ) * 100
                    if asset_returns_map[asset_key]["value_month_ago"] > 0:
                        asset_returns_map[asset_key]["return_percent_month"] = (
                            asset_returns_map[asset_key]["total_return_month"] / 
                            asset_returns_map[asset_key]["value_month_ago"]
                        ) * 100

            # === объединяем детей ===
            for child_id in parent_to_children.get(parent_id, []):
                merge_child_into_parent(child_id)  # рекурсивно сначала посчитаем детей
                child = analytics_map.get(child_id)
                if not child:
                    continue

                child_totals = child.get("totals") or {}
                for k, v in child_totals.items():
                    # Для return_percent нужно пересчитать на основе объединенных данных
                    if k == "return_percent":
                        continue  # Пропускаем, пересчитаем позже
                    # Для total_profit тоже нужно пересчитать (суммируем из дочерних портфелей)
                    if k == "total_profit":
                        totals[k] = (totals.get(k, 0) or 0) + (v or 0)
                        continue
                    totals[k] += v or 0

                for op in child.get("operations_breakdown") or []:
                    op_map[op["type"]] += op["sum"] or 0

                for m in child.get("monthly_flow") or []:
                    month_map[m["month"]]["inflow"] += m.get("inflow", 0)
                    month_map[m["month"]]["outflow"] += m.get("outflow", 0)

                for mp in child.get("monthly_payouts") or []:
                    month_key = mp["month"]
                    monthly_payouts_map[month_key]["dividends"] += mp.get("dividends", 0) or 0
                    monthly_payouts_map[month_key]["coupons"] += mp.get("coupons", 0) or 0
                    monthly_payouts_map[month_key]["amortizations"] += mp.get("amortizations", 0) or 0
                    monthly_payouts_map[month_key]["total_payouts"] += mp.get("total_payouts", 0) or 0

                for ad in child.get("asset_distribution") or []:
                    asset_key = ad.get("asset_id") or ad.get("asset_ticker") or ad.get("asset_name", "")
                    if asset_key:
                        if asset_key not in asset_distribution_map:
                            asset_distribution_map[asset_key] = {
                                "asset_id": ad.get("asset_id"),
                                "asset_name": ad.get("asset_name", ""),
                                "asset_ticker": ad.get("asset_ticker", ""),
                                "total_value": 0.0
                            }
                        asset_distribution_map[asset_key]["total_value"] += ad.get("total_value", 0)

                # Выплаты по активам - объединяем из дочерних портфелей
                for pba in child.get("payouts_by_asset") or []:
                    asset_key = pba.get("asset_id") or pba.get("asset_ticker", "")
                    if asset_key:
                        if asset_key not in payouts_by_asset_map:
                            payouts_by_asset_map[asset_key] = {
                                "asset_id": pba.get("asset_id"),
                                "asset_name": pba.get("asset_name", ""),
                                "asset_ticker": pba.get("asset_ticker", ""),
                                "total_dividends": 0.0,
                                "total_coupons": 0.0,
                                "total_payouts": 0.0
                            }
                        payouts_by_asset_map[asset_key]["total_dividends"] += pba.get("total_dividends", 0)
                        payouts_by_asset_map[asset_key]["total_coupons"] += pba.get("total_coupons", 0)
                        payouts_by_asset_map[asset_key]["total_payouts"] += pba.get("total_payouts", 0)

                for fp in child.get("future_payouts") or []:
                    month_key = fp["month"]
                    future_payouts_map[month_key]["dividends"] += fp.get("dividends", 0) or 0
                    future_payouts_map[month_key]["coupons"] += fp.get("coupons", 0) or 0
                    future_payouts_map[month_key]["amortizations"] += fp.get("amortizations", 0) or 0
                    future_payouts_map[month_key]["total_amount"] += fp.get("total_amount", 0) or 0
                    future_payouts_map[month_key]["payout_count"] += fp.get("payout_count", 0) or 0

                # Доходность по активам - объединяем из дочерних портфелей
                for ar in child.get("asset_returns") or []:
                    asset_key = ar.get("asset_id") or ar.get("asset_ticker") or ar.get("asset_name", "")
                    if asset_key:
                        if asset_key not in asset_returns_map:
                            asset_returns_map[asset_key] = {
                                "asset_id": ar.get("asset_id"),
                                "asset_name": ar.get("asset_name", ""),
                                "asset_ticker": ar.get("asset_ticker", ""),
                                "invested_amount": 0.0,
                                "current_value": 0.0,
                                "price_change": 0.0,
                                "realized_profit": 0.0,
                                "total_payouts": 0.0,
                                "total_return": 0.0,
                                "return_percent": 0.0,
                                # Данные за год
                                "value_year_ago": 0.0,
                                "price_change_year": 0.0,
                                "realized_profit_year": 0.0,
                                "total_payouts_year": 0.0,
                                "total_return_year": 0.0,
                                "return_percent_year": 0.0,
                                # Данные за месяц
                                "value_month_ago": 0.0,
                                "price_change_month": 0.0,
                                "realized_profit_month": 0.0,
                                "total_payouts_month": 0.0,
                                "total_return_month": 0.0,
                                "return_percent_month": 0.0
                            }
                        asset_returns_map[asset_key]["invested_amount"] += ar.get("invested_amount", 0) or 0
                        asset_returns_map[asset_key]["current_value"] += ar.get("current_value", 0) or 0
                        asset_returns_map[asset_key]["price_change"] += ar.get("price_change", 0) or 0
                        asset_returns_map[asset_key]["realized_profit"] += ar.get("realized_profit", 0) or 0
                        asset_returns_map[asset_key]["total_payouts"] += ar.get("total_payouts", 0) or 0
                        asset_returns_map[asset_key]["total_return"] += ar.get("total_return", 0) or 0
                        # Данные за год
                        asset_returns_map[asset_key]["value_year_ago"] += ar.get("value_year_ago", 0) or 0
                        asset_returns_map[asset_key]["price_change_year"] += ar.get("price_change_year", 0) or 0
                        asset_returns_map[asset_key]["realized_profit_year"] += ar.get("realized_profit_year", 0) or 0
                        asset_returns_map[asset_key]["total_payouts_year"] += ar.get("total_payouts_year", 0) or 0
                        asset_returns_map[asset_key]["total_return_year"] += ar.get("total_return_year", 0) or 0
                        # Данные за месяц
                        asset_returns_map[asset_key]["value_month_ago"] += ar.get("value_month_ago", 0) or 0
                        asset_returns_map[asset_key]["price_change_month"] += ar.get("price_change_month", 0) or 0
                        asset_returns_map[asset_key]["realized_profit_month"] += ar.get("realized_profit_month", 0) or 0
                        asset_returns_map[asset_key]["total_payouts_month"] += ar.get("total_payouts_month", 0) or 0
                        asset_returns_map[asset_key]["total_return_month"] += ar.get("total_return_month", 0) or 0
                        # Пересчитываем процент доходности на основе объединенных данных
                        if asset_returns_map[asset_key]["invested_amount"] > 0:
                            asset_returns_map[asset_key]["return_percent"] = (
                                asset_returns_map[asset_key]["total_return"] / 
                                asset_returns_map[asset_key]["invested_amount"]
                            ) * 100
                        if asset_returns_map[asset_key]["value_year_ago"] > 0:
                            asset_returns_map[asset_key]["return_percent_year"] = (
                                asset_returns_map[asset_key]["total_return_year"] / 
                                asset_returns_map[asset_key]["value_year_ago"]
                            ) * 100
                        if asset_returns_map[asset_key]["value_month_ago"] > 0:
                            asset_returns_map[asset_key]["return_percent_month"] = (
                                asset_returns_map[asset_key]["total_return_month"] / 
                                asset_returns_map[asset_key]["value_month_ago"]
                            ) * 100

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

            # записываем объединённые данные
            analytics_map[parent_id]["totals"] = dict(totals)
            analytics_map[parent_id]["operations_breakdown"] = [
                {"type": k, "sum": v} for k, v in op_map.items()
            ]
            analytics_map[parent_id]["monthly_flow"] = [
                {"month": k, **v} for k, v in sorted(month_map.items())
            ]
            analytics_map[parent_id]["monthly_payouts"] = [
                {
                    "month": k,
                    "dividends": v["dividends"],
                    "coupons": v["coupons"],
                    "amortizations": v["amortizations"],
                    "total_payouts": v["total_payouts"]
                }
                for k, v in sorted(monthly_payouts_map.items())
            ]
            analytics_map[parent_id]["asset_distribution"] = sorted(
                list(asset_distribution_map.values()),
                key=lambda x: x["total_value"],
                reverse=True
            )
            analytics_map[parent_id]["payouts_by_asset"] = sorted(
                list(payouts_by_asset_map.values()),
                key=lambda x: x["total_payouts"],
                reverse=True
            )
            analytics_map[parent_id]["future_payouts"] = [
                {
                    "month": k,
                    "dividends": v["dividends"],
                    "coupons": v["coupons"],
                    "amortizations": v["amortizations"],
                    "total_amount": v["total_amount"],
                    "payout_count": v["payout_count"]
                }
                for k, v in sorted(future_payouts_map.items())
            ]
            analytics_map[parent_id]["asset_returns"] = sorted(
                list(asset_returns_map.values()),
                key=lambda x: x.get("return_percent", 0),
                reverse=True
            )

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
