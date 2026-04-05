"""
Репозиторий для работы с активами.
"""
from typing import List, Optional, Dict, Any
from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.database_service import (
    table_select_async,
    table_insert_async,
    rpc_async,
)


class AssetRepository(BaseRepository):
    """Репозиторий для работы с таблицей assets."""

    table_name = "assets"

    async def find_by_ticker_and_user(self, ticker: str, user_id: str) -> Optional[Dict[str, Any]]:
        result = await table_select_async(
            "assets", select="*",
            filters={"ticker": ticker, "user_id": user_id},
            limit=1,
        )
        return self._first_or_none(result)

    async def get_all_assets(self) -> List[Dict[str, Any]]:
        return await rpc_async("get_all_assets", {}) or []

    async def add_price(self, asset_id: int, price: float, trade_date: str) -> Optional[Dict[str, Any]]:
        result = await table_insert_async("asset_prices", {
            "asset_id": asset_id,
            "price": price,
            "trade_date": trade_date,
        })
        return self._first_or_none(result)

    async def get_price_history(
        self,
        asset_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100000,
    ) -> List[Dict[str, Any]]:
        result = await table_select_async(
            "asset_prices", select="*",
            filters={"asset_id": asset_id},
            order={"column": "trade_date", "desc": True},
            limit=limit,
        )
        return result or []

    async def get_latest_price(self, asset_id: int) -> Optional[Dict[str, Any]]:
        result = await table_select_async(
            "asset_latest_prices", select="*",
            filters={"asset_id": asset_id},
            limit=1,
        )
        return self._first_or_none(result)

    async def update_latest_price(self, asset_id: int) -> bool:
        result = await rpc_async("update_asset_latest_prices_batch", {"p_asset_ids": [asset_id]})
        return result is not False
