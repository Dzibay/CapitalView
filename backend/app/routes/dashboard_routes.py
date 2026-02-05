from flask import Blueprint
from flask_jwt_extended import jwt_required
import asyncio
import time
from app.services.dashboard_service import get_dashboard_data
from app.constants import HTTPStatus, ErrorMessages
from app.decorators import require_user, handle_errors
from app.utils.response_helpers import success_response
import logging

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/", methods=["GET"])
@jwt_required()
@require_user
@handle_errors
def dashboard(user):
    """Получение данных дашборда пользователя."""
    logger.info('Запрос на дашборд получен')
    start = time.time()
    
    # Примечание: Flask не поддерживает async routes напрямую
    # Используем asyncio.run для вызова async функции
    # В будущем можно переделать на полностью синхронный код или использовать Quart
    data = asyncio.run(get_dashboard_data(user["email"]))
    
    elapsed_time = time.time() - start
    logger.info(f'Данные сформированы за {elapsed_time:.2f} секунд')
    
    return success_response(data={"data": data})
