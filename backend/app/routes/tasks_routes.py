"""
Роуты для работы с задачами импорта портфелей.
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from app.services.task_service import (
    create_import_task,
    get_task,
    get_user_tasks,
    cancel_task,
    update_task_status,
    TaskStatus
)
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
from app.dependencies import get_current_user
from app.utils.response_helpers import success_response
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{task_id}")
async def get_task_route(
    task_id: int,
    user: dict = Depends(get_current_user)
):
    """Получение информации о задаче."""
    task = get_task(task_id)
    
    if not task:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Задача не найдена"
        )
    
    # Проверяем права доступа (сравниваем UUID как строки)
    task_user_id = str(task["user_id"]) if task.get("user_id") else None
    user_id = str(user["id"]) if user.get("id") else None
    if task_user_id != user_id:
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
    """Получение статуса задачи (упрощенный endpoint для polling)."""
    task = get_task(task_id)
    
    if not task:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Задача не найдена"
        )
    
    # Проверяем права доступа (сравниваем UUID как строки)
    task_user_id = str(task["user_id"]) if task.get("user_id") else None
    user_id = str(user["id"]) if user.get("id") else None
    if task_user_id != user_id:
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
    tasks = get_user_tasks(user["id"], limit=limit)
    
    return success_response(data={"tasks": tasks})


@router.post("/{task_id}/cancel")
async def cancel_task_route(
    task_id: int,
    user: dict = Depends(get_current_user)
):
    """Отмена задачи."""
    success = cancel_task(task_id, user["id"])
    
    if not success:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Не удалось отменить задачу"
        )
    
    return success_response(message="Задача отменена")
