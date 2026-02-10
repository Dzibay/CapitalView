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
        portfolios_analytics = result or []

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

            # Пересчитываем return_percent на основе средней доходности активов
            # Доходность уже вычислена в SQL на основе средней доходности за 5 лет (акции) или ставки купона (облигации)
            # Для объединенных портфелей считаем как средневзвешенную по инвестированным суммам
            total_weighted_return = 0.0
            total_invested_for_return = 0.0
            
            # Добавляем данные родителя (если есть активы в самом портфеле)
            parent_invested = totals.get("total_invested", 0) or 0
            parent_return = parent_analytics.get("totals", {}).get("return_percent", 0) or 0
            if parent_invested > 0 and parent_return > 0:
                # Вычитаем инвестированную сумму дочерних портфелей, чтобы получить только собственные активы
                children_invested_sum = sum(
                    analytics_map.get(child_id, {}).get("totals", {}).get("total_invested", 0) or 0
                    for child_id in parent_to_children.get(parent_id, [])
                )
                own_invested = max(0, parent_invested - children_invested_sum)
                if own_invested > 0:
                    total_weighted_return += parent_return * own_invested
                    total_invested_for_return += own_invested
            
            # Собираем данные из дочерних портфелей для расчета средневзвешенной доходности
            for child_id in parent_to_children.get(parent_id, []):
                child = analytics_map.get(child_id)
                if not child:
                    continue
                child_totals = child.get("totals") or {}
                child_invested = child_totals.get("total_invested", 0) or 0
                child_return = child_totals.get("return_percent", 0) or 0
                if child_invested > 0 and child_return > 0:
                    total_weighted_return += child_return * child_invested
                    total_invested_for_return += child_invested
            
            # Пересчитываем средневзвешенную доходность
            if total_invested_for_return > 0:
                totals["return_percent"] = total_weighted_return / total_invested_for_return
            else:
                totals["return_percent"] = 0

            # Пересчитываем net_cashflow
            totals["net_cashflow"] = (
                totals.get("inflow", 0) + totals.get("dividends", 0) + totals.get("coupons", 0)
                - totals.get("outflow", 0) - totals.get("commissions", 0) - totals.get("taxes", 0)
            )

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
