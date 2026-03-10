"""
Обновление купонов облигаций с MOEX.
Перенесено из supabase_data/update_coupons.py
"""
import asyncio
from app.infrastructure.database.postgres_async import db_select, table_insert_async
from tqdm.asyncio import tqdm_asyncio
from app.infrastructure.external.moex.client import create_moex_session, fetch_json
from app.utils.date import parse_date as normalize_date, normalize_date_to_string as format_date
from app.core.logging import get_logger

logger = get_logger(__name__)

MOEX_BONDIZATION_URL = "https://iss.moex.com/iss/securities/{ticker}/bondization.json"
BATCH_SIZE = 1000


async def fetch_bond_payouts_from_moex(session, ticker: str):
    """Получает данные о купонах облигации с MOEX."""
    url = MOEX_BONDIZATION_URL.format(ticker=ticker)
    data = await fetch_json(session, url)
    if not data:
        return []

    results = []

    if "coupons" in data and "data" in data["coupons"]:
        cols = data["coupons"]["columns"]
        for row in data["coupons"]["data"]:
            rec = dict(zip(cols, row))
            results.append({
                "record_date": rec.get("recorddate"),
                "payment_date": rec.get("coupondate"),  # coupondate - дата выплаты купона
                "value": rec.get("value"),
                "type": "coupon"
            })

    return results


async def update_all_coupons():
    """Обновляет купоны для всех облигаций с batch вставками и проверкой на дубликаты."""
    print("📥 Загрузка облигаций из БД...")
    bonds = await db_select(
        "assets",
        "id, ticker",
        filters={"asset_type_id": 2},  # Облигации
        limit=None
    )
    
    if not bonds:
        print("⚠️ Облигации не найдены")
        return
    
    print(f"✅ Найдено {len(bonds)} облигаций")
    
    # Загружаем все существующие купоны одним запросом для проверки дубликатов
    print("📥 Загрузка существующих купонов из БД...")
    existing_payouts = await db_select(
        "asset_payouts",
        "asset_id, record_date, value, type",
        filters={"type": "coupon"},
        limit=None
    )
    
    # Создаем множество ключей для быстрой проверки дубликатов
    # Ключ: (asset_id, record_date, value, type)
    existing_keys = set()
    for payout in existing_payouts:
        record_date = payout.get("record_date")
        if not record_date:
            continue
        
        # Нормализуем дату для сравнения
        if isinstance(record_date, str):
            record_date = normalize_date(record_date)
        
        if record_date:
            value = round(float(payout.get("value") or 0), 2)
            p_type = payout.get("type") or "coupon"
            key = (payout["asset_id"], record_date.isoformat() if hasattr(record_date, 'isoformat') else str(record_date), value, p_type)
            existing_keys.add(key)
    
    print(f"✅ Загружено {len(existing_keys)} существующих купонов")
    
    # Создаем словарь тикер -> asset_id
    ticker_map = {bond["ticker"].upper(): bond["id"] for bond in bonds if bond.get("ticker")}
    
    print(f"\n📥 Загрузка данных о купонах с MOEX...")
    
    # Собираем все купоны для всех облигаций
    all_new_payouts = []
    
    async with create_moex_session() as session:
        tasks = [
            fetch_bond_payouts_from_moex(session, bond["ticker"])
            for bond in bonds
            if bond.get("ticker")
        ]
        
        results = await tqdm_asyncio.gather(*tasks, desc="Загрузка купонов")
        
        # Обрабатываем результаты
        for bond, payouts in zip(bonds, results):
            if not payouts or not bond.get("ticker"):
                continue
            
            asset_id = bond["id"]
            ticker = bond["ticker"]
            
            for payout in payouts:
                record_date = normalize_date(payout.get("record_date"))
                if not record_date:
                    continue
                
                value = round(float(payout.get("value") or 0), 2)
                p_type = "coupon"
                
                # Проверяем на дубликаты
                key = (asset_id, record_date.isoformat(), value, p_type)
                if key in existing_keys:
                    continue
                
                existing_keys.add(key)  # Добавляем в множество, чтобы избежать дубликатов в рамках одного запуска
                
                payment_date = normalize_date(payout.get("payment_date"))
                
                new_payout = {
                    "asset_id": asset_id,
                    "record_date": record_date.isoformat(),
                    "payment_date": payment_date.isoformat() if payment_date else None,
                    "value": value,
                    "dividend_yield": None,  # Для купонов dividend_yield не применим
                    "type": p_type
                }
                
                all_new_payouts.append(new_payout)
    
    if not all_new_payouts:
        print("📭 Новых купонов для вставки не найдено")
        return
    
    print(f"\n📦 Найдено {len(all_new_payouts)} новых купонов для вставки")
    print(f"📦 Начинаем пакетную вставку батчами по {BATCH_SIZE}...")
    
    added_count = 0
    skipped_count = 0
    total_batches = (len(all_new_payouts) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for i in range(0, len(all_new_payouts), BATCH_SIZE):
        batch = all_new_payouts[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        
        try:
            await table_insert_async("asset_payouts", batch)
            added_count += len(batch)
            if batch_num % 10 == 0 or batch_num == total_batches:
                print(f"   ✅ Вставлен батч {batch_num}/{total_batches} ({len(batch)} записей, всего: {added_count})")
        except Exception as e:
            error_str = str(e)
            if "23505" in error_str or "duplicate" in error_str.lower() or "unique" in error_str.lower():
                # Если есть дубликаты в батче, вставляем по одной
                print(f"   ⚠️ Обнаружены дубликаты в батче {batch_num}, вставляем по одной...")
                for record in batch:
                    try:
                        await table_insert_async("asset_payouts", record)
                        added_count += 1
                    except Exception as inner_e:
                        inner_error_str = str(inner_e)
                        if "23505" not in inner_error_str and "duplicate" not in inner_error_str.lower() and "unique" not in inner_error_str.lower():
                            logger.error(f"      ⚠️ Ошибка вставки записи: {inner_e}")
                        else:
                            skipped_count += 1
            else:
                logger.error(f"   ❌ Ошибка вставки батча {batch_num}: {e}")
                skipped_count += len(batch)
    
    print(f"\n🎯 Готово!")
    print(f"   ➕ Добавлено купонов: {added_count}")
    if skipped_count > 0:
        print(f"   ⏭️ Пропущено дубликатов: {skipped_count}")


if __name__ == "__main__":
    from app.utils.async_runner import run_async
    run_async(update_all_coupons())
