import asyncio
import logging
import os
from app.services.supabase_async import db_select, db_insert, db_update
from tqdm.asyncio import tqdm_asyncio
from app.supabase_data.moex_utils import (
    create_moex_session,
    fetch_json,
    normalize_date,
    format_date
)

# Настройка логирования
LOG_LEVEL = os.getenv("MOEX_LOG_LEVEL", "INFO").upper()
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(handler)

MOEX_BONDIZATION_URL = "https://iss.moex.com/iss/securities/{ticker}/bondization.json"
MOEX_COUPONS_URL = "https://iss.moex.com/iss/securities/{ticker}/coupons.json"

# ===================================================
# 📊 ПОЛУЧЕНИЕ ДАННЫХ С MOEX (Только облигации)
# ===================================================

async def fetch_bond_payouts_from_moex(session, ticker: str):
    logger.debug(f"Получение выплат по облигации {ticker}")
    url = MOEX_BONDIZATION_URL.format(ticker=ticker)
    data = await fetch_json(session, url)
    if not data:
        logger.warning(f"Нет данных о выплатах для {ticker}")
        return []

    results = []

    # --- Купоны ---
    if "coupons" in data and "data" in data["coupons"]:
        cols = data["coupons"]["columns"]
        coupons_data = data["coupons"]["data"]
        logger.debug(f"Найдено {len(coupons_data)} купонов для {ticker}")
        for row in coupons_data:
            rec = dict(zip(cols, row))
            results.append({
                "record_date": rec.get("recorddate"),
                "payment_date": rec.get("coupondate"),
                "value": rec.get("value"),
                "currency": rec.get("faceunit"),
                "type": "coupon"  # Тип выплаты
            })

    # --- Амортизации ---
    if "amortizations" in data and "data" in data["amortizations"]:
        cols = data["amortizations"]["columns"]
        amort_data = data["amortizations"]["data"]
        logger.debug(f"Найдено {len(amort_data)} амортизаций для {ticker}")
        for row in amort_data:
            rec = dict(zip(cols, row))
            results.append({
                "record_date": rec.get("amortdate"),
                "payment_date": rec.get("amortdate"),
                "value": rec.get("value"),
                "currency": rec.get("faceunit"),
                "type": "amortization"  # Тип выплаты
            })

    logger.debug(f"Всего выплат для {ticker}: {len(results)}")
    return results


async def fetch_bond_meta_from_coupons(session, ticker: str):
    logger.debug(f"Получение метаданных облигации {ticker}")
    url = MOEX_COUPONS_URL.format(ticker=ticker)
    data = await fetch_json(session, url)
    if not data or "description" not in data or "data" not in data["description"]:
        logger.warning(f"Нет метаданных для {ticker}")
        return {}

    desc = data["description"]["data"]
    meta = {row[0]: row[2] for row in desc if len(row) >= 3}
    logger.debug(f"Метаданные для {ticker}: {len(meta)} полей")

    result = {
        "coupon_percent": float(meta.get("COUPONPERCENT", 0)) if meta.get("COUPONPERCENT") else None,
        "coupon_value": float(meta.get("COUPONVALUE", 0)) if meta.get("COUPONVALUE") else None,
        "coupon_frequency": int(meta.get("COUPONFREQUENCY", 0)) if meta.get("COUPONFREQUENCY") else None,
        "face_value": float(meta.get("FACEVALUE", 0)) if meta.get("FACEVALUE") else None,
        "currency": meta.get("FACEUNIT", "RUB"),
        "mat_date": meta.get("MATDATE"),
    }
    logger.debug(f"Метаданные {ticker}: coupon_percent={result['coupon_percent']}, face_value={result['face_value']}")
    return result

# ===================================================
# 🧠 ОБНОВЛЕНИЕ В БД
# ===================================================

