from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.transactions_service import get_transactions
from app.services.supabase_service import table_select, table_insert, table_delete, table_update, rpc
from app.services.user_service import get_user_by_email
from app.services.supabase_service import refresh_materialized_view

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
    refresh_materialized_view('portfolio_daily_positions')
    refresh_materialized_view('portfolio_daily_values')

    return jsonify({"success": True, "transaction": res_transaction[0]}), 201

@transactions_bp.route("/", methods=["DELETE"])
@jwt_required()
def delete_transactions_route():
    """Удаление нескольких транзакций и обновление связанных активов."""
    payload = request.get_json()
    ids = payload.get("ids", [])
    print(ids)

    if not ids:
        return jsonify({"success": False, "error": "Список ID пуст"}), 400

    try:
        # --- 1️⃣ Получаем portfolio_asset_id для удаляемых транзакций ---
        affected_rows = table_select(
            "transactions",
            select="portfolio_asset_id",
            in_filters={"id": ids}
        )

        # фильтруем уникальные значения, игнорируя None
        affected_assets = list({row["portfolio_asset_id"] for row in affected_rows if row["portfolio_asset_id"]})


        # --- 2️⃣ Удаляем транзакции ---
        deleted = table_delete("transactions", in_filters={"id": ids})
        print(deleted)

        # --- 3️⃣ Обновляем все затронутые активы ---
        print(affected_assets)
        if affected_assets:
            rpc("update_assets_after_tx_delete", {"asset_ids": affected_assets})
            refresh_materialized_view('portfolio_daily_positions')
            refresh_materialized_view('portfolio_daily_values')

        return jsonify({
            "success": True,
            "deleted": len(deleted),
            "updated_assets": len(affected_assets)
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@transactions_bp.route("/", methods=["PUT"])
@jwt_required()
def update_transaction_route():
    """Обновление данных транзакции по ID."""
    payload = request.get_json()
    print(payload)
    
    tx_id = payload.get("transaction_id")
    if not tx_id:
        return jsonify({"success": False, "error": "Не указан ID транзакции"}), 400

    # Получаем portfolio_asset_id из базы, если его нет в payload
    pa_id = payload.get("portfolio_asset_id")
    if not pa_id:
        tx_record = table_select("transactions", select="portfolio_asset_id", filters={"id": tx_id})
        if tx_record and len(tx_record) > 0:
            pa_id = tx_record[0].get("portfolio_asset_id")

    # Формируем словарь только с реально переданными данными
    update_data = {
        "transaction_type": 1 if payload.get("transaction_type") == 'Покупка' else 2,
        "price": payload.get("price"),
        "quantity": payload.get("quantity"),
        "transaction_date": payload.get("transaction_date")
    }
    # Убираем ключи со значением None
    update_data = {k: v for k, v in update_data.items() if v is not None}

    if not update_data:
        return jsonify({"success": False, "error": "Нет данных для обновления"}), 400

    try:
        res = table_update("transactions", update_data, {"id": tx_id})

        if not res:
            return jsonify({"success": False, "error": "Транзакция не найдена"}), 404

        # Если есть portfolio_asset_id — пересчитаем актив
        if pa_id:
            rpc("update_portfolio_asset", {"pa_id": pa_id})
            refresh_materialized_view('portfolio_daily_positions')
            refresh_materialized_view('portfolio_daily_values')

        return jsonify({"success": True, "updated": res[0]}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
