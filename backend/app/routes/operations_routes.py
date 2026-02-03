from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.operations_service import get_operations
from app.services.user_service import get_user_by_email
from app.constants import HTTPStatus, ErrorMessages
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

operations_bp = Blueprint("operations", __name__)

@operations_bp.route("/", methods=["GET"])
@jwt_required()
def get_operations_route():
    try:
        user_email = get_jwt_identity()
        user = get_user_by_email(user_email)
        
        if not user:
            return jsonify({
                "success": False,
                "error": ErrorMessages.USER_NOT_FOUND
            }), HTTPStatus.NOT_FOUND
        
        user_id = user["id"]

        # Парсинг query параметров
        portfolio_id = request.args.get("portfolio_id", type=int)
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")
        limit = request.args.get("limit", type=int, default=1000)

        # Преобразование строк в datetime если нужно
        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
            except:
                start_date = start_date_str
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            except:
                end_date = end_date_str

        data = get_operations(user_id, portfolio_id, start_date, end_date, limit)

        return jsonify({
            "success": True,
            "operations": data
        }), HTTPStatus.OK

    except Exception as e:
        logger.error(f"Ошибка при получении операций: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR
