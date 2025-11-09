import asyncio
from collections import defaultdict
from copy import deepcopy
from app.services.supabase_service import rpc, table_select

async def get_user_portfolios_analytics(user_id: str):
    """
    Асинхронно вызывает RPC get_user_portfolios_analytics(p_user_id)
    и агрегирует аналитику дочерних портфелей в родительские.
    """
    print(f"🚀 Получаем аналитику для пользователя {user_id}")

    try:
        # === 1️⃣ Берём аналитику по всем портфелям ===
        result = await asyncio.to_thread(rpc, "get_user_portfolios_analytics", {"p_user_id": user_id})
        portfolios_analytics = result or []

        # === 2️⃣ Получаем структуру портфелей (id, parent_id, name) ===
        portfolios = table_select(
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
                }

            parent_analytics = analytics_map[parent_id]
            totals = defaultdict(float, parent_analytics.get("totals", {}))
            op_map = defaultdict(float)
            month_map = defaultdict(lambda: {"inflow": 0.0, "outflow": 0.0})

            # учитываем текущие breakdown / monthly
            for op in parent_analytics.get("operations_breakdown") or []:
                op_map[op["type"]] += op["sum"] or 0

            for m in parent_analytics.get("monthly_flow") or []:
                month_map[m["month"]]["inflow"] += m.get("inflow", 0)
                month_map[m["month"]]["outflow"] += m.get("outflow", 0)

            # === объединяем детей ===
            for child_id in parent_to_children.get(parent_id, []):
                merge_child_into_parent(child_id)  # рекурсивно сначала посчитаем детей
                child = analytics_map.get(child_id)
                if not child:
                    continue

                child_totals = child.get("totals") or {}
                for k, v in child_totals.items():
                    totals[k] += v or 0

                for op in child.get("operations_breakdown") or []:
                    op_map[op["type"]] += op["sum"] or 0

                for m in child.get("monthly_flow") or []:
                    month_map[m["month"]]["inflow"] += m.get("inflow", 0)
                    month_map[m["month"]]["outflow"] += m.get("outflow", 0)

            # записываем объединённые данные
            analytics_map[parent_id]["totals"] = dict(totals)
            analytics_map[parent_id]["operations_breakdown"] = [
                {"type": k, "sum": v} for k, v in op_map.items()
            ]
            analytics_map[parent_id]["monthly_flow"] = [
                {"month": k, **v} for k, v in sorted(month_map.items())
            ]

        # === 5️⃣ Собираем итог ===
        # Определяем корневые портфели (без parent_portfolio_id)
        root_portfolios = [p["id"] for p in portfolios if not p.get("parent_portfolio_id")]

        for root_id in root_portfolios:
            merge_child_into_parent(root_id)

        aggregated = [analytics_map[i] for i in analytics_map.keys()]

        print(f"✅ Аналитика собрана: {len(aggregated)} портфелей (включая агрегированные)")
        return aggregated

    except Exception as e:
        print(f"⚠️ Ошибка при сборке аналитики: {e}")
        return {"success": False, "error": str(e)}
