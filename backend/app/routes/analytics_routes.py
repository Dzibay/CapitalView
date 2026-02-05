from flask import Blueprint
from flask_jwt_extended import jwt_required
import asyncio
from app.decorators import require_user, handle_errors
from app.utils.response_helpers import success_response, not_found_response
from app.services.analytics_service import get_user_portfolios_analytics
from app.constants import HTTPStatus
import logging

logger = logging.getLogger(__name__)

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/portfolios", methods=["GET"])
@jwt_required()
@require_user
@handle_errors
def user_portfolios_analytics_route(user):
    """Получение аналитики всех портфелей пользователя."""
    logger.info(f"📊 Запрос аналитики всех портфелей для пользователя {user['email']}")
    
    # Примечание: asyncio.run блокирует event loop, но для совместимости оставляем
    # В будущем можно переделать на полностью синхронный код или использовать Quart
    data = asyncio.run(get_user_portfolios_analytics(user["id"]))
    
    return success_response(data={"analytics": data})
