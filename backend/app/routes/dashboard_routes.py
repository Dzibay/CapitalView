from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.dashboard_service import get_dashboard_data
from app.constants import HTTPStatus, ErrorMessages
import time
import logging

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/", methods=["GET"])
@jwt_required()
async def dashboard():
    try:
        logger.info('Запрос на дашборд получен')
        email = get_jwt_identity()
        start = time.time()
        
        data = await get_dashboard_data(email)
        
        elapsed_time = time.time() - start
        logger.info(f'Данные сформированы за {elapsed_time:.2f} секунд')
        
        return jsonify({
            "success": True,
            "data": data
        }), HTTPStatus.OK
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных дашборда: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR
