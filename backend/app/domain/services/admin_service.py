"""
Агрегированные данные для админки (только для platform admin).
"""
import asyncio
from typing import Any, Dict

from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.database.repositories.portfolio_repository import PortfolioRepository
from app.infrastructure.database.repositories.portfolio_asset_repository import (
    PortfolioAssetRepository,
)

_user_repository = UserRepository()
_portfolio_repository = PortfolioRepository()
_portfolio_asset_repository = PortfolioAssetRepository()


async def get_platform_stats_overview() -> Dict[str, Any]:
    """
    Сводка по платформе. Расширяйте новыми ключами по мере появления экранов админки;
    фронт и отчёты могут опираться на стабильные имена полей.
    """
    users_total, users_verified, portfolios_total, portfolio_assets_total = await asyncio.gather(
        _user_repository.count_rows(),
        _user_repository.count_rows({"email_verified": True}),
        _portfolio_repository.count_rows(),
        _portfolio_asset_repository.count_rows(),
    )
    return {
        "users_total": users_total,
        "users_verified": users_verified,
        "portfolios_total": portfolios_total,
        "portfolio_assets_total": portfolio_assets_total,
    }
