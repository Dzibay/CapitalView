from app.infrastructure.database.database_service import rpc
from app.utils.date import normalize_date_to_string
from app.domain.services.portfolio_service import update_portfolios_with_asset
from app.core.logging import get_logger
from app.infrastructure.database.repositories.asset_repository import AssetRepository

logger = get_logger(__name__)

_asset_repository = AssetRepository()


def add_asset_price(data):
    asset_id = data.get('asset_id')
    price = data.get('price', 0)
    date = data.get('date')

    if not asset_id:
        return {"success": False, "error": "asset_id обязателен"}
    if not price or price <= 0:
        return {"success": False, "error": "price должен быть больше 0"}
    if not date:
        return {"success": False, "error": "date обязателен"}

    try:
        asset = _asset_repository.get_by_id_sync(asset_id)
        if not asset:
            return {"success": False, "error": "Актив не найден"}

        if asset.get("user_id") is None:
            return {"success": False, "error": "Невозможно изменить цену системного актива"}
    except Exception as e:
        logger.error(f"Ошибка при проверке актива {asset_id}: {e}")
        return {"success": False, "error": "Ошибка при проверке актива"}

    date_str = normalize_date_to_string(date, include_time=True) or ""

    price_data_list = [{
        "asset_id": asset_id,
        "price": float(price),
        "trade_date": date_str
    }]

    try:
        result = rpc("upsert_asset_prices", {"p_prices": price_data_list})

        if result is False:
            return {"success": False, "error": "Ошибка при добавлении цены"}

        try:
            update_result = rpc('update_asset_latest_prices_batch', {'p_asset_ids': [asset_id]})
            if update_result is False:
                logger.warning(f"RPC функция вернула False для актива {asset_id}")
        except Exception as rpc_error:
            logger.warning(f"Ошибка при обновлении цены актива {asset_id}: {rpc_error}")

        update_portfolios_with_asset(asset_id, date_str)

        return {"success": True, "message": "Цена успешно добавлена/обновлена"}
    except Exception as e:
        logger.error(f"Ошибка при добавлении цены актива: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def add_asset_prices_batch(asset_id: int, prices: list):
    if not asset_id:
        return {"success": False, "error": "asset_id обязателен"}
    if not prices or len(prices) == 0:
        return {"success": False, "error": "prices не может быть пустым"}

    try:
        asset = _asset_repository.get_by_id_sync(asset_id)
        if not asset:
            return {"success": False, "error": "Актив не найден"}

        if asset.get("user_id") is None:
            return {"success": False, "error": "Невозможно изменить цену системного актива"}
    except Exception as e:
        logger.error(f"Ошибка при проверке актива {asset_id}: {e}")
        return {"success": False, "error": "Ошибка при проверке актива"}

    price_data_list = []
    for price_item in prices:
        price = price_item.get('price', 0)
        date = price_item.get('date')

        if not price or price <= 0:
            continue

        if not date:
            continue

        if hasattr(date, 'isoformat'):
            date_str = date.isoformat()
        elif isinstance(date, str):
            date_str = date
        else:
            date_str = str(date)

        price_data_list.append({
            "asset_id": asset_id,
            "price": float(price),
            "trade_date": date_str
        })

    if not price_data_list:
        return {"success": False, "error": "Нет валидных цен для добавления"}

    try:
        result = rpc("upsert_asset_prices", {"p_prices": price_data_list})

        if result is False:
            return {"success": False, "error": "Ошибка при массовом добавлении цен"}

        try:
            update_result = rpc('update_asset_latest_prices_batch', {'p_asset_ids': [asset_id]})
            if update_result is False:
                logger.warning(f"RPC функция вернула False для актива {asset_id}")
        except Exception as rpc_error:
            logger.warning(f"Ошибка при обновлении цены актива {asset_id}: {rpc_error}")

        min_date = min([p.get('trade_date', '') for p in price_data_list], default=None)
        if min_date:
            update_portfolios_with_asset(asset_id, min_date)

        return {
            "success": True,
            "message": f"Успешно добавлено {len(price_data_list)} цен",
            "count": len(price_data_list)
        }
    except Exception as e:
        logger.error(f"Ошибка при массовом добавлении цен актива: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def get_asset_price_history(asset_id: int, start_date: str = None, end_date: str = None, limit: int = 1000):
    try:
        from datetime import datetime, date as date_type

        query = _asset_repository.get_price_history(asset_id, start_date=start_date, end_date=end_date, limit=limit)

        if start_date or end_date:
            filtered = []
            for row in query:
                trade_date = row.get("trade_date")

                if isinstance(trade_date, str):
                    try:
                        trade_date = datetime.fromisoformat(trade_date.replace("Z", "+00:00"))
                    except:
                        try:
                            trade_date = datetime.fromisoformat(trade_date)
                        except:
                            continue
                elif isinstance(trade_date, date_type):
                    trade_date = datetime.combine(trade_date, datetime.min.time())

                trade_date_normalized = trade_date.replace(hour=0, minute=0, second=0, microsecond=0)

                if start_date:
                    try:
                        start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                    except:
                        start = datetime.fromisoformat(start_date)
                    start_normalized = start.replace(hour=0, minute=0, second=0, microsecond=0)
                    if trade_date_normalized < start_normalized:
                        continue

                if end_date:
                    try:
                        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    except:
                        end = datetime.fromisoformat(end_date)
                    end_normalized = end.replace(hour=23, minute=59, second=59, microsecond=999999)
                    if trade_date_normalized > end_normalized:
                        continue

                filtered.append(row)
            query = filtered

        return {"success": True, "prices": query, "count": len(query)}
    except Exception as e:
        return {"success": False, "error": str(e)}
