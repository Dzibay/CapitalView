"""
Репозиторий для работы с портфелями.
"""
from typing import List, Optional, Dict, Any
from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.database_service import (
    table_select_async,
    rpc_async,
)


class PortfolioRepository(BaseRepository):
    """Репозиторий для работы с таблицей portfolios."""

    table_name = "portfolios"

    # ─── RPC-методы ─────────────────────────────────────────────

    async def get_user_portfolios(self, user_id: str) -> List[Dict[str, Any]]:
        return await rpc_async("get_user_portfolios", {"u_id": user_id}) or []

    async def get_portfolio_assets(self, portfolio_id: int) -> List[Dict[str, Any]]:
        return await rpc_async("get_portfolio_assets", {"p_portfolio_id": portfolio_id}) or []

    async def get_portfolio_transactions(self, portfolio_id: int) -> List[Dict[str, Any]]:
        return await rpc_async("get_portfolio_transactions", {"p_portfolio_id": portfolio_id}) or []

    async def get_portfolio_value_history(self, portfolio_id: int) -> List[Dict[str, Any]]:
        return await rpc_async("get_portfolio_value_history", {"p_portfolio_id": portfolio_id}) or []

    # ─── Query-методы ──────────────────────────────────────────

    async def find_by_parent_and_name(
        self, parent_portfolio_id: int, name: str,
    ) -> Optional[Dict[str, Any]]:
        result = await table_select_async(
            "portfolios", select="id",
            filters={"parent_portfolio_id": parent_portfolio_id, "name": name},
            limit=1,
        )
        return self._first_or_none(result)

    async def get_by_user_id(
        self, user_id: str, select_fields: str = "*",
    ) -> List[Dict[str, Any]]:
        result = await table_select_async(
            "portfolios", select=select_fields,
            filters={"user_id": user_id},
        )
        return result or []
