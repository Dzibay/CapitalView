"""
Репозиторий для работы с денежными операциями.
"""
from typing import List, Optional, Dict, Any
from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.database_service import (
    table_select_async,
    table_insert_async,
    rpc_async,
)


class OperationRepository(BaseRepository):
    """Репозиторий для работы с таблицей cash_operations."""

    table_name = "cash_operations"

    # ─── RPC-методы ────────────────────────────────────────────

    async def get_user_operations(
        self,
        user_id: str,
        portfolio_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        if limit is None:
            limit = 1000
        # rpc_async подставляет аргументы позиционно ($1..$n) в порядке ключей словаря.
        # Сигнатура get_cash_operations: user_id, portfolio_id, start_date, end_date, limit.
        # Нельзя опускать NULL из середины — иначе limit окажется на месте portfolio_id.
        params = {
            "p_user_id": user_id,
            "p_portfolio_id": portfolio_id,
            "p_start_date": start_date,
            "p_end_date": end_date,
            "p_limit": limit,
        }
        return await rpc_async("get_cash_operations", params) or []

    async def apply_operations_batch(self, p_operations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        return await rpc_async("apply_operations_batch", {"p_operations": p_operations})

    async def update_operations_batch(self, p_updates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        return await rpc_async("update_operations_batch", {"p_updates": p_updates})

    async def delete_operations_batch(self, operation_ids: List[int]) -> Optional[Dict[str, Any]]:
        return await rpc_async("delete_operations_batch", {"p_operation_ids": operation_ids})

    # ─── Bulk ──────────────────────────────────────────────────

    async def create_bulk(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not data_list:
            return []
        result = await table_insert_async("cash_operations", data_list)
        return result or []

    # ─── Query-методы ──────────────────────────────────────────

    async def get_portfolio_operations(self, portfolio_id: int) -> List[Dict[str, Any]]:
        result = await table_select_async(
            "cash_operations", select="*",
            filters={"portfolio_id": portfolio_id},
            order={"column": "date", "desc": True},
        )
        return result or []

    async def get_by_portfolio_and_asset(
        self,
        portfolio_id: int,
        asset_id: int,
        operation_types: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        filters = {"portfolio_id": portfolio_id, "asset_id": asset_id}
        in_filters = {"type": operation_types} if operation_types else None
        result = await table_select_async(
            "cash_operations", select="*",
            filters=filters, in_filters=in_filters,
            order={"column": "date", "desc": True},
        )
        return result or []

    async def get_by_transaction_id(self, transaction_id: int) -> Optional[Dict[str, Any]]:
        result = await table_select_async(
            "cash_operations",
            select="*",
            filters={"transaction_id": transaction_id},
            order={"column": "date", "desc": True},
        )
        return result[0] if result else None

    async def get_by_portfolio(
        self, portfolio_id: int, select_fields: str = "*",
    ) -> List[Dict[str, Any]]:
        result = await table_select_async(
            "cash_operations", select=select_fields,
            filters={"portfolio_id": portfolio_id},
            order={"column": "date", "desc": True},
        )
        return result or []
