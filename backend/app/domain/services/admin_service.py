"""
Агрегированные данные для админки (только для platform admin).
"""
from typing import Any, Dict, List

from app.core.exceptions import DatabaseError, NotFoundError
from app.domain.services.support_service import _serialize_row
from app.domain.services.user_service import get_user_by_id
from app.infrastructure.database.database_service import rpc_async, table_insert_async

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


async def admin_reply_support_message(target_user_id: str, text: str) -> dict:
    """
    Ответ администратора в переписку пользователя (та же нить, что и сообщения пользователя).
    """
    target = await get_user_by_id(target_user_id)
    if not target:
        raise NotFoundError("Пользователь")

    inserted = await table_insert_async(
        "support_messages",
        {
            "user_id": target_user_id,
            "message": text,
            "is_from_admin": True,
        },
    )
    if not inserted:
        raise DatabaseError("Не удалось сохранить ответ")

    return _serialize_row(inserted[0])