async def update_asset_payouts(session, asset):
    asset_id = asset["id"]
    ticker = asset["ticker"]
    logger.debug(f"Обновление выплат для актива {ticker} (ID: {asset_id})")

    atype = await db_select("asset_types", select="name", filters={"id": asset["asset_type_id"]})
    type_name = (atype[0]["name"].lower() if atype else "").strip()

    # --- Проверка типа актива: работаем только с облигациями ---
    if "bond" not in type_name and "облига" not in type_name:
        logger.debug(f"Пропуск {ticker}: не облигация (тип: {type_name})")
        return

    # --- Получаем выплаты и метаданные параллельно (оптимизировано) ---
    logger.debug(f"Параллельная загрузка выплат и метаданных для {ticker}")
    payouts_task = fetch_bond_payouts_from_moex(session, ticker)
    meta_task = fetch_bond_meta_from_coupons(session, ticker)
    payouts, meta = await asyncio.gather(payouts_task, meta_task)

    if not payouts:
        logger.debug(f"Нет выплат для {ticker}")
        return

    logger.debug(f"Получено {len(payouts)} выплат для {ticker}")

    # --- Получаем существующие записи ---
    logger.debug(f"Загрузка существующих выплат для {ticker} из БД")
    existing = await db_select("asset_payouts", filters={"asset_id": asset_id})
    
    # Формируем множество ключей: (Дата, Сумма, Тип)
    existing_keys = set()
    for i in existing:
        d = normalize_date(i.get("record_date"))
        val = round(float(i.get("value") or 0), 2)
        p_type = i.get("type")
        if d:
            existing_keys.add((d, val, p_type))

    # --- Фильтрация и батчевая вставка (оптимизировано) ---
    payouts_to_insert = []
    for p in payouts:
        if not p["record_date"] or not p["value"]:
            continue

        p_date = normalize_date(p["record_date"])
        if not p_date: 
            continue
            
        p_val = round(float(p["value"]), 2)
        p_type = p["type"]

        # Ключ для проверки на дубликаты
        key = (p_date, p_val, p_type)

        if key in existing_keys:
            continue

        # Нормализуем payment_date
        payment_date = normalize_date(p.get("payment_date"))
        
        payouts_to_insert.append({
            "asset_id": asset_id,
            "type": p["type"],
            "value": p["value"],
            "dividend_yield": meta.get('coupon_percent'), 
            "last_buy_date": None,
            "record_date": format_date(p_date),
            "payment_date": format_date(payment_date)
        })
    
    # Батчевая вставка (вместо по одной записи)
    if payouts_to_insert:
        logger.info(f"Вставка {len(payouts_to_insert)} выплат для {ticker} батчем")
        try:
            await db_insert("asset_payouts", payouts_to_insert)
            logger.debug(f"Успешно вставлено {len(payouts_to_insert)} выплат для {ticker}")
        except Exception as e:
            logger.warning(f"Ошибка батчевой вставки для {ticker}: {e}, пробуем по одной")
            # Если батч не прошел, пробуем по одной (fallback)
            inserted_count = 0
            for payout_data in payouts_to_insert:
                try:
                    await db_insert("asset_payouts", payout_data)
                    inserted_count += 1
                except Exception as inner_e:
                    logger.debug(f"Пропуск дубликата выплаты для {ticker}: {inner_e}")
            logger.info(f"Вставлено {inserted_count}/{len(payouts_to_insert)} выплат для {ticker} по одной")

    # --- Обновляем свойства облигации ---
    if meta:
        props = asset.get("properties") or {}
        props.update(meta)
        await db_update("assets", {"properties": props}, {"id": asset_id})


# ===================================================
# 🚀 ОБРАБОТКА ВСЕХ АКТИВОВ
# ===================================================

async def update_all_moex_assets():
    logger.info("Начало обновления выплат по облигациям MOEX")
    # Загружаем активы
    logger.debug("Загрузка активов из БД")
    assets = await db_select("assets")
    moex_assets = [
        a for a in assets
        if a.get("properties") and a["properties"].get("source") == "moex"
    ]
    logger.info(f"Найдено {len(moex_assets)} активов MOEX для обработки")

    if not moex_assets:
        logger.warning("Нет активов MOEX для обработки")
        return

    async with create_moex_session() as session:
        logger.debug(f"Запуск обработки {len(moex_assets)} активов")
        tasks = [update_asset_payouts(session, a) for a in moex_assets]
        await tqdm_asyncio.gather(*tasks, desc="MOEX обновление (облигации)", total=len(tasks))
    logger.info("Обновление выплат по облигациям завершено")


if __name__ == "__main__":
    asyncio.run(update_all_moex_assets())