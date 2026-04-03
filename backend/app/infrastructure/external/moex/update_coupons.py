"""
Обновление купонов и амортизаций облигаций с MOEX.
Перенесено из supabase_data/update_coupons.py
"""
from datetime import date, datetime

from app.infrastructure.database.postgres_async import db_select, get_connection_pool
from tqdm.asyncio import tqdm_asyncio
from app.infrastructure.external.moex.client import create_moex_session, fetch_json
from app.utils.date import parse_date as normalize_date
from app.core.logging import get_logger

logger = get_logger(__name__)

MOEX_BONDIZATION_URL = "https://iss.moex.com/iss/securities/{ticker}/bondization.json"
BATCH_SIZE = 1000

# Совпадает с idx_asset_payouts_unique_coupon: (asset_id, payment_date, type) без value
INSERT_COUPON_SQL = """
INSERT INTO asset_payouts (asset_id, value, dividend_yield, record_date, payment_date, type)
VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT (asset_id, payment_date, type) WHERE type = 'coupon' AND payment_date IS NOT NULL
DO NOTHING
"""

INSERT_AMORTIZATION_SQL = """
INSERT INTO asset_payouts (asset_id, value, dividend_yield, record_date, payment_date, type)
VALUES ($1, $2, $3, $4, $5, $6)
"""


def _payout_dedup_key(asset_id, payment_date, record_date, p_type: str):
    """Ключ дедупликации как в БД: (asset_id, дата выплаты, type), без value."""
    d = payment_date or record_date
    if not d:
        return None
    if isinstance(d, str):
        d = normalize_date(d)
    if not d:
        return None
    if isinstance(d, datetime):
        ds = d.date().isoformat()
    elif isinstance(d, date):
        ds = d.isoformat()
    else:
        ds = str(d)
    return (asset_id, ds, p_type)


def _payout_row_args(r: dict):
    return (
        r["asset_id"],
        r["value"],
        r["dividend_yield"],
        normalize_date(r["record_date"]) if r.get("record_date") else None,
        normalize_date(r["payment_date"]) if r.get("payment_date") else None,
        r["type"],
    )


async def _insert_asset_payouts_batch(rows: list) -> None:
    """Вставка батча: купоны с ON CONFLICT DO NOTHING (без ERROR в логах), амортизации — обычный INSERT."""
    if not rows:
        return
    coupons = [r for r in rows if r.get("type") == "coupon"]
    amorts = [r for r in rows if r.get("type") == "amortization"]
    pool = await get_connection_pool()
    async with pool.acquire() as conn:
        if coupons:
            await conn.executemany(INSERT_COUPON_SQL, [_payout_row_args(r) for r in coupons])
        if amorts:
            await conn.executemany(INSERT_AMORTIZATION_SQL, [_payout_row_args(r) for r in amorts])


async def fetch_bond_payouts_from_moex(session, ticker: str):
    """Получает данные о купонах и амортизациях облигации с MOEX."""
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
                "payment_date": rec.get("coupondate"),
                "value": rec.get("value"),
                "type": "coupon"
            })

    if "amortizations" in data and "data" in data["amortizations"]:
        cols = data["amortizations"]["columns"]
        for row in data["amortizations"]["data"]:
            rec = dict(zip(cols, row))
            if rec.get("data_source") == "maturity":
                continue
            results.append({
                "record_date": None,
                "payment_date": rec.get("amortdate"),
                "value": rec.get("value"),
                "type": "amortization"
            })

    return results


async def update_all_coupons():
    """Обновляет купоны и амортизации для всех облигаций с batch вставками и проверкой на дубликаты."""
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
    
    print("📥 Загрузка существующих купонов и амортизаций из БД...")
    existing_payouts = await db_select(
        "asset_payouts",
        "asset_id, record_date, payment_date, value, type",
        in_filters={"type": ["coupon", "amortization"]},
        limit=None
    )
    
    existing_keys = set()
    for payout in existing_payouts:
        p_type = payout.get("type") or "coupon"
        pd = payout.get("payment_date")
        rd = payout.get("record_date")
        if isinstance(pd, str):
            pd = normalize_date(pd)
        if isinstance(rd, str):
            rd = normalize_date(rd)
        key = _payout_dedup_key(payout["asset_id"], pd, rd, p_type)
        if key:
            existing_keys.add(key)
    
    print(f"✅ Загружено {len(existing_keys)} существующих записей (купоны + амортизации)")
    
    print(f"\n📥 Загрузка данных о купонах и амортизациях с MOEX...")
    
    all_new_payouts = []
    
    async with create_moex_session() as session:
        tasks = [
            fetch_bond_payouts_from_moex(session, bond["ticker"])
            for bond in bonds
            if bond.get("ticker")
        ]
        
        results = await tqdm_asyncio.gather(*tasks, desc="Загрузка купонов и амортизаций")
        
        for bond, payouts in zip(bonds, results):
            if not payouts or not bond.get("ticker"):
                continue
            
            asset_id = bond["id"]
            
            for payout in payouts:
                payment_date = normalize_date(payout.get("payment_date"))
                record_date = normalize_date(payout.get("record_date"))
                if not payment_date and not record_date:
                    continue
                value = round(float(payout.get("value") or 0), 2)
                p_type = payout.get("type", "coupon")
                key = _payout_dedup_key(asset_id, payment_date, record_date, p_type)
                if not key or key in existing_keys:
                    continue
                existing_keys.add(key)
                
                new_payout = {
                    "asset_id": asset_id,
                    "record_date": record_date.isoformat() if record_date else None,
                    "payment_date": payment_date.isoformat() if payment_date else None,
                    "value": value,
                    "dividend_yield": None,
                    "type": p_type
                }
                
                all_new_payouts.append(new_payout)
    
    if not all_new_payouts:
        print("📭 Новых купонов/амортизаций для вставки не найдено")
        return
    
    new_coupons = sum(1 for p in all_new_payouts if p["type"] == "coupon")
    new_amortizations = sum(1 for p in all_new_payouts if p["type"] == "amortization")
    print(f"\n📦 Найдено {len(all_new_payouts)} новых записей (купонов: {new_coupons}, амортизаций: {new_amortizations})")
    print(f"📦 Начинаем пакетную вставку батчами по {BATCH_SIZE}...")
    
    total_batches = (len(all_new_payouts) + BATCH_SIZE - 1) // BATCH_SIZE
    processed = 0
    
    for i in range(0, len(all_new_payouts), BATCH_SIZE):
        batch = all_new_payouts[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        try:
            await _insert_asset_payouts_batch(batch)
            processed += len(batch)
            if batch_num % 10 == 0 or batch_num == total_batches:
                print(f"   ✅ Батч {batch_num}/{total_batches} ({len(batch)} строк, всего отправлено: {processed})")
        except Exception as e:
            logger.error(f"   ❌ Ошибка вставки батча {batch_num}: {e}")
            raise
    
    print(f"\n🎯 Готово!")
    print(f"   ➕ Обработано строк: {processed} (дубликаты купонов по дате отброшены в БД без ошибок)")


if __name__ == "__main__":
    from app.utils.async_runner import run_async
    run_async(update_all_coupons())
