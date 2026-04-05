"""
Репозиторий для работы с портфельными активами.
"""
from typing import List, Optional, Dict, Any
from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.database_service import (
    table_select_async,
    rpc_async,
)


class PortfolioAssetRepository(BaseRepository):
    """Репозиторий для работы с таблицей portfolio_assets."""

    table_name = "portfolio_assets"

    async def get_by_portfolio_and_asset(
        self, portfolio_id: int, asset_id: int,
    ) -> Optional[Dict[str, Any]]:
        result = await table_select_async(
            "portfolio_assets", select="*",
            filters={"portfolio_id": portfolio_id, "asset_id": asset_id},
            limit=1,
        )
        return self._first_or_none(result)

    async def get_by_portfolio(self, portfolio_id: int, select_fields: str = "*") -> List[Dict[str, Any]]:
        result = await table_select_async(
            "portfolio_assets", select=select_fields,
            filters={"portfolio_id": portfolio_id},
        )
        return result or []

    async def get_by_asset(self, asset_id: int) -> List[Dict[str, Any]]:
        result = await table_select_async(
            "portfolio_assets", select="portfolio_id",
            filters={"asset_id": asset_id},
        )
        return result or []

    async def update_portfolio_asset(self, portfolio_asset_id: int) -> bool:
        result = await rpc_async("update_portfolio_asset", {"pa_id": portfolio_asset_id})
        return result is not False

    async def get_portfolio_asset_meta(self, portfolio_asset_id: int) -> Optional[Dict[str, Any]]:
        result = await rpc_async("get_portfolio_asset_meta", {
            "p_portfolio_asset_id": portfolio_asset_id,
        })
        if isinstance(result, dict):
            return result
        elif isinstance(result, list) and result:
            return result[0]
        return None
