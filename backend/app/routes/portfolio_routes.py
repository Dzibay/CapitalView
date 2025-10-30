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
    """
    Импорт или синхронизация портфелей с брокером (например, Тинькофф).
    Работает с двухуровневой структурой: родительский + дочерние портфели.
    """
    print('📥 Запрос универсального импорта портфеля')

    data = request.get_json()
    user_email = get_jwt_identity()

    broker_id = data.get("broker_id")          # например, 1 = Tinkoff
    token = data.get("token")
    portfolio_id = data.get("portfolio_id")    # id родительского портфеля
    portfolio_name = data.get("portfolio_name")

    if not broker_id:
        return jsonify({"success": False, "error": "Не указан брокер"}), 400
    if not token:
        return jsonify({"success": False, "error": "Не указан токен или API-ключ брокера"}), 400

    try:
        # === 1️⃣ Получаем пользователя ===
        user = get_user_by_email(user_email)
        user_id = user["id"]

        # === 2️⃣ Создание или поиск родительского портфеля ===
        if not portfolio_id:
            user_root_portfolio = await get_user_portfolio_parent(user_email)
            new_portfolio = {
                "user_id": user_id,
                "parent_portfolio_id": user_root_portfolio["id"],
                "name": portfolio_name or f"Портфель {broker_id}",
                "description": f"Импорт из брокера {broker_id} — {datetime.utcnow().isoformat()}",
            }
            res = supabase.table("portfolios").insert(new_portfolio).execute()
            if not res.data:
                return jsonify({"success": False, "error": "Ошибка при создании портфеля"}), 500
            portfolio_id = res.data[0]["id"]
            print(f"✅ Создан новый родительский портфель id={portfolio_id}")
        else:
            print(f"🔁 Синхронизация существующего портфеля id={portfolio_id}")

        # === 3️⃣ Получаем данные от брокера ===
        print(f"🚀 Импортируем данные брокера: {broker_id}")

        if broker_id == 1:
            from app.services.integrations.tinkoff_import import get_tinkoff_portfolio
            broker_data = get_tinkoff_portfolio(token, 365)
        else:
            return jsonify({"success": False, "error": f"Импорт для брокера {broker_id} не реализован"}), 400

        # === 4️⃣ Синхронизация портфелей и активов ===
        from app.services.portfolio_service import import_broker_portfolio
        result = await import_broker_portfolio(user_email, portfolio_id, broker_data)

        # === 5️⃣ Обновляем user_broker_connections ===
        conn_data = {
            "user_id": user_id,
            "broker_id": broker_id,
            "portfolio_id": portfolio_id,
            "api_key": token,
            "last_sync_at": datetime.utcnow().isoformat(),
        }

        existing_conn = table_select(
            "user_broker_connections",
            "*",
            {"user_id": user_id, "broker_id": broker_id, "portfolio_id": portfolio_id}
        )
        if existing_conn:
            supabase.table("user_broker_connections") \
                .update(conn_data) \
                .eq("id", existing_conn[0]["id"]) \
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

