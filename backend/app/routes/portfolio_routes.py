from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import asyncio
from pydantic import ValidationError
from app.services.supabase_service import table_select, table_insert, rpc
from app.services.portfolio_service import (
    get_user_portfolios,
    get_portfolio_assets,
    get_portfolio_value_history,
    get_user_portfolio_parent,
    update_portfolio_description,
    get_portfolio_info,
    get_portfolio_summary,
    get_portfolio_transactions
)
from app.services.user_service import get_user_by_email
from app.models.portfolio_models import (
    CreatePortfolioRequest,
    UpdatePortfolioDescriptionRequest,
    ImportBrokerRequest
)
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
import logging

logger = logging.getLogger(__name__)

portfolio_bp = Blueprint("portfolio", __name__)

@portfolio_bp.route("/list", methods=["GET"])
@jwt_required()
def list_portfolios_route():
    try:
        user_email = get_jwt_identity()
        data = asyncio.run(get_user_portfolios(user_email))
        return jsonify({
            "success": True,
            "portfolios": data
        }), HTTPStatus.OK
    except Exception as e:
        logger.error(f"Ошибка при получении списка портфелей: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@portfolio_bp.route("/add", methods=["POST"])
@jwt_required()
def add_portfolio_route():
    try:
        # Валидация входных данных
        data = CreatePortfolioRequest(**request.get_json())
        
        user_email = get_jwt_identity()
        user = get_user_by_email(user_email)
        
        if not user:
            return jsonify({
                "success": False,
                "error": ErrorMessages.USER_NOT_FOUND
            }), HTTPStatus.NOT_FOUND
        
        user_id = user["id"]
        parent_portfolio_id = data.parent_portfolio_id

        # Если не указан родительский портфель, получаем корневой
        if not parent_portfolio_id:
            parent_portfolio = asyncio.run(get_user_portfolio_parent(user_email))
            parent_portfolio_id = parent_portfolio["id"]

        insert_data = {
            "user_id": user_id,
            "parent_portfolio_id": parent_portfolio_id,
            "name": data.name,
            "description": data.description or {}
        }
        
        res = table_insert("portfolios", insert_data)
        
        if not res:
            return jsonify({
                "success": False,
                "error": "Ошибка при создании портфеля"
            }), HTTPStatus.INTERNAL_SERVER_ERROR
        
        return jsonify({
            "success": True,
            "message": SuccessMessages.PORTFOLIO_CREATED,
            "portfolio": res[0]
        }), HTTPStatus.CREATED
        
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": ErrorMessages.VALIDATION_ERROR,
            "details": e.errors()
        }), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.error(f"Ошибка при создании портфеля: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@portfolio_bp.route("/<int:portfolio_id>/delete", methods=["DELETE"])
@jwt_required()
def delete_portfolio_route(portfolio_id):
    try:
        logger.info(f"Запрос удаления портфеля {portfolio_id}")
        rpc("clear_portfolio_full", {"p_portfolio_id": portfolio_id, "p_delete_self": True})
        return jsonify({
            "success": True,
            "message": SuccessMessages.PORTFOLIO_DELETED
        }), HTTPStatus.OK
    except Exception as e:
        logger.error(f"Ошибка при удалении портфеля {portfolio_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@portfolio_bp.route("/<int:portfolio_id>/clear", methods=["POST"])
@jwt_required()
def portfolio_clear_route(portfolio_id):
    """Очистка портфеля (удаление всех активов и транзакций)."""
    try:
        logger.info(f"Запрос очистки портфеля {portfolio_id}")
        rpc("clear_portfolio_full", {"p_portfolio_id": portfolio_id})
        return jsonify({
            "success": True,
            "message": "Портфель успешно очищен"
        }), HTTPStatus.OK
    except Exception as e:
        logger.error(f"Ошибка при очистке портфеля {portfolio_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@portfolio_bp.route("/<int:portfolio_id>/assets", methods=["GET"])
@jwt_required()
def portfolio_assets_route(portfolio_id):
    try:
        data = asyncio.run(get_portfolio_assets(portfolio_id))
        return jsonify({
            "success": True,
            "assets": data
        }), HTTPStatus.OK
    except Exception as e:
        logger.error(f"Ошибка при получении активов портфеля {portfolio_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@portfolio_bp.route("/<int:portfolio_id>/description", methods=["POST"])
@jwt_required()
def update_portfolio_description_route(portfolio_id):
    """Обновление описания портфеля."""
    try:
        # Валидация входных данных
        data = UpdatePortfolioDescriptionRequest(**request.get_json())
        
        updated = update_portfolio_description(
            portfolio_id,
            text=data.text,
            capital_target_name=data.capital_target_name,
            capital_target_value=data.capital_target_value,
            capital_target_deadline=data.capital_target_deadline,
            capital_target_currency=data.capital_target_currency
        )
        
        return jsonify({
            "success": True,
            "message": SuccessMessages.PORTFOLIO_UPDATED,
            "description": updated
        }), HTTPStatus.OK
        
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": ErrorMessages.VALIDATION_ERROR,
            "details": e.errors()
        }), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.error(f"Ошибка при обновлении описания портфеля {portfolio_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@portfolio_bp.route("/<int:portfolio_id>/history", methods=["GET"])
@jwt_required()
def portfolio_history_route(portfolio_id):
    """Получение истории стоимости портфеля."""
    try:
        data = asyncio.run(get_portfolio_value_history(portfolio_id))
        return jsonify({
            "success": True,
            "history": data
        }), HTTPStatus.OK
    except Exception as e:
        logger.error(f"Ошибка при получении истории портфеля {portfolio_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@portfolio_bp.route("/<int:portfolio_id>", methods=["GET"])
@jwt_required()
def get_portfolio_info_route(portfolio_id):
    try:
        result = get_portfolio_info(portfolio_id)
        
        if not result.get("success"):
            status_code = HTTPStatus.NOT_FOUND if "не найден" in result.get("error", "") else HTTPStatus.INTERNAL_SERVER_ERROR
            return jsonify(result), status_code
        
        return jsonify(result), HTTPStatus.OK
        
    except Exception as e:
        logger.error(f"Ошибка при получении информации о портфеле {portfolio_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@portfolio_bp.route("/<int:portfolio_id>/summary", methods=["GET"])
@jwt_required()
def get_portfolio_summary_route(portfolio_id):
    try:
        result = get_portfolio_summary(portfolio_id)
        
        if not result.get("success"):
            status_code = HTTPStatus.NOT_FOUND if "не найден" in result.get("error", "") else HTTPStatus.INTERNAL_SERVER_ERROR
            return jsonify(result), status_code
        
        return jsonify(result), HTTPStatus.OK
        
    except Exception as e:
        logger.error(f"Ошибка при получении сводки портфеля {portfolio_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@portfolio_bp.route("/<int:portfolio_id>/transactions", methods=["GET"])
@jwt_required()
def get_portfolio_transactions_route(portfolio_id):
    try:
        data = asyncio.run(get_portfolio_transactions(portfolio_id))
        return jsonify({
            "success": True,
            "transactions": data
        }), HTTPStatus.OK
        
    except Exception as e:
        logger.error(f"Ошибка при получении транзакций портфеля {portfolio_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@portfolio_bp.route("/import_broker", methods=["POST"])
@jwt_required()
async def import_broker_route():
    try:
        # Валидация входных данных
        data = ImportBrokerRequest(**request.get_json())
        
        logger.info(f"📥 Запрос универсального импорта портфеля от брокера {data.broker_id}")
        user_email = get_jwt_identity()

        # === 1️⃣ Получаем пользователя ===
        user = get_user_by_email(user_email)
        if not user:
            return jsonify({
                "success": False,
                "error": ErrorMessages.USER_NOT_FOUND
            }), HTTPStatus.NOT_FOUND
        
        user_id = user["id"]

        # === 2️⃣ Создание или поиск родительского портфеля ===
        portfolio_id = data.portfolio_id
        if not portfolio_id:
            user_root_portfolio = await get_user_portfolio_parent(user_email)
            new_portfolio = {
                "user_id": user_id,
                "parent_portfolio_id": user_root_portfolio["id"],
                "name": data.portfolio_name or f"Портфель {data.broker_id}",
                "description": f"Импорт из брокера {data.broker_id} — {datetime.utcnow().isoformat()}",
            }
            res = table_insert("portfolios", new_portfolio)
            if not res:
                return jsonify({
                    "success": False,
                    "error": "Ошибка при создании портфеля"
                }), HTTPStatus.INTERNAL_SERVER_ERROR
            portfolio_id = res[0]["id"]
            logger.info(f"✅ Создан новый родительский портфель id={portfolio_id}")
        else:
            logger.info(f"🔁 Синхронизация существующего портфеля id={portfolio_id}")

        # === 3️⃣ Получаем данные от брокера ===
        logger.info(f"🚀 Импортируем данные брокера: {data.broker_id}")

        from app.constants import BrokerID
        if data.broker_id == BrokerID.TINKOFF:
            from app.services.integrations.tinkoff_import import get_tinkoff_portfolio
            broker_data = get_tinkoff_portfolio(data.token, 365)
        else:
            return jsonify({
                "success": False,
                "error": f"Импорт для брокера {data.broker_id} не реализован"
            }), HTTPStatus.BAD_REQUEST

        # === 4️⃣ Синхронизация портфелей и активов ===
        from app.services.portfolio_service import import_broker_portfolio
        result = await import_broker_portfolio(user_email, portfolio_id, broker_data)

        # === 5️⃣ Обновляем user_broker_connections ===
        from app.services.broker_connections_service import upsert_broker_connection
        upsert_broker_connection(user_id, data.broker_id, portfolio_id, data.token)

        logger.info(f"✅ Импорт брокера {data.broker_id} завершён успешно")

        return jsonify({
            "success": True,
            "message": SuccessMessages.BROKER_IMPORT_SUCCESS,
            "portfolio_id": portfolio_id,
            "import_result": result,
        }), HTTPStatus.CREATED

    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": ErrorMessages.VALIDATION_ERROR,
            "details": e.errors()
        }), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.error(f"❌ Ошибка при импорте брокера: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR

