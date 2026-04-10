"""
Обновление купонов и амортизаций облигаций с MOEX.
Перенесено из supabase_data/update_coupons.py
"""
import asyncio
from datetime import date, datetime

from app.infrastructure.database.postgres_async import db_select, db_update, get_connection_pool
from tqdm.asyncio import tqdm_asyncio
from app.infrastructure.external.moex.client import create_moex_session, fetch_json
from app.utils.date import parse_date as normalize_date
from app.core.logging import get_logger
from app.domain.constants.payout_types import (
    PAYOUT_CODE_BY_ID,
    PAYOUT_TYPE_AMORTIZATION_ID,
    PAYOUT_TYPE_COUPON_ID,
)

logger = get_logger(__name__)

MOEX_BONDIZATION_URL = "https://iss.moex.com/iss/securities/{ticker}/bondization.json"
BATCH_SIZE = 1000
# Семафор смягчает волны из тысяч корутин; значения ближе к дефолтному коннектору MOEX (30 / 5).
MOEX_BONDIZATION_CONCURRENCY = 10
MOEX_BONDIZATION_REQUEST_DELAY_SEC = 0.02

# Совпадает с idx_asset_payouts_unique_coupon: (asset_id, payment_date, type_id), type_id=2 (купон)
INSERT_COUPON_SQL = """
INSERT INTO asset_payouts (asset_id, value, dividend_yield, record_date, payment_date, type_id)
VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT (asset_id, payment_date, type_id) WHERE type_id = 2 AND payment_date IS NOT NULL
DO NOTHING
"""

