"""
Роуты для работы с задачами импорта портфелей.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.task_service import (
    create_import_task,
    get_task,
    get_user_tasks,
    cancel_task,
    update_task_status,
    TaskStatus
)
from app.services.user_service import get_user_by_email
from app.models.task_models import CreateImportTaskRequest, TaskResponse, TaskStatusResponse
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("/<int:task_id>", methods=["GET"])
@jwt_required()
def get_task_route(task_id: int):
    """Получение информации о задаче."""
    try:
        user_email = get_jwt_identity()
        user = get_user_by_email(user_email)
        
        if not user:
            return jsonify({
                "success": False,
                "error": ErrorMessages.USER_NOT_FOUND
            }), HTTPStatus.NOT_FOUND
        
        task = get_task(task_id)
        
        if not task:
            return jsonify({
                "success": False,
                "error": "Задача не найдена"
            }), HTTPStatus.NOT_FOUND
        
        # Проверяем права доступа (сравниваем UUID как строки)
        task_user_id = str(task["user_id"]) if task.get("user_id") else None
        user_id = str(user["id"]) if user.get("id") else None
        if task_user_id != user_id:
            return jsonify({
                "success": False,
                "error": "Доступ запрещен"
            }), HTTPStatus.FORBIDDEN
        
        return jsonify({
            "success": True,
            "task": task
        }), HTTPStatus.OK
        
    except Exception as e:
        logger.error(f"Ошибка при получении задачи {task_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@tasks_bp.route("/<int:task_id>/status", methods=["GET"])
@jwt_required()
def get_task_status_route(task_id: int):
    """Получение статуса задачи (упрощенный endpoint для polling)."""
    try:
        user_email = get_jwt_identity()
        user = get_user_by_email(user_email)
        
        if not user:
            return jsonify({
                "success": False,
                "error": ErrorMessages.USER_NOT_FOUND
            }), HTTPStatus.NOT_FOUND
        
        task = get_task(task_id)
        
        if not task:
            return jsonify({
                "success": False,
                "error": "Задача не найдена"
            }), HTTPStatus.NOT_FOUND
        
        # Проверяем права доступа (сравниваем UUID как строки)
        task_user_id = str(task["user_id"]) if task.get("user_id") else None
        user_id = str(user["id"]) if user.get("id") else None
        if task_user_id != user_id:
            return jsonify({
                "success": False,
                "error": "Доступ запрещен"
            }), HTTPStatus.FORBIDDEN
        
        return jsonify({
            "success": True,
            "status": task["status"],
            "progress": task.get("progress", 0),
            "progress_message": task.get("progress_message"),
            "error_message": task.get("error_message"),
            "result": task.get("result"),
            "completed_at": task.get("completed_at")
        }), HTTPStatus.OK
        
    except Exception as e:
        logger.error(f"Ошибка при получении статуса задачи {task_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@tasks_bp.route("/user", methods=["GET"])
@jwt_required()
def get_user_tasks_route():
    """Получение списка задач пользователя."""
    try:
        user_email = get_jwt_identity()
        user = get_user_by_email(user_email)
        
        if not user:
            return jsonify({
                "success": False,
                "error": ErrorMessages.USER_NOT_FOUND
            }), HTTPStatus.NOT_FOUND
        
        limit = request.args.get("limit", type=int, default=50)
        tasks = get_user_tasks(user["id"], limit=limit)
        
        return jsonify({
            "success": True,
            "tasks": tasks
        }), HTTPStatus.OK
        
    except Exception as e:
        logger.error(f"Ошибка при получении задач пользователя: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@tasks_bp.route("/<int:task_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_task_route(task_id: int):
    """Отмена задачи."""
    try:
        user_email = get_jwt_identity()
        user = get_user_by_email(user_email)
        
        if not user:
            return jsonify({
                "success": False,
                "error": ErrorMessages.USER_NOT_FOUND
            }), HTTPStatus.NOT_FOUND
        
        success = cancel_task(task_id, user["id"])
        
        if not success:
            return jsonify({
                "success": False,
                "error": "Не удалось отменить задачу"
            }), HTTPStatus.BAD_REQUEST
        
        return jsonify({
            "success": True,
            "message": "Задача отменена"
        }), HTTPStatus.OK
        
    except Exception as e:
        logger.error(f"Ошибка при отмене задачи {task_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR
