"""
Агрегированные данные для админки (только для platform admin).
"""
from typing import Any, Dict, List

from app.infrastructure.database.database_service import rpc_async

_ADMIN_SUPPORT_MESSAGES_LIMIT = 100


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


async def list_support_messages_for_admin() -> List[Dict[str, Any]]:
    """
    Сообщения в поддержку с данными пользователя (email, имя), новые первыми.
    Один вызов RPC get_admin_support_messages (как get_admin_data для сводки).
    """
    result = await rpc_async(
        "get_admin_support_messages",
        {"p_limit": _ADMIN_SUPPORT_MESSAGES_LIMIT},
    )
    if isinstance(result, list):
        return result
    return []
