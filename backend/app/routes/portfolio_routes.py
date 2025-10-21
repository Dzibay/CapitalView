from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import asyncio
from app.services.supabase_service import *
from app.services.portfolio_service import (
    get_user_portfolios,
    get_portfolio_assets,
    get_portfolio_transactions,
    get_portfolio_value_history,
    import_broker_portfolio,
    clear_portfolio,
    get_user_portfolio_parent,
    update_portfolio_description
)
from app.services.user_service import get_user_by_email

portfolio_bp = Blueprint("portfolio", __name__)

@portfolio_bp.route("/list", methods=["GET"])
@jwt_required()
def list_portfolios_route():
    user_email = get_jwt_identity()
    data = asyncio.run(get_user_portfolios(user_email))
    return jsonify(data)

@portfolio_bp.route("/add", methods=["POST"])
@jwt_required()
def add_portfolio_route():
    user_email = get_jwt_identity()
    user_id = get_user_by_email(user_email)["id"]

    data = request.get_json()
    parent_portfolio_id = data.get("parent_portfolio_id")
    portfolio_name = data.get("name")

    if not parent_portfolio_id:
        parent_portfolio_id = asyncio.run(get_user_portfolio_parent(user_email))["id"]
        print(parent_portfolio_id)

    insert_data = {
        "user_id": user_id,
        "parent_portfolio_id": parent_portfolio_id,
        "name": portfolio_name,
        "description": {}
    }
    res = table_insert("portfolios", insert_data)
    return jsonify({"success": True, "portfolio": res[0]}), 201

@portfolio_bp.route("/<int:portfolio_id>/delete", methods=["DELETE"])
@jwt_required()
def delete_portfolio_route(portfolio_id):
    print('Запрос удаления портфеля', portfolio_id)
    data = asyncio.run(clear_portfolio(portfolio_id, True))
    return jsonify(data)

@portfolio_bp.route("/<int:portfolio_id>/clear", methods=["POST"])
@jwt_required()
def portfolio_clear_route(portfolio_id):
    print('Запрос очистки портфеля', portfolio_id)
    data = asyncio.run(clear_portfolio(portfolio_id))
    return jsonify(data)

@portfolio_bp.route("/<int:portfolio_id>/assets", methods=["GET"])
@jwt_required()
def portfolio_assets_route(portfolio_id):
    data = asyncio.run(get_portfolio_assets(portfolio_id))
    return jsonify(data)

@portfolio_bp.route("/add_transaction", methods=["POST"])
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
    res_transaction = supabase.table("transactions").insert(tx_data).execute()

    if not res_transaction.data:
        return jsonify({"success": False, "error": "Ошибка при добавлении транзакции"}), 500

    # --- 2️⃣ Проверяем наличие цены ---
    existing_price = (
        supabase.table("asset_prices")
        .select("id")
        .eq("asset_id", asset_id)
        .eq("trade_date", tx_date)
        .execute()
    )

    # --- 3️⃣ Если цены нет — добавляем ---
    if not existing_price.data:
        supabase.table("asset_prices").insert({
            "asset_id": asset_id,
            "price": price,
            "trade_date": tx_date
        }).execute()

    # --- 4️⃣ Обновляем расчёты по портфельному активу ---
    supabase.rpc("update_portfolio_asset", {"pa_id": portfolio_asset_id}).execute()

    return jsonify({"success": True, "transaction": res_transaction.data[0]}), 201


