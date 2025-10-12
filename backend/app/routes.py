from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.supabase_service import *
from app import bcrypt
from app.tinkoff_service import get_full_portfolio
from datetime import datetime

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/check-token", methods=["GET"])
@jwt_required()
def check_token():
    # Получаем identity пользователя из токена
    user_email = get_jwt_identity()
    return jsonify({"msg": "Token is valid", "user": get_user_by_email(user_email)}), 200

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if get_user_by_email(email):
        return jsonify({"msg": "User already exists"}), 400

    create_user(email, password)
    return jsonify({"msg": "User created successfully"}), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = get_user_by_email(email)
    if not user or not bcrypt.check_password_hash(user["password_hash"], password):
        return jsonify({"msg": "Invalid email or password"}), 401

    access_token = create_access_token(identity=user["email"])
    return jsonify({"access_token": access_token})


assets_bp = Blueprint("assets", __name__)

@assets_bp.route("/get_all", methods=["GET"])
@jwt_required()
def get_assets():
    user_email = get_jwt_identity()
    
    assets = get_all_assets(user_email)
    return jsonify({"portfolios": assets})

@assets_bp.route("/add", methods=["POST"])
@jwt_required()
def add_asset():
    user_email = get_jwt_identity()
    data = request.get_json()

    try:
        asset = add_asset_transaction(user_email, data)
        return jsonify(asset), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@assets_bp.route('/delete/<int:asset_id>', methods=['DELETE'])
@jwt_required()
def delete_asset_route(asset_id):
    user_email = get_jwt_identity()

    try:
        deleted = delete_asset(asset_id)
        if deleted:
            return jsonify(deleted), 200
        else:
            return jsonify({"success": False, "message": "Asset not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@assets_bp.route("/sell", methods=["POST"])
@jwt_required()
def sell_asset_route():
    user_email = get_jwt_identity()

    data = request.get_json()
    portfolio_asset_id = data.get("portfolio_asset_id")
    quantity = data.get("quantity")
    price = data.get("price")
    date = data.get("date")

    try:
        result = sell_asset(portfolio_asset_id, quantity, price, date)
        return jsonify(result), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@assets_bp.route("/references", methods=["GET"])
def get_asset_references():
    """Возвращает справочные данные для формы добавления актива."""
    try:
        asset_types = get_asset_types()
        currencies = get_currencies()
        assets = get_existing_assets()
        return jsonify({
            "asset_types": asset_types,
            "currencies": currencies,
            "assets": assets
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@assets_bp.route("/import_tinkoff_portfolio", methods=["POST"])
@jwt_required()
def import_tinkoff_portfolio_route():
    user_email = get_jwt_identity()
    data = request.get_json()

    token = data.get("token")
    portfolio_name = data.get("portfolio_name")

    if not token or not portfolio_name:
        return jsonify({"success": False, "error": "Не указан токен или название портфеля"}), 400

    try:
        # Создаём новый портфель
        user = get_user_by_email(user_email)
        user_id = user["id"]

        new_portfolio = {
            "user_id": user_id,
            "name": portfolio_name,
            "description": f"Импорт из Tinkoff {datetime.utcnow().isoformat()}"
        }
        print('Создаем портфель')
        res = supabase.table("portfolios").insert(new_portfolio).execute()
        if not res.data:
            return jsonify({"success": False, "error": "Ошибка при создании портфеля"}), 500
        portfolio_id = res.data[0]["id"]

        # Получаем данные из Tinkoff и импортируем
        print('Получаем данные тинькофф')
        tinkoff_data = get_full_portfolio(token)
        print('Получили данные')
        import_result = import_tinkoff_portfolio_to_db(user_email, portfolio_id, tinkoff_data)

        return jsonify({
            "success": True,
            "portfolio_id": portfolio_id,
            "message": "Портфель и транзакции успешно импортированы",
            "import_result": import_result
        }), 201

    except Exception as e:
        # всегда возвращаем JSON, даже при исключении
        return jsonify({"success": False, "error": str(e)}), 500



statistics_bp = Blueprint("statistics", __name__)

@statistics_bp.route("/portfolio_value", methods=["GET"])
@jwt_required()
def get_portfolio_value():
    user_email = get_jwt_identity()
    prices = get_user_portfolio_value(user_email)
    return jsonify(prices)
