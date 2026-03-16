"""
API endpoints для поддержки.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.infrastructure.database.postgres_service import table_insert
from app.utils.response import success_response
from app.constants import HTTPStatus
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/support", tags=["support"])


class SupportMessageRequest(BaseModel):
    """Модель запроса отправки сообщения в поддержку."""
    message: str = Field(..., min_length=1, max_length=5000, description="Текст сообщения")


@router.post("/message", status_code=HTTPStatus.CREATED)
async def send_support_message(
    data: SupportMessageRequest,
    user: dict = Depends(get_current_user)
):
    """Отправка сообщения в поддержку."""
    result = table_insert("support_messages", {
        "user_id": str(user["id"]),
        "message": data.message.strip(),
    })
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Не удалось сохранить сообщение")
    return success_response(
        message="Сообщение отправлено. Мы свяжемся с вами в ближайшее время.",
        status_code=HTTPStatus.CREATED
    )
