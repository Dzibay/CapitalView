import json
from app.infrastructure.database.database_service import rpc_async
from app.domain.services.user_service import get_user_by_email
from datetime import datetime
from app.utils.date import normalize_date_to_string, normalize_date_to_sql_date
from app.core.logging import get_logger
from app.infrastructure.database.repositories.asset_repository import AssetRepository
logger = get_logger(__name__)

_asset_repository = AssetRepository()


async def create_asset(email: str, data: dict):
    """Создает актив в портфеле через RPC функцию с ACID транзакцией."""
    user = await get_user_by_email(email)
    if not user:
        return {"success": False, "error": "Пользователь не найден"}

    user_id = user["id"]

    def normalize_value(value):
        if value is None or value == "None" or value == "":
            return None
        return value

    portfolio_id = normalize_value(data.get("portfolio_id"))
    asset_id = normalize_value(data.get("asset_id"))
    asset_type_id = normalize_value(data.get("asset_type_id"))
    name = data.get("name")
    ticker = data.get("ticker")
    quantity = float(data.get("quantity", 0))
    currency = int(data.get("currency")) if data.get("currency") and data.get("currency") != "None" else None
    price = float(data.get("average_price", 0))
    date = data.get("date") or normalize_date_to_string(datetime.utcnow(), include_time=True)

    if portfolio_id is not None:
        try:
            portfolio_id = int(portfolio_id)
        except (ValueError, TypeError):
            return {"success": False, "error": "Некорректный portfolio_id"}

    if asset_id is not None:
        try:
            asset_id = int(asset_id)
        except (ValueError, TypeError):
            return {"success": False, "error": "Некорректный asset_id"}

    try:
        transaction_date = normalize_date_to_string(date)
        if not transaction_date:
            transaction_date = normalize_date_to_sql_date(datetime.utcnow().date())

        rpc_params = {
            "p_user_id": str(user_id),
            "p_portfolio_id": portfolio_id,
            "p_asset_id": asset_id,
            "p_asset_type_id": asset_type_id,
            "p_name": name,
            "p_ticker": ticker,
            "p_currency_id": currency,
            "p_quantity": quantity,
            "p_price": price,
            "p_transaction_date": transaction_date
        }

        result = await rpc_async("create_portfolio_asset", rpc_params)

        if not result:
            return {"success": False, "error": "Ошибка при создании актива: пустой ответ от RPC"}

        if isinstance(result, str):
            try:
                parsed_result = json.loads(result)
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка при парсинге JSON из RPC: {e}, result: {result}")
                return {"success": False, "error": f"Ошибка при парсинге ответа от RPC: {str(e)}"}
        elif isinstance(result, dict):
            parsed_result = result
        elif isinstance(result, list) and len(result) > 0:
            parsed_result = result[0]
        else:
            return {"success": False, "error": f"Некорректный формат ответа от RPC: {type(result)}"}

        create_deposit_operation = data.get("create_deposit_operation", False)
        if create_deposit_operation and quantity > 0 and price > 0:
            try:
                from app.domain.services.operations_service import apply_operations

                asset_info = parsed_result.get("asset", {})
                asset_id_from_result = asset_info.get("asset_id")
                portfolio_asset_id_from_result = asset_info.get("portfolio_asset_id")

                if asset_id_from_result and portfolio_id:
                    deposit_amount = float(quantity * price)
                    asset_row = await _asset_repository.get_by_id(asset_id_from_result)
                    currency_id = (asset_row.get("quote_asset_id") or 1) if asset_row else 1
                    await apply_operations(
                        user_id=str(user_id),
                        operations=[
                            {
                                "operation_type": 5,
                                "operation_date": transaction_date,
                                "amount": deposit_amount,
                                "currency_id": currency_id,
                                "asset_id": asset_id_from_result,
                                "portfolio_asset_id": portfolio_asset_id_from_result,
                                "portfolio_id": portfolio_id,
                            }
                        ],
                    )
            except Exception as e:
                logger.warning(f"Ошибка при создании операции пополнения для актива: {e}", exc_info=True)

        return parsed_result

    except Exception as e:
        logger.error(f"Ошибка при добавлении актива: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def delete_asset(portfolio_asset_id: int):
    """Удаляет актив из портфеля через RPC функцию."""
    try:
        result = await rpc_async("delete_portfolio_asset", {"p_portfolio_asset_id": portfolio_asset_id})

        if not result:
            return {"success": False, "error": "Ошибка при удалении актива: пустой ответ от RPC"}

        if isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка при парсинге JSON из RPC: {e}, result: {result}")
                return {"success": False, "error": f"Ошибка при парсинге ответа от RPC: {str(e)}"}
        elif isinstance(result, dict):
            return result
        elif isinstance(result, list) and len(result) > 0:
            return result[0]
        else:
            return {"success": False, "error": f"Некорректный формат ответа от RPC: {type(result)}"}

    except Exception as e:
        logger.error(f"Ошибка при удалении актива {portfolio_asset_id}: {e}", exc_info=True)
        return {"success": False, "error": f"Ошибка при удалении актива: {str(e)}"}


async def get_asset_info(asset_id: int):
    """Получает детальную информацию об активе."""
    try:
        asset_info = await _asset_repository.get_by_id(asset_id)
        if not asset_info:
            return {"success": False, "error": "Актив не найден"}

        latest_price = await _asset_repository.get_latest_price(asset_id)
        asset_info["latest_price"] = latest_price

        return {"success": True, "asset": asset_info}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _shape_portfolio_asset_detail_rpc(result: dict) -> dict:
    """Преобразует JSON из get_portfolio_asset_detail / get_asset_detail_for_user в ответ API."""
    portfolio_asset_data = result.get("portfolio_asset")
    if not portfolio_asset_data:
        return {"success": False, "error": "Данные портфельного актива не найдены"}

    portfolio_asset = {
        "id": portfolio_asset_data.get("portfolio_asset_id"),
        "asset_id": portfolio_asset_data.get("asset_id"),
        "portfolio_id": portfolio_asset_data.get("portfolio_id"),
        "quantity": portfolio_asset_data.get("quantity"),
        "leverage": portfolio_asset_data.get("leverage"),
        "average_price": portfolio_asset_data.get("average_price"),
        "last_price": portfolio_asset_data.get("last_price"),
        "daily_change": portfolio_asset_data.get("daily_change"),
        "currency_ticker": portfolio_asset_data.get("currency_ticker"),
        "quote_asset_id": portfolio_asset_data.get("quote_asset_id"),
        "currency_rate_to_rub": portfolio_asset_data.get("currency_rate_to_rub"),
        "name": portfolio_asset_data.get("asset_name"),
        "ticker": portfolio_asset_data.get("ticker"),
        "type": portfolio_asset_data.get("asset_type"),
        "transactions": result.get("transactions", []),
        "transactions_count": len(result.get("transactions", [])),
        "all_payouts": result.get("all_payouts", []),
        "payouts_count": len(result.get("all_payouts", [])),
        "daily_values": result.get("daily_values", []),
        "cash_operations": result.get("cash_operations", []),
        "price_history": result.get("price_history", []),
        "asset_value": portfolio_asset_data.get("asset_value"),
        "invested_value": portfolio_asset_data.get("invested_value"),
        "realized_pnl": portfolio_asset_data.get("realized_pnl"),
        "payouts": portfolio_asset_data.get("payouts"),
        "commissions": portfolio_asset_data.get("commissions"),
        "taxes": portfolio_asset_data.get("taxes"),
        "total_pnl": portfolio_asset_data.get("total_pnl")
    }

    portfolios_data = result.get("portfolios", [])
    for portfolio in portfolios_data:
        portfolio_total = portfolio.get("portfolio_total_value") or 0
        asset_value = portfolio.get("asset_value") or 0
        try:
            portfolio_total = float(portfolio_total) if portfolio_total is not None else 0
            asset_value = float(asset_value) if asset_value is not None else 0
        except (ValueError, TypeError):
            portfolio_total = 0
            asset_value = 0
        if portfolio_total > 0:
            portfolio["percentage_in_portfolio"] = round((asset_value / portfolio_total) * 100, 2)
        else:
            portfolio["percentage_in_portfolio"] = 0

    return {
        "success": True,
        "portfolio_asset": portfolio_asset,
        "portfolios": portfolios_data
    }


async def get_asset_daily_values(portfolio_asset_id: int, from_date: str = None, to_date: str = None):
    """Получает историю стоимости актива для графика."""
    try:
        params = {"p_portfolio_asset_id": portfolio_asset_id}
        if from_date:
            params["p_from_date"] = from_date
        if to_date:
            params["p_to_date"] = to_date

        result = await rpc_async("get_portfolio_asset_daily_values", params)

        if result is None:
            return {"success": False, "error": "Не удалось получить данные"}
        if not result:
            return {"success": True, "values": [], "count": 0}

        return {"success": True, "values": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Ошибка при получении истории стоимости актива {portfolio_asset_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def get_portfolio_asset_info(portfolio_asset_id: int, user_id: str):
    """Получает детальную информацию о портфельном активе."""
    try:
        if not user_id:
            return {"success": False, "error": "user_id обязателен для получения информации об активе"}

        result = await rpc_async("get_portfolio_asset_detail", {
            "p_portfolio_asset_id": portfolio_asset_id,
            "p_user_id": user_id,
            "p_include_price_history": True,
            "p_price_history_limit": 100000
        })

        if not result:
            return {"success": False, "error": "Портфельный актив не найден"}

        portfolio_asset_data = result.get("portfolio_asset")
        if not portfolio_asset_data:
            return {"success": False, "error": "Данные портфельного актива не найдены"}

        return _shape_portfolio_asset_detail_rpc(result)
    except Exception as e:
        logger.error(f"Ошибка при получении информации о портфельном активе: {e}")
        return {"success": False, "error": str(e)}


async def get_asset_detail_for_user(asset_id: int, user_id: str):
    """Детальная страница актива по asset_id (и позициям пользователя), без обязательной привязки к portfolio_asset_id в URL."""
    try:
        if not user_id:
            return {"success": False, "error": "user_id обязателен для получения информации об активе"}

        result = await rpc_async("get_asset_detail_for_user", {
            "p_asset_id": asset_id,
            "p_user_id": user_id,
            "p_include_price_history": True,
            "p_price_history_limit": 100000
        })

        if not result:
            return {"success": False, "error": "Актив не найден или доступ запрещён"}

        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                return {"success": False, "error": "Некорректный ответ при получении деталей актива"}

        shaped = _shape_portfolio_asset_detail_rpc(result)
        if not shaped.get("success"):
            return shaped
        return shaped
    except Exception as e:
        logger.error(f"Ошибка при получении деталей актива по asset_id: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def move_asset_to_portfolio(portfolio_asset_id: int, target_portfolio_id: int, user_id: int = None):
    """Перемещает актив из одного портфеля в другой."""
    try:
        user_id_str = str(user_id) if user_id else None
        result = await rpc_async("move_portfolio_asset", {
            "p_portfolio_asset_id": portfolio_asset_id,
            "p_target_portfolio_id": target_portfolio_id,
            "p_user_id": user_id_str
        })

        if not result:
            return {"success": False, "error": "Ошибка при перемещении актива: пустой ответ"}

        if isinstance(result, str):
            import json as _json
            try:
                result = _json.loads(result)
            except _json.JSONDecodeError:
                return {"success": False, "error": f"Некорректный ответ: {result}"}

        return result

    except Exception as e:
        logger.error(f"Ошибка при перемещении актива: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def get_asset_in_all_portfolios(asset_id: int, user_id: str):
    """Получает информацию об активе во всех портфелях пользователя."""
    try:
        user_id_str = str(user_id) if user_id else None
        result = await rpc_async("get_asset_in_all_portfolios", {
            "p_asset_id": asset_id,
            "p_user_id": user_id_str
        })
        if result is None:
            return {"success": False, "error": "Не удалось получить данные"}
        return {"success": True, "portfolios": result if result else []}
    except Exception as e:
        logger.error(f"Ошибка при получении информации об активе в портфелях: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