INSERT_AMORTIZATION_SQL = """
INSERT INTO asset_payouts (asset_id, value, dividend_yield, record_date, payment_date, type_id)
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
        r["type_id"],
    )


async def _insert_asset_payouts_batch(rows: list) -> None:
    """Вставка батча: купоны с ON CONFLICT DO NOTHING (без ERROR в логах), амортизации — обычный INSERT."""
    if not rows:
        return
    coupons = [r for r in rows if r.get("type_id") == PAYOUT_TYPE_COUPON_ID]
    amorts = [r for r in rows if r.get("type_id") == PAYOUT_TYPE_AMORTIZATION_ID]
    pool = await get_connection_pool()
    async with pool.acquire() as conn:
        if coupons:
            await conn.executemany(INSERT_COUPON_SQL, [_payout_row_args(r) for r in coupons])
        if amorts:
            await conn.executemany(INSERT_AMORTIZATION_SQL, [_payout_row_args(r) for r in amorts])


async def fetch_bond_payouts_from_moex(session, ticker: str):
    """
    Получает данные о купонах и амортизациях облигации с MOEX.

    Returns:
        (payouts: list, initial_face_value: float | None, coupon_percent: float | None).
        Если в ответе нет initialfacevalue, но есть строки купонов/амортизаций, подставляется 1000.
    """
    url = MOEX_BONDIZATION_URL.format(ticker=ticker)
    data = await fetch_json(session, url)
    if not data:
        return [], None, None

    results = []
    initial_face_value = None
    coupon_percent = None

    if "coupons" in data and "data" in data["coupons"]:
        cols = data["coupons"]["columns"]
        today_str = date.today().isoformat()
        best_coupon_rec = None  # ближайший будущий купон или последний прошедший
        for row in data["coupons"]["data"]:
            rec = dict(zip(cols, row))
            if initial_face_value is None and rec.get("initialfacevalue"):
                try:
                    initial_face_value = float(rec["initialfacevalue"])
                except (ValueError, TypeError):
                    pass
            coupon_date = rec.get("coupondate") or ""
            if best_coupon_rec is None:
                best_coupon_rec = rec
            elif coupon_date >= today_str and (best_coupon_rec.get("coupondate", "") < today_str or coupon_date < best_coupon_rec.get("coupondate", "")):
                # предпочитаем ближайший будущий
                best_coupon_rec = rec
            elif coupon_date < today_str and best_coupon_rec.get("coupondate", "") < today_str and coupon_date > best_coupon_rec.get("coupondate", ""):
                # из прошлых — самый последний
                best_coupon_rec = rec

            results.append({
                "record_date": rec.get("recorddate"),
                "payment_date": rec.get("coupondate"),
                "value": rec.get("value"),
                "type_id": PAYOUT_TYPE_COUPON_ID,
            })

        if best_coupon_rec and best_coupon_rec.get("valueprc") is not None:
            try:
                coupon_percent = float(best_coupon_rec["valueprc"])
            except (ValueError, TypeError):
                pass

    if "amortizations" in data and "data" in data["amortizations"]:
        cols = data["amortizations"]["columns"]
        for row in data["amortizations"]["data"]:
            rec = dict(zip(cols, row))
            if initial_face_value is None and rec.get("initialfacevalue"):
                try:
                    initial_face_value = float(rec["initialfacevalue"])
                except (ValueError, TypeError):
                    pass
            results.append({
                "record_date": None,
                "payment_date": rec.get("amortdate"),
                "value": rec.get("value"),
                "type_id": PAYOUT_TYPE_AMORTIZATION_ID,
            })

    if initial_face_value is None and results:
        initial_face_value = 1000.0

    return results, initial_face_value, coupon_percent


async def _fetch_bond_payouts_throttled(
    session,
    semaphore: asyncio.Semaphore,
    ticker: str,
):
    async with semaphore:
        await asyncio.sleep(MOEX_BONDIZATION_REQUEST_DELAY_SEC)
        return await fetch_bond_payouts_from_moex(session, ticker)


async def _update_bond_properties(
    bonds_with_ticker: list,
    initial_fv_map: dict,
    coupon_percent_map: dict,
):
    """
    Обновляет assets.properties для облигаций:
    - initial_face_value: для всех облигаций, у которых он ещё не задан
    - coupon_percent: только если отсутствует в текущих properties (исправляет пропущенные данные)
    """
    all_update_ids = set(initial_fv_map.keys()) | set(coupon_percent_map.keys())
    if not all_update_ids:
        return 0

    bond_ids = [b["id"] for b in bonds_with_ticker if b["id"] in all_update_ids]
    if not bond_ids:
        return 0

    assets_rows = await db_select(
        "assets", "id, properties",
        in_filters={"id": bond_ids}, limit=None,
    )

    import json as _json

    updated = 0
    for row in assets_rows:
        asset_id = row["id"]

        props = row.get("properties") or {}
        if isinstance(props, str):
            try:
                props = _json.loads(props)
            except (ValueError, TypeError):
                props = {}

        changed = False

        ifv = initial_fv_map.get(asset_id)
        if ifv and props.get("initial_face_value") != ifv:
            props["initial_face_value"] = ifv
            changed = True

        cp = coupon_percent_map.get(asset_id)
        if cp is not None and props.get("coupon_percent") is None:
            props["coupon_percent"] = cp
            changed = True

        if not changed:
            continue

        try:
            await db_update("assets", {"properties": props}, {"id": asset_id})
            updated += 1
        except Exception as e:
            logger.error(f"Ошибка обновления properties для asset_id={asset_id}: {e}")

    return updated


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
        "asset_id, record_date, payment_date, value, type_id",
        in_filters={"type_id": [PAYOUT_TYPE_COUPON_ID, PAYOUT_TYPE_AMORTIZATION_ID]},
        limit=None
    )
    
    existing_keys = set()
    for payout in existing_payouts:
        p_type = PAYOUT_CODE_BY_ID.get(payout.get("type_id"), "coupon")
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
    initial_fv_map = {}      # {asset_id: initial_face_value}
    coupon_percent_map = {}  # {asset_id: coupon_percent}
    bonds_with_ticker = [b for b in bonds if b.get("ticker")]
    
    sem = asyncio.Semaphore(MOEX_BONDIZATION_CONCURRENCY)
    async with create_moex_session() as session:
        tasks = [
            _fetch_bond_payouts_throttled(session, sem, bond["ticker"])
            for bond in bonds_with_ticker
        ]
        
        results = await tqdm_asyncio.gather(*tasks, desc="Загрузка купонов и амортизаций")
        
        for bond, (payouts, initial_fv, coupon_pct) in zip(bonds_with_ticker, results):
            asset_id = bond["id"]

            if initial_fv and initial_fv > 0:
                initial_fv_map[asset_id] = initial_fv
            if coupon_pct is not None:
                coupon_percent_map[asset_id] = coupon_pct

            if not payouts:
                continue
            
            for payout in payouts:
                payment_date = normalize_date(payout.get("payment_date"))
                record_date = normalize_date(payout.get("record_date"))
                if not payment_date and not record_date:
                    continue
                value = round(float(payout.get("value") or 0), 2)
                p_type = PAYOUT_CODE_BY_ID.get(payout.get("type_id"), "coupon")
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
                    "type_id": payout.get("type_id") or PAYOUT_TYPE_COUPON_ID,
                }
                
                all_new_payouts.append(new_payout)
    
    # Обновляем properties: initial_face_value для всех облигаций + coupon_percent для тех, у кого отсутствует
    if initial_fv_map or coupon_percent_map:
        print(f"\n📦 Обновление properties: initial_face_value ({len(initial_fv_map)} шт.), coupon_percent ({len(coupon_percent_map)} шт.)...")
        props_updated = await _update_bond_properties(bonds_with_ticker, initial_fv_map, coupon_percent_map)
        print(f"   ✅ Обновлено облигаций: {props_updated}")

    if not all_new_payouts:
        print("📭 Новых купонов/амортизаций для вставки не найдено")
        return
    
    new_coupons = sum(1 for p in all_new_payouts if p.get("type_id") == PAYOUT_TYPE_COUPON_ID)
    new_amortizations = sum(1 for p in all_new_payouts if p.get("type_id") == PAYOUT_TYPE_AMORTIZATION_ID)
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
