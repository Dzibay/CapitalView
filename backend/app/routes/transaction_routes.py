from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.transactions_service import get_transactions
from app.services.supabase_service import rpc
from app.services.user_service import get_user_by_email

transactions_bp = Blueprint("transactions", __name__)

# 🔹 Получение транзакций с фильтрацией по активу, портфелю и периоду
@transactions_bp.route("/", methods=["GET"])
@jwt_required()
def get_transactions_route():
    user_email = get_jwt_identity()
    user_id = get_user_by_email(user_email)["id"]

    asset_name = request.args.get("asset_name")
    portfolio_id = request.args.get("portfolio_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    limit = request.args.get("limit")

    limit = int(limit) if limit else None
    portfolio_id = int(portfolio_id) if portfolio_id else None

    data = get_transactions(user_id, portfolio_id, asset_name, start_date, end_date, limit)

    return jsonify(data)

