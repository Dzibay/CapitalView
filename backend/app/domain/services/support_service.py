"""
Сообщения поддержки: переписка пользователя с администрацией.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.infrastructure.database.database_service import table_insert_async, table_select_async


def _serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    ts = out.get("created_at")
    if isinstance(ts, datetime):
        out["created_at"] = ts.isoformat()
    out["is_from_admin"] = bool(out.get("is_from_admin"))
    return out


async def list_messages_for_user(user_id: str) -> List[Dict[str, Any]]:
    rows = await table_select_async(
        "support_messages",
        select="id, message, created_at, is_from_admin",
        filters={"user_id": user_id},
        order={"column": "created_at", "desc": False},
        limit=2000,
    )
    return [_serialize_row(r) for r in rows]


async def create_user_message(user_id: str, text: str) -> Optional[Dict[str, Any]]:
    inserted = await table_insert_async(
        "support_messages",
        {
            "user_id": user_id,
            "message": text,
            "is_from_admin": False,
        },
    )
    if not inserted:
        return None
    return _serialize_row(inserted[0])
