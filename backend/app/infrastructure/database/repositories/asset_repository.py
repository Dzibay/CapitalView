"""
Репозиторий для работы с активами.
"""
from typing import List, Optional, Dict, Any
from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.database_service import (
    table_select,
    table_insert,
    rpc,
    rpc_async,
)


class AssetRepository(BaseRepository):
    """Репозиторий для работы с таблицей assets."""

    table_name = "assets"

    def find_by_ticker_and_user(self, ticker: str, user_id: str) -> Optional[Dict[str, Any]]:
        result = table_select(
            "assets", select="*",
            filters={"ticker": ticker, "user_id": user_id},
            limit=1,
        )
        return self._first_or_none(result)

    def get_all_assets(self) -> List[Dict[str, Any]]:
        return rpc("get_all_assets", {}) or []

    async def get_all_assets_async(self) -> List[Dict[str, Any]]:
        return await rpc_async("get_all_assets", {}) or []

    def add_price(self, asset_id: int, price: float, trade_date: str) -> Optional[Dict[str, Any]]:
        result = table_insert("asset_prices", {
            "asset_id": asset_id,
            "price": price,
            "trade_date": trade_date,
        })
        return self._first_or_none(result)

    def get_price_history(
        self,
        asset_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100000,
    ) -> List[Dict[str, Any]]:
        result = table_select(
            "asset_prices", select="*",
            filters={"asset_id": asset_id},
            order={"column": "trade_date", "desc": True},
            limit=limit,
        )
        return result or []

    def get_latest_price(self, asset_id: int) -> Optional[Dict[str, Any]]:
        result = table_select(
            "asset_latest_prices", select="*",
            filters={"asset_id": asset_id},
            limit=1,
        )
        return self._first_or_none(result)

    def update_latest_price(self, asset_id: int) -> bool:
        result = rpc("update_asset_latest_prices_batch", {"p_asset_ids": [asset_id]})
        return result is not False
