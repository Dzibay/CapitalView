"""
Backfill: рассчитывает accrued_coupon для всех существующих цен облигаций
на основе купонных расписаний из asset_payouts.

Запуск:
    python -m scripts.backfill_accrued_coupon
"""
import asyncio
from datetime import date, datetime
from bisect import bisect_right
from typing import Dict, List, Tuple

from app.infrastructure.database.postgres_async import (
    db_select,
    get_connection_pool,
)
from app.utils.date import parse_date as normalize_date
from app.domain.constants.payout_types import PAYOUT_TYPE_COUPON_ID


BATCH_SIZE = 2000


def calculate_accrued_coupon(
    coupon_schedule: List[Tuple[date, float]],
    trade_date: date,
) -> float:
    if not coupon_schedule or len(coupon_schedule) < 2:
        return 0.0

    dates = [c[0] for c in coupon_schedule]
    idx = bisect_right(dates, trade_date)

    if idx == 0 or idx >= len(coupon_schedule):
        return 0.0

    prev_date, _ = coupon_schedule[idx - 1]
    next_date, next_value = coupon_schedule[idx]

    period_days = (next_date - prev_date).days
    if period_days <= 0:
        return 0.0

    elapsed_days = (trade_date - prev_date).days
    return round(next_value * elapsed_days / period_days, 6)


async def load_coupon_schedules() -> Dict[int, List[Tuple[date, float]]]:
    rows = await db_select(
        "asset_payouts",
        "asset_id, payment_date, value",
        filters={"type_id": PAYOUT_TYPE_COUPON_ID},
        order="asset_id, payment_date",
        limit=None,
    )

    schedules: Dict[int, List[Tuple[date, float]]] = {}
    for r in rows:
        aid = r["asset_id"]
        pd = r.get("payment_date")
        val = r.get("value")
        if pd is None or val is None:
            continue
        if isinstance(pd, str):
            pd = normalize_date(pd)
        if isinstance(pd, datetime):
            pd = pd.date()
        if pd is None:
            continue
        schedules.setdefault(aid, []).append((pd, float(val)))

    return schedules


async def backfill():
    print("Loading bond assets...")
    bonds = await db_select(
        "assets", "id, ticker",
        filters={"asset_type_id": 2},
        limit=None,
    )
    bond_ids = [b["id"] for b in bonds]
    if not bond_ids:
        print("No bonds found.")
        return

    print(f"Found {len(bond_ids)} bonds")

    print("Loading coupon schedules...")
    schedules = await load_coupon_schedules()
    bonds_with_coupons = [bid for bid in bond_ids if bid in schedules and len(schedules[bid]) >= 2]
    print(f"Bonds with coupon schedules (>=2 coupons): {len(bonds_with_coupons)}")

    if not bonds_with_coupons:
        print("No bonds with sufficient coupon data.")
        return

    print("Loading asset_prices for bonds...")
    pool = await get_connection_pool()

    total_updated = 0

    for i in range(0, len(bonds_with_coupons), 50):
        chunk_ids = bonds_with_coupons[i:i + 50]

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT asset_id, trade_date, accrued_coupon
                FROM asset_prices
                WHERE asset_id = ANY($1)
                ORDER BY asset_id, trade_date
                """,
                chunk_ids,
            )

        updates: List[Tuple[float, int, date]] = []
        for row in rows:
            aid = row["asset_id"]
            td = row["trade_date"]
            if isinstance(td, datetime):
                td = td.date()

            coupons = schedules.get(aid, [])
            nkd = calculate_accrued_coupon(coupons, td)
            current = float(row["accrued_coupon"] or 0)

            if abs(nkd - current) > 0.001:
                updates.append((nkd, aid, td))

        if updates:
            async with pool.acquire() as conn:
                for batch_start in range(0, len(updates), BATCH_SIZE):
                    batch = updates[batch_start:batch_start + BATCH_SIZE]
                    await conn.executemany(
                        "UPDATE asset_prices SET accrued_coupon = $1 WHERE asset_id = $2 AND trade_date = $3",
                        batch,
                    )
            total_updated += len(updates)

        processed = min(i + 50, len(bonds_with_coupons))
        print(f"  Processed {processed}/{len(bonds_with_coupons)} bonds, updated {total_updated} rows so far")

    print(f"\nDone! Total rows updated: {total_updated}")

    if total_updated > 0:
        print("Updating asset_latest_prices for affected bonds...")
        from app.infrastructure.database.postgres_async import db_rpc
        for i in range(0, len(bonds_with_coupons), 500):
            batch = bonds_with_coupons[i:i + 500]
            await db_rpc("update_asset_latest_prices_batch", {"p_asset_ids": batch})
        print("asset_latest_prices updated.")


if __name__ == "__main__":
    from app.utils.async_runner import run_async
    run_async(backfill())
