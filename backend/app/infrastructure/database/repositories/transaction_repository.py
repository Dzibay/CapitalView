"""
Репозиторий для работы с транзакциями.
"""
from typing import List, Optional, Dict, Any
from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.database_service import (
    table_select,
    table_select_async,
    table_delete,
    rpc,
    rpc_async,
)


class TransactionRepository(BaseRepository):
    """Репозиторий для работы с таблицей transactions."""

    table_name = "transactions"

    # ─── RPC-методы ────────────────────────────────────────────

    async def get_user_transactions(self, user_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        return await rpc_async("get_user_transactions", {
            "p_user_id": user_id, "p_limit": limit,
        }) or []

    def get_user_transactions_sync(self, user_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        return rpc("get_user_transactions", {
            "p_user_id": user_id, "p_limit": limit,
        }) or []

    async def get_portfolio_transactions(self, portfolio_id: int) -> List[Dict[str, Any]]:
        return await rpc_async("get_portfolio_transactions", {
            "p_portfolio_id": portfolio_id,
        }) or []

    # ─── Query-методы ──────────────────────────────────────────

    async def get_by_portfolio_asset(self, portfolio_asset_id: int) -> List[Dict[str, Any]]:
        result = await table_select_async(
            "transactions", select="*",
            filters={"portfolio_asset_id": portfolio_asset_id},
            order={"column": "transaction_date", "desc": True},
        )
        return result or []

    def get_by_portfolio_asset_sync(self, portfolio_asset_id: int) -> List[Dict[str, Any]]:
        result = table_select(
            "transactions", select="*",
            filters={"portfolio_asset_id": portfolio_asset_id},
            order={"column": "transaction_date", "desc": True},
        )
        return result or []

    async def delete_by_portfolio_asset(self, portfolio_asset_id: int) -> bool:
        result = table_delete("transactions", {"portfolio_asset_id": portfolio_asset_id})
        return bool(result)

    async def get_by_portfolio_asset_async(
        self, portfolio_asset_id: int, select_fields: str = "*",
    ) -> List[Dict[str, Any]]:
        result = await table_select_async(
            "transactions", select=select_fields,
            filters={"portfolio_asset_id": portfolio_asset_id},
            order={"column": "transaction_date", "desc": True},
        )
        return result or []

    async def get_by_portfolio_assets_async(
        self, portfolio_asset_ids: List[int], select_fields: str = "*",
    ) -> List[Dict[str, Any]]:
        if not portfolio_asset_ids:
            return []
        result = await table_select_async(
            "transactions", select=select_fields,
            in_filters={"portfolio_asset_id": portfolio_asset_ids},
        )
        return result or []
