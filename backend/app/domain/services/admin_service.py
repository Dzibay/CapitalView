"""
Агрегированные данные для админки (только для platform admin).
"""
import asyncio
from typing import Any, Dict, Optional

from app.infrastructure.database.database_service import table_select_async


async def _count_rows(table: str, filters: Optional[Dict[str, Any]] = None) -> int:
    rows = await table_select_async(
        table,
        select="COUNT(*)::bigint AS cnt",
        filters=filters or {},
        limit=1,
    )
    if not rows:
        return 0
    return int(rows[0]["cnt"])


async def get_platform_stats_overview() -> Dict[str, Any]:
    """
    Сводка по платформе. Расширяйте новыми ключами по мере появления экранов админки;
    фронт и отчёты могут опираться на стабильные имена полей.
    """
    users_total, users_verified, portfolios_total, portfolio_assets_total = await asyncio.gather(
        _count_rows("users"),
        _count_rows("users", {"email_verified": True}),
        _count_rows("portfolios"),
        _count_rows("portfolio_assets"),
    )
    return {
        "users_total": users_total,
        "users_verified": users_verified,
        "portfolios_total": portfolios_total,
        "portfolio_assets_total": portfolio_assets_total,
    }
