from collections import defaultdict
from datetime import datetime
from app.services.integrations.tinkoff_import import get_tinkoff_portfolio

TOKEN = "t.b7cVknEoyjXW6FG39o4woo12yzoCAKsTwYgT0LqYFvNEH0hC5IGSMtLxVEwGfwXOv048FR5kGmxMeFpEM-GCRQ"

data = get_tinkoff_portfolio(TOKEN, days=365)

print("\n\n🔍 === ДИАГНОСТИКА ДАННЫХ ТИНЬКОФФ ===\n")

for acc, acc_data in data.items():
    print(f"📒 Аккаунт: {acc}")
    positions = {p["figi"]: p for p in acc_data["positions"]}
    transactions = acc_data["transactions"]

    # --- 1️⃣ Сводим количество по транзакциям
    calc_qty = defaultdict(float)
    for t in transactions:
        if t["type"] == "buy":
            calc_qty[t["figi"]] += t["quantity"]
        elif t["type"] == "sell":
            calc_qty[t["figi"]] -= t["quantity"]

    # --- 2️⃣ Проверяем расхождения
    print("\n⚠️ Проверяем расхождения по количеству:\n")
    for figi, pos in positions.items():
        pos_qty = pos["quantity"]
        calc = calc_qty.get(figi, 0)
        diff = calc - pos_qty
        if abs(diff) > 0.001:
            print(f"  {figi}  |  позиция={pos_qty}  транзакциями={calc}  Δ={diff:+.2f}")

    # --- 3️⃣ Ищем операции не типа buy/sell
    others = [t for t in transactions if t["type"] == "other"]
    if others:
        print("\n🟠 Найдены операции не buy/sell:")
        for o in others[:20]:  # ограничим вывод
            print(f"  {o['figi']} {o['instrument_type']} {o['date']} — type={o['type']}")

    # --- 4️⃣ Проверяем дублирующиеся сделки (одинаковый figi, дата, цена, тип)
    seen = defaultdict(list)
    for t in transactions:
        if t["price"] and t["date"]:
            key = (t["figi"], round(t["price"], 2), t["date"].date(), t["type"])
            seen[key].append(t)

    print("\n🟣 Подозрение на дублированные сделки:")
    for key, group in seen.items():
        if len(group) > 1:
            figi, price, day, ttype = key
            print(f"  {figi} ({ttype}, {day}, {price}) — {len(group)} раз")

    print("\n" + "-" * 80 + "\n")
