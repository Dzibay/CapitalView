from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.services.operations_service import get_operations
from app.constants import HTTPStatus
from app.decorators import require_user, handle_errors
from app.utils.response_helpers import success_response
from app.utils.date_utils import parse_date_range
import logging

logger = logging.getLogger(__name__)

operations_bp = Blueprint("operations", __name__)

@operations_bp.route("/", methods=["GET"])
@jwt_required()
@require_user
@handle_errors
def get_operations_route(user):
    """Получение списка операций пользователя."""
    # Парсинг query параметров
    portfolio_id = request.args.get("portfolio_id", type=int)
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    limit = request.args.get("limit", type=int, default=1000)

    # Используем единую утилиту для парсинга дат
    start_date, end_date = parse_date_range(start_date_str, end_date_str)

    data = get_operations(user["id"], portfolio_id, start_date, end_date, limit)

    return success_response(data={"operations": data})
