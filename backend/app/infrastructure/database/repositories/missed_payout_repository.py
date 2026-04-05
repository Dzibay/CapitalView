"""
Repository для работы с неполученными выплатами (missed_payouts).
"""
from typing import List, Dict, Any, Optional, Tuple

from app.infrastructure.database.postgres_async import rpc_async, table_delete_async, get_connection_pool


class MissedPayoutRepository:
    """Repository для работы с неполученными выплатами."""

    async def get_user_missed_payouts(
        self,
        user_id: str,
        portfolio_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        params = {
            "p_user_id": user_id,
            "p_portfolio_id": portfolio_id
        }
        params = {k: v for k, v in params.items() if v is not None}
        result = await rpc_async("get_missed_payouts", params)
        return result or []

    async def delete_missed_payout(
        self,
        portfolio_asset_id: int,
        payout_id: int
    ) -> bool:
        result = await table_delete_async(
            "missed_payouts",
            filters={
                "portfolio_asset_id": portfolio_asset_id,
                "payout_id": payout_id,
            }
        )
        return bool(result)

    async def delete_missed_payouts_batch(
        self,
        keys: List[Tuple[int, int]]
    ) -> int:
        if not keys:
            return 0

        pa_ids = [k[0] for k in keys]
        p_ids = [k[1] for k in keys]

        pool = await get_connection_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM missed_payouts mp
                USING unnest($1::bigint[], $2::bigint[]) AS x(pa_id, pid)
                WHERE mp.portfolio_asset_id = x.pa_id AND mp.payout_id = x.pid
                """,
                pa_ids,
                p_ids,
            )

        # asyncpg: 'DELETE N' prefix
        if result and str(result).upper().startswith("DELETE "):
            try:
                return int(str(result).split()[-1])
            except (ValueError, IndexError):
                return len(keys)
        return len(keys)

    async def check_missed_payouts(
        self,
        portfolio_asset_id: int
    ) -> int:
        params = {
            "p_portfolio_asset_id": portfolio_asset_id
        }
        result = await rpc_async("check_missed_payouts", params)
        return result or 0

    async def check_missed_payouts_for_portfolio(
        self,
        portfolio_id: int
    ) -> Dict[str, Any]:
        params = {
            "p_portfolio_id": portfolio_id
        }
        result = await rpc_async("check_missed_payouts_for_portfolio", params)
        return result or {}

    async def check_missed_payouts_for_user(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        params = {
            "p_user_id": user_id
        }
        result = await rpc_async("check_missed_payouts_for_user", params)
        return result or {}