@portfolio_bp.route("/<int:portfolio_id>/description", methods=["POST"])
@jwt_required()
def update_portfolio_description_route(portfolio_id):
    user_email = get_jwt_identity()
    data = request.get_json()

    text = data.get("text")
    capital_target_name = data.get("capital_target_name")
    capital_target_value = data.get("capital_target_value")
    capital_target_deadline = data.get("capital_target_deadline")
    capital_target_currency = data.get("capital_target_currency", "RUB")

    try:
        # Можно дополнительно проверить, что портфель принадлежит пользователю
        updated = update_portfolio_description(
            portfolio_id,
            text=text,
            capital_target_name=capital_target_name,
            capital_target_value=capital_target_value,
            capital_target_deadline=capital_target_deadline,
            capital_target_currency=capital_target_currency
        )
        return jsonify({"success": True, "description": updated}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@portfolio_bp.route("/<int:portfolio_id>/history", methods=["GET"])
@jwt_required()
def portfolio_history_route(portfolio_id):
    data = asyncio.run(get_portfolio_value_history(portfolio_id))
    return jsonify(data)


@portfolio_bp.route("/import_broker", methods=["POST"])
@jwt_required()
async def import_broker_route():
    print('📥 Запрос универсального импорта портфеля')

    data = request.get_json()
    user_email = get_jwt_identity()

    broker_id = data.get("broker_id")          # например, "tinkoff" или "bybit"
    token = data.get("token")
    portfolio_id = data.get("portfolio_id")
    portfolio_name = data.get("portfolio_name")

    if not broker_id:
        return jsonify({"success": False, "error": "Не указан брокер"}), 400
    if not token:
        return jsonify({"success": False, "error": "Не указан токен или API-ключ брокера"}), 400

    try:
        # 1️⃣ Получаем пользователя
        user = get_user_by_email(user_email)
        user_id = user["id"]

        # 3️⃣ Создание или очистка портфеля
        if not portfolio_id:
            user_parent_portfolio = await get_user_portfolio_parent(user_email)
            new_portfolio = {
                "user_id": user_id,
                "parent_portfolio_id": user_parent_portfolio["id"],
                "name": portfolio_name,
                "description": f"Импорт из брокера {broker_id} — {datetime.utcnow().isoformat()}",
            }
            res = supabase.table("portfolios").insert(new_portfolio).execute()
            if not res.data:
                return jsonify({"success": False, "error": "Ошибка при создании портфеля"}), 500
            portfolio_id = res.data[0]["id"]
            print(f"✅ Создан новый портфель (id={portfolio_id})")
        else:
            print(f"⚙️ Очищаем существующий портфель {portfolio_id}...")
            await clear_portfolio(portfolio_id)

        # 4️⃣ Импорт данных в зависимости от брокера
        print(f"🚀 Импортируем данные брокера: {broker_id}")

        broker_data = None
        if broker_id == 1:
            from app.services.integrations.tinkoff_import import get_tinkoff_portfolio
            broker_data = get_tinkoff_portfolio(token, 365)
            result = await import_broker_portfolio(user_email, portfolio_id, broker_data)

        elif broker_id == 2:
            from app.services.integrations.bybit_import import import_bybit_portfolio
            result = await import_bybit_portfolio(user_email, portfolio_id)

        else:
            return jsonify({"success": False, "error": f"Импорт для брокера {broker_id} не реализован"}), 400

        # 5️⃣ Создаём или обновляем связь в user_broker_connections
        connection_res = table_select(
            "user_broker_connections",
            "*",
            {"user_id": user_id, "broker_id": broker_id, "portfolio_id": portfolio_id}
        )

        conn_data = {
            "user_id": user_id,
            "broker_id": broker_id,
            "portfolio_id": portfolio_id,
            "api_key": token,
            "last_sync_at": datetime.utcnow().isoformat(),
        }

        if connection_res:
            supabase.table("user_broker_connections") \
                .update(conn_data) \
                .eq("id", connection_res[0]["id"]) \
                .execute()
        else:
            supabase.table("user_broker_connections").insert(conn_data).execute()

        print(f"✅ Импорт брокера {broker_id} завершён успешно")

        return jsonify({
            "success": True,
            "message": f"Импорт из {broker_id} завершён успешно",
            "portfolio_id": portfolio_id,
            "import_result": result,
        }), 201

    except Exception as e:
        print("❌ Ошибка при импорте брокера:", e)
        return jsonify({"success": False, "error": str(e)}), 500
