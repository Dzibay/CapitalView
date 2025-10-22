from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.transactions_service import get_transactions
from app.services.supabase_service import table_select, table_insert, rpc
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

@transactions_bp.route("/", methods=["POST"])
@jwt_required()
def add_transaction_route():
    """Добавление транзакции и автоматическое создание цены актива, если на дату её нет."""
    payload = request.get_json()
    user_email = get_jwt_identity()
    user_id = get_user_by_email(user_email)["id"]

    portfolio_asset_id = payload.get("portfolio_asset_id")
    asset_id = payload.get("asset_id")        # только для asset_prices
    tx_date = payload.get("transaction_date")
    price = payload.get("price")

    # --- 1️⃣ Добавляем транзакцию ---
    tx_data = {
        "user_id": user_id,
        "portfolio_asset_id": portfolio_asset_id,
        "transaction_type": payload.get("transaction_type"),
        "quantity": payload.get("quantity"),
        "price": price,
        "transaction_date": tx_date,
    }
    res_transaction = table_insert("transactions", tx_data)

    if not res_transaction:
        return jsonify({"success": False, "error": "Ошибка при добавлении транзакции"}), 500

    # --- 2️⃣ Проверяем наличие цены ---
    existing_price = (table_select("asset_prices", "id", filters={"asset_id": asset_id, "trade_date": tx_date}))

    # --- 3️⃣ Если цены нет — добавляем ---
    if not existing_price:
        table_insert("asset_prices", {"asset_id": asset_id, "price": price, "trade_date": tx_date})
        

    # --- 4️⃣ Обновляем расчёты по портфельному активу ---
    rpc("update_portfolio_asset", {"pa_id": portfolio_asset_id})

    return jsonify({"success": True, "transaction": res_transaction[0]}), 201