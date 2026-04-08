"""
Агрегированные данные для админки (только для platform admin).
"""
from typing import Any, Dict

from app.infrastructure.database.database_service import rpc_async


async def get_admin_data() -> Dict[str, Any]:
    """
    Один вызов RPC get_admin_data(): overview + users_registration_series.
    """
    result = await rpc_async("get_admin_data", {})
    if isinstance(result, dict):
        out = dict(result)
        if not isinstance(out.get("users"), list):
            out["users"] = []
        return out
    return {
        "overview": {
            "users_total": 0,
            "users_verified": 0,
            "portfolios_total": 0,
            "portfolio_assets_total": 0,
        },
        "users_registration_series": [],
        "users": [],
    }
