"""
Репозиторий для работы с транзакциями.
"""
from typing import List, Optional, Dict, Any
from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.database_service import (
    table_select_async,
    table_delete_async,
    rpc_async,
)


class TransactionRepository(BaseRepository):
    """Репозиторий для работы с таблицей transactions."""

    table_name = "transactions"

    # ─── RPC-методы ────────────────────────────────────────────

    async def get_transactions(
        self,
        user_id: str,
        portfolio_id: Optional[int] = None,
        asset_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        params = {"p_user_id": user_id, "p_limit": limit or 1000}
        if portfolio_id:
            params["p_portfolio_id"] = portfolio_id
        if asset_name:
            params["p_asset_name"] = asset_name
        if start_date:
            params["p_start_date"] = start_date
        if end_date:
            params["p_end_date"] = end_date
        return await rpc_async("get_transactions", params) or []

    async def get_user_transactions(self, user_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        return await self.get_transactions(user_id, limit=limit)

    async def delete_transactions_batch(self, transaction_ids: List[int]) -> Optional[Dict[str, Any]]:
        return await rpc_async("delete_transactions_batch", {"p_transaction_ids": transaction_ids})

    async def get_portfolio_transactions(self, portfolio_id: int) -> List[Dict[str, Any]]:
        return await rpc_async("get_portfolio_transactions", {
            "p_portfolio_id": portfolio_id,
        }) or []

    # ─── Query-методы ──────────────────────────────────────────

    async def get_by_portfolio_asset(self, portfolio_asset_id: int, select_fields: str = "*") -> List[Dict[str, Any]]:
        result = await table_select_async(
            "transactions", select=select_fields,
            filters={"portfolio_asset_id": portfolio_asset_id},
            order={"column": "transaction_date", "desc": True},
        )
        return result or []

    async def delete_by_portfolio_asset(self, portfolio_asset_id: int) -> bool:
        result = await table_delete_async("transactions", {"portfolio_asset_id": portfolio_asset_id})
        return bool(result)

    async def get_by_portfolio_assets(
        self, portfolio_asset_ids: List[int], select_fields: str = "*",
    ) -> List[Dict[str, Any]]:
        if not portfolio_asset_ids:
            return []
        result = await table_select_async(
            "transactions", select=select_fields,
            in_filters={"portfolio_asset_id": portfolio_asset_ids},
        )
        return result or []
