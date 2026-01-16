from flask import Blueprint, jsonify
import asyncio
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.user_service import get_user_by_email
from app.services.analitics_service import get_user_portfolios_analytics
from app.constants import HTTPStatus, ErrorMessages
import logging

logger = logging.getLogger(__name__)

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/portfolios", methods=["GET"])
@jwt_required()
def user_portfolios_analytics_route():
    """
    Возвращает сводную аналитику по всем портфелям пользователя.
    ---
    tags:
      - Analytics
    summary: Аналитика портфелей
    description: Возвращает аналитику по всем портфелям пользователя
    security:
      - Bearer: []
    produces:
      - application/json
    responses:
      200:
        description: Аналитика портфелей
        schema:
          type: object
          properties:
            success:
              type: boolean
            analytics:
              type: object
      401:
        description: Требуется аутентификация
      404:
        description: Пользователь не найден
      500:
        description: Внутренняя ошибка сервера
    """
    try:
        user_email = get_jwt_identity()
        logger.info(f"📊 Запрос аналитики всех портфелей для пользователя {user_email}")

        # Получаем id пользователя
        user = get_user_by_email(user_email)
        if not user:
            return jsonify({
                "success": False,
                "error": ErrorMessages.USER_NOT_FOUND
            }), HTTPStatus.NOT_FOUND

        user_id = user["id"]

        data = asyncio.run(get_user_portfolios_analytics(user_id))
        
        return jsonify({
            "success": True,
            "analytics": data
        }), HTTPStatus.OK

    except Exception as e:
        logger.error(f"❌ Ошибка при получении аналитики: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR



