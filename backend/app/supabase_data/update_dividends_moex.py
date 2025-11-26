import asyncio
import aiohttp
from app.services.supabase_service import table_select, table_insert, table_update
from datetime import datetime
from tqdm.asyncio import tqdm_asyncio
from datetime import date, datetime

MOEX_DIVIDENDS_URL = "https://iss.moex.com/iss/securities/{ticker}/dividends.json"
MOEX_BONDIZATION_URL = "https://iss.moex.com/iss/securities/{ticker}/bondization.json"
MOEX_COUPONS_URL = "https://iss.moex.com/iss/securities/{ticker}/coupons.json"


# ===================================================
# 📡 ВСПОМОГАТЕЛЬНЫЕ АСИНХРОННЫЕ ФУНКЦИИ
# ===================================================

async def fetch_json(session, url):
    """Асинхронный запрос JSON"""
    try:
        async with session.get(url, timeout=10) as resp:
            if resp.status != 200:
                print(f"⚠️ Ошибка {resp.status}: {url}")
                return None
            return await resp.json()
    except Exception as e:
        print(f"❌ Ошибка при запросе {url}: {e}")
        return None

def normalize_date(d):
    """Превращает строку или datetime в объект date для корректного сравнения"""
    if not d:
        return None
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        try:
            # Отрезаем время, если оно есть (2023-01-01T00:00:00 -> 2023-01-01)
            return datetime.fromisoformat(d.split('T')[0]).date()
        except ValueError:
            return None
    return None
# ===================================================
# 📊 ПОЛУЧЕНИЕ ДАННЫХ С MOEX
# ===================================================

async def fetch_dividends_from_moex(session, ticker: str):
    url = MOEX_DIVIDENDS_URL.format(ticker=ticker)
    data = await fetch_json(session, url)
    if not data or "dividends" not in data or "data" not in data["dividends"]:
        return []

    cols = data["dividends"]["columns"]
    payouts = []
    for row in data["dividends"]["data"]:
        d = dict(zip(cols, row))
        payouts.append({
            "record_date": d.get("registryclosedate"),
            "payment_date": None,
            "value": d.get("value"),
            "currency": d.get("currencyid"),
            "type": "dividend"
        })
    return payouts


async def fetch_bond_payouts_from_moex(session, ticker: str):
    url = MOEX_BONDIZATION_URL.format(ticker=ticker)
    data = await fetch_json(session, url)
    if not data:
        return []

    results = []

    # --- Купоны ---
    if "coupons" in data and "data" in data["coupons"]:
        cols = data["coupons"]["columns"]
        for row in data["coupons"]["data"]:
            rec = dict(zip(cols, row))
            results.append({
                "record_date": rec.get("recorddate"),
                "payment_date": rec.get("coupondate"),
                "value": rec.get("value"),
                "currency": rec.get("faceunit"),
                "type": "coupon"
            })

    # --- Амортизации ---
    if "amortizations" in data and "data" in data["amortizations"]:
        cols = data["amortizations"]["columns"]
        for row in data["amortizations"]["data"]:
            rec = dict(zip(cols, row))
            results.append({
                "record_date": rec.get("amortdate"),
                "payment_date": rec.get("amortdate"),
                "value": rec.get("value"),
                "currency": rec.get("faceunit"),
                "type": "amortization"
            })

    return results


async def fetch_bond_meta_from_coupons(session, ticker: str):
    url = MOEX_COUPONS_URL.format(ticker=ticker)
    data = await fetch_json(session, url)
    if not data or "description" not in data or "data" not in data["description"]:
        return {}

    desc = data["description"]["data"]
    meta = {row[0]: row[2] for row in desc if len(row) >= 3}

    return {
        "coupon_percent": float(meta.get("COUPONPERCENT", 0)) if meta.get("COUPONPERCENT") else None,
        "coupon_value": float(meta.get("COUPONVALUE", 0)) if meta.get("COUPONVALUE") else None,
        "coupon_frequency": int(meta.get("COUPONFREQUENCY", 0)) if meta.get("COUPONFREQUENCY") else None,
        "face_value": float(meta.get("FACEVALUE", 0)) if meta.get("FACEVALUE") else None,
        "currency": meta.get("FACEUNIT", "RUB"),
        "mat_date": meta.get("MATDATE"),
    }

# ===================================================
# 🧠 ОБНОВЛЕНИЕ В БД
# ===================================================

async def update_asset_payouts(session, asset):
    asset_id = asset["id"]
    ticker = asset["ticker"]

    atype = await asyncio.to_thread(table_select, "asset_types", select="name", filters={"id": asset["asset_type_id"]})
    type_name = (atype[0]["name"].lower() if atype else "").strip()

    # --- Получаем выплаты и метаданные ---
    if "bond" in type_name or "облига" in type_name:
        payouts = await fetch_bond_payouts_from_moex(session, ticker)
        meta = await fetch_bond_meta_from_coupons(session, ticker)
    else:
        payouts = await fetch_dividends_from_moex(session, ticker)
        meta = {}

    if not payouts:
        return

    # --- Получаем существующие записи ---
    existing = await asyncio.to_thread(table_select, "asset_payouts", filters={"asset_id": asset_id})
    
    # Формируем множество ключей: (Дата, Сумма, Тип)
    # Используем normalize_date для надежности
    existing_keys = set()
    for i in existing:
        d = normalize_date(i.get("record_date"))
        val = round(float(i.get("value") or 0), 2)
        p_type = i.get("type")
        if d:
            existing_keys.add((d, val, p_type))

    # --- Фильтрация и вставка ---
    for p in payouts:
        if not p["record_date"] or not p["value"]:
            continue

        p_date = normalize_date(p["record_date"])
        if not p_date: 
            continue
            
        p_val = round(float(p["value"]), 2)
        p_type = p["type"]

        # Ключ для проверки
        key = (p_date, p_val, p_type)

        if key in existing_keys:
            continue

        payout_data = {
            "asset_id": asset_id,
            "value": p["value"],
            "record_date": p_date.isoformat(), # Сохраняем в строгом формате YYYY-MM-DD
            "payment_date": p.get("payment_date"),
            "declared_date": None,
            "type": p_type
        }

        try:
            # Благодаря SQL constraint, даже если проверка выше пропустит дубль,
            # база данных выбросит исключение, которое мы ловим здесь.
            await asyncio.to_thread(table_insert, "asset_payouts", payout_data)
        except Exception as e:
            # print(f"Дубликат или ошибка вставки для {ticker}: {e}")
            pass

    # --- Обновляем свойства облигации ---
    if meta and ("bond" in type_name or "облига" in type_name):
        props = asset.get("properties") or {}
        props.update(meta)
        await asyncio.to_thread(table_update, "assets", {"properties": props}, {"id": asset_id})


# ===================================================
# 🚀 ОБРАБОТКА ВСЕХ АКТИВОВ
# ===================================================

async def update_all_moex_assets():
    # Загружаем активы
    assets = await asyncio.to_thread(table_select, "assets")
    moex_assets = [
        a for a in assets
        if a.get("properties") and a["properties"].get("source") == "moex"
    ]

    if not moex_assets:
        return

    # tqdm_asyncio.gather — полноценный асинхронный прогресс-бар
    async with aiohttp.ClientSession() as session:
        tasks = [update_asset_payouts(session, a) for a in moex_assets]
        await tqdm_asyncio.gather(*tasks, desc="MOEX обновление", total=len(tasks))


if __name__ == "__main__":
    asyncio.run(update_all_moex_assets())
