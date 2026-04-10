"""
API endpoints для поддержки.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.constants import HTTPStatus
from app.core.dependencies import get_current_user
from app.domain.services.support_service import create_user_message, list_messages_for_user
from app.utils.response import success_response

router = APIRouter(prefix="/support", tags=["support"])


class SupportMessageRequest(BaseModel):
    """Модель запроса отправки сообщения в поддержку."""
    message: str = Field(..., min_length=1, max_length=5000, description="Текст сообщения")


@router.get("/messages")
async def get_support_thread(user: dict = Depends(get_current_user)):
    """История переписки текущего пользователя с поддержкой (хронологический порядок)."""
    messages = await list_messages_for_user(str(user["id"]))
    return success_response(data={"messages": messages}, message="OK")


@router.post("/message", status_code=HTTPStatus.CREATED)
async def send_support_message(
    data: SupportMessageRequest,
    user: dict = Depends(get_current_user),
):
    """Отправка сообщения пользователя в чат поддержки."""
    row = await create_user_message(str(user["id"]), data.message.strip())
    if not row:
        raise HTTPException(status_code=500, detail="Не удалось сохранить сообщение")
    return success_response(
        data={"chat_message": row},
        message="Сообщение отправлено",
        status_code=HTTPStatus.CREATED,
    )
