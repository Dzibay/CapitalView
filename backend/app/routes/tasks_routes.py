"""
Роуты для работы с задачами импорта портфелей.
"""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.services.task_service import (
    create_import_task,
    get_task,
    get_user_tasks,
    cancel_task,
    update_task_status,
    TaskStatus
)
from app.models.task_models import CreateImportTaskRequest, TaskResponse, TaskStatusResponse
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
from app.decorators import require_user, handle_errors, validate_json_body
from app.utils.response_helpers import success_response, error_response, not_found_response, forbidden_response
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("/<int:task_id>", methods=["GET"])
@jwt_required()
@require_user
@handle_errors
def get_task_route(task_id: int, user):
    """Получение информации о задаче."""
    task = get_task(task_id)
    
    if not task:
        return not_found_response("Задача")
    
    # Проверяем права доступа (сравниваем UUID как строки)
    task_user_id = str(task["user_id"]) if task.get("user_id") else None
    user_id = str(user["id"]) if user.get("id") else None
    if task_user_id != user_id:
        return forbidden_response("Доступ запрещен")
    
    return success_response(data={"task": task})


@tasks_bp.route("/<int:task_id>/status", methods=["GET"])
@jwt_required()
@require_user
@handle_errors
def get_task_status_route(task_id: int, user):
    """Получение статуса задачи (упрощенный endpoint для polling)."""
    task = get_task(task_id)
    
    if not task:
        return not_found_response("Задача")
    
    # Проверяем права доступа (сравниваем UUID как строки)
    task_user_id = str(task["user_id"]) if task.get("user_id") else None
    user_id = str(user["id"]) if user.get("id") else None
    if task_user_id != user_id:
        return forbidden_response("Доступ запрещен")
    
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


@tasks_bp.route("/user", methods=["GET"])
@jwt_required()
@require_user
@handle_errors
def get_user_tasks_route(user):
    """Получение списка задач пользователя."""
    limit = request.args.get("limit", type=int, default=50)
    tasks = get_user_tasks(user["id"], limit=limit)
    
    return success_response(data={"tasks": tasks})


@tasks_bp.route("/<int:task_id>/cancel", methods=["POST"])
@jwt_required()
@require_user
@handle_errors
def cancel_task_route(task_id: int, user):
    """Отмена задачи."""
    success = cancel_task(task_id, user["id"])
    
    if not success:
        return error_response(
            "Не удалось отменить задачу",
            status_code=HTTPStatus.BAD_REQUEST
        )
    
    return success_response(message="Задача отменена")
