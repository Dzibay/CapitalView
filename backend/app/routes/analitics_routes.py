from flask import Blueprint, jsonify
import asyncio
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.user_service import get_user_by_email
from app.services.analitics_service import get_user_portfolios_analytics

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/portfolios", methods=["GET"])
@jwt_required()
def user_portfolios_analytics_route():
    """Возвращает сводную аналитику по всем портфелям пользователя."""
    user_email = get_jwt_identity()
    print(f"📊 Запрос аналитики всех портфелей для пользователя {user_email}")

    try:
        # Получаем id пользователя
        user = get_user_by_email(user_email)
        if not user:
            return jsonify({"success": False, "error": "Пользователь не найден"}), 404

        user_id = user["id"]

        data = asyncio.run(get_user_portfolios_analytics(user_id))
        return jsonify({"success": True, "analytics": data}), 200

    except Exception as e:
        print(f"❌ Ошибка при получении аналитики: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



