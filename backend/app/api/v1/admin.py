"""
Административное API (platform admin).

Префикс /admin — единая точка расширения: обзор, пользователи, метрики, «от имени пользователя».
"""
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_admin_user
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
from app.domain.services.admin_service import (
    admin_reply_support_message,
    get_admin_data,
    list_support_messages_for_admin,
)
from app.domain.services.dashboard_service import get_dashboard_data
from app.domain.services.user_service import get_user_by_id
from app.domain.services.portfolio_service import refresh_portfolio_assets_and_daily_values
from app.domain.services.broker_connections_service import get_user_portfolio_connections
from app.domain.services.task_service import create_import_task
from app.infrastructure.database.database_service import table_select_async, rpc_async
from app.infrastructure.cache import invalidate_cache
from app.utils.response import success_response

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminSupportReplyBody(BaseModel):
    user_id: UUID
    message: str = Field(..., min_length=1, max_length=5000)


@router.get("/data")
async def admin_data(_: dict = Depends(get_current_admin_user)):
    payload = await get_admin_data()
    return success_response(data=payload, message="OK")


@router.get("/support-messages")
async def admin_support_messages(_: dict = Depends(get_current_admin_user)):
    messages = await list_support_messages_for_admin()
    return success_response(data={"support_messages": messages}, message="OK")


@router.post("/support-messages/reply", status_code=201)
async def admin_support_reply(
    body: AdminSupportReplyBody,
    _: dict = Depends(get_current_admin_user),
):
    """Ответ администратора в чат пользователя."""
    row = await admin_reply_support_message(str(body.user_id), body.message.strip())
    return success_response(
        data={"chat_message": row},
        message="Ответ отправлен",
        status_code=201,
    )


@router.get("/users/{user_id}/dashboard")
async def admin_user_dashboard(
    user_id: UUID,
    _: dict = Depends(get_current_admin_user),
):
    """
    Данные дашборда выбранного пользователя (те же, что GET /dashboard/ для него самого).
    Только для platform admin.
    """
    uid = str(user_id)
    target = await get_user_by_id(uid)
    if not target:
        raise NotFoundError("Пользователь")

    start = time.time()
    dashboard = await get_dashboard_data(uid)
    logger.info(f"Admin dashboard view target_user={uid}: {time.time() - start:.2f}s")

    return ORJSONResponse(content=success_response(data={"dashboard": dashboard}))


async def _admin_assert_portfolio_owned_by_user(portfolio_id: int, user_id: str) -> dict:
    rows = await table_select_async(
        "portfolios",
        "id, user_id, parent_portfolio_id",
        {"id": portfolio_id},
        limit=1,
    )
    if not rows:
        raise NotFoundError("Портфель")
    row = rows[0]
    if str(row.get("user_id")) != str(user_id):
        raise NotFoundError("Портфель")
    return row


async def _admin_invalidate_user_dashboard(user_id: str) -> None:
    await invalidate_cache("dashboard:{user_id}", user_id=str(user_id))


@router.post("/users/{user_id}/portfolios/{portfolio_id}/refresh", status_code=HTTPStatus.ACCEPTED)
async def admin_user_portfolio_refresh(
    user_id: UUID,
    portfolio_id: int,
    _: dict = Depends(get_current_admin_user),
):
    """Пересчёт портфеля (как POST /portfolios/{id}/refresh) — для выбранного пользователя."""
    uid = str(user_id)
    target = await get_user_by_id(uid)
    if not target:
        raise NotFoundError("Пользователь")
    await _admin_assert_portfolio_owned_by_user(portfolio_id, uid)
    result = await refresh_portfolio_assets_and_daily_values(portfolio_id)
    await _admin_invalidate_user_dashboard(uid)
    return success_response(
        data={"result": result},
        message="Портфель успешно обновлён",
        status_code=HTTPStatus.ACCEPTED,
    )


@router.post("/users/{user_id}/portfolios/{portfolio_id}/clear")
async def admin_user_portfolio_clear(
    user_id: UUID,
    portfolio_id: int,
    _: dict = Depends(get_current_admin_user),
):
    """Очистка портфеля (как POST /portfolios/{id}/clear)."""
    uid = str(user_id)
    target = await get_user_by_id(uid)
    if not target:
        raise NotFoundError("Пользователь")
    await _admin_assert_portfolio_owned_by_user(portfolio_id, uid)
    await rpc_async("clear_portfolio_full", {"p_portfolio_id": portfolio_id})
    await _admin_invalidate_user_dashboard(uid)
    return success_response(message="Портфель успешно очищен")


@router.delete("/users/{user_id}/portfolios/{portfolio_id}")
async def admin_user_portfolio_delete(
    user_id: UUID,
    portfolio_id: int,
    _: dict = Depends(get_current_admin_user),
):
    """Удаление дочернего портфеля (как DELETE /portfolios/{id})."""
    uid = str(user_id)
    target = await get_user_by_id(uid)
    if not target:
        raise NotFoundError("Пользователь")
    row = await _admin_assert_portfolio_owned_by_user(portfolio_id, uid)
    if not row.get("parent_portfolio_id"):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=ErrorMessages.PARENT_PORTFOLIO_CANNOT_BE_DELETED,
        )
    await rpc_async(
        "clear_portfolio_full",
        {"p_portfolio_id": portfolio_id, "p_delete_self": True},
    )
    await _admin_invalidate_user_dashboard(uid)
    return success_response(message=SuccessMessages.PORTFOLIO_DELETED)


@router.post("/users/{user_id}/portfolios/broker-sync")
async def admin_user_broker_sync_portfolios(
    user_id: UUID,
    _: dict = Depends(get_current_admin_user),
):
    """
    Поставить в очередь импорт из брокера для всех портфелей пользователя
    с сохранённым API-ключом (как кнопка «Обновить портфели» в приложении).
    """
    uid = str(user_id)
    target = await get_user_by_id(uid)
    if not target:
        raise NotFoundError("Пользователь")
    conns = await get_user_portfolio_connections(uid)
    tasks = []
    for pid, cred in conns.items():
        api_key = cred.get("api_key")
        bid = cred.get("broker_id")
        if not api_key or bid is None:
            continue
        task_row = await create_import_task(
            user_id=uid,
            broker_id=int(bid),
            broker_token=api_key,
            portfolio_id=int(pid),
            portfolio_name=None,
            priority=0,
        )
        if task_row and task_row.get("id") is not None:
            tasks.append(
                {
                    "task_id": int(task_row["id"]),
                    "portfolio_id": int(pid),
                }
            )
    return success_response(
        data={"tasks": tasks, "count": len(tasks)},
        message="Задачи поставлены в очередь" if tasks else "Нет портфелей с API-ключом брокера",
    )
