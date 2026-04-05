"""
API endpoints для работы с задачами.
Версия 1.
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from app.domain.services.task_service import (
    get_task,
    get_user_tasks,
    cancel_task,
    import_task_belongs_to_user,
)
from app.constants import HTTPStatus
from app.core.dependencies import get_current_user
from app.utils.response import success_response
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}")
async def get_task_route(
    task_id: int,
    user: dict = Depends(get_current_user)
):
    """Получение информации о задаче."""
    task = await get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Задача не найдена"
        )

    if not await import_task_belongs_to_user(task, user["id"]):
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Доступ запрещен"
        )

    return success_response(data={"task": task})


@router.get("/{task_id}/status")
async def get_task_status_route(
    task_id: int,
    user: dict = Depends(get_current_user)
):
    """Получение статуса задачи."""
    task = await get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Задача не найдена"
        )

    if not await import_task_belongs_to_user(task, user["id"]):
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Доступ запрещен"
        )

    return success_response(
        data={
            "status": task["status"],
            "progress": task.get("progress", 0),
            "progress_message": task.get("progress_message"),
            "error_message": task.get("error_message"),
            "result": task.get("result"),
            "completed_at": task.get("completed_at")
        }
    )


@router.get("/user/list")
async def get_user_tasks_route(
    user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1)
):
    """Получение списка задач пользователя."""
    tasks = await get_user_tasks(user["id"], limit=limit)

    return success_response(data={"tasks": tasks})


@router.post("/{task_id}/cancel")
async def cancel_task_route(
    task_id: int,
    user: dict = Depends(get_current_user)
):
    """Отмена задачи."""
    success = await cancel_task(task_id, user["id"])

    if not success:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Не удалось отменить задачу"
        )

    return success_response(message="Задача отменена")
