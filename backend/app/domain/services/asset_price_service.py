from app.infrastructure.database.database_service import rpc_async
from app.infrastructure.database.postgres_async import get_connection_pool
from app.utils.date import normalize_date_to_string
from app.domain.services.portfolio_service import update_portfolios_with_asset
from app.core.logging import get_logger
from app.infrastructure.database.repositories.asset_repository import AssetRepository

logger = get_logger(__name__)

_asset_repository = AssetRepository()


async def add_asset_price(data):
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
        asset = await _asset_repository.get_by_id(asset_id)
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
        result = await rpc_async("upsert_asset_prices", {"p_prices": price_data_list})
        if result is False:
            return {"success": False, "error": "Ошибка при добавлении цены"}

        try:
            update_result = await rpc_async('update_asset_latest_prices_batch', {'p_asset_ids': [asset_id]})
            if update_result is False:
                logger.warning(f"RPC функция вернула False для актива {asset_id}")
        except Exception as rpc_error:
            logger.warning(f"Ошибка при обновлении цены актива {asset_id}: {rpc_error}")

        await update_portfolios_with_asset(asset_id, date_str)

        return {"success": True, "message": "Цена успешно добавлена/обновлена"}
    except Exception as e:
        logger.error(f"Ошибка при добавлении цены актива: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def add_asset_prices_batch(asset_id: int, prices: list):
    if not asset_id:
        return {"success": False, "error": "asset_id обязателен"}
    if not prices or len(prices) == 0:
        return {"success": False, "error": "prices не может быть пустым"}

    try:
        asset = await _asset_repository.get_by_id(asset_id)
        if not asset:
            return {"success": False, "error": "Актив не найден"}
        if asset.get("user_id") is None:
            return {"success": False, "error": "Невозможно изменить цену системного актива"}
    except Exception as e:
        logger.error(f"Ошибка при проверке актива {asset_id}: {e}")
        return {"success": False, "error": "Ошибка при проверке актива"}

    price_data_list = []
    normalized_dates = []
    for price_item in prices:
        price = price_item.get('price', 0)
        date = price_item.get('date')
        if not price or price <= 0:
            continue
        if not date:
            continue
        date_str = normalize_date_to_string(date, include_time=False)
        if not date_str:
            continue
        price_data_list.append({
            "asset_id": asset_id,
            "price": float(price),
            "trade_date": date_str
        })
        normalized_dates.append(date_str)

    if not price_data_list:
        return {"success": False, "error": "Нет валидных цен для добавления"}

    try:
        min_date = min(normalized_dates)
        max_date = max(normalized_dates)

        pool = await get_connection_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM asset_prices
                WHERE asset_id = $1
                  AND trade_date BETWEEN $2::date AND $3::date
                """,
                asset_id, min_date, max_date,
            )

        result = await rpc_async("upsert_asset_prices", {"p_prices": price_data_list})
        if result is False:
            return {"success": False, "error": "Ошибка при массовом добавлении цен"}

        try:
            update_result = await rpc_async('update_asset_latest_prices_batch', {'p_asset_ids': [asset_id]})
            if update_result is False:
                logger.warning(f"RPC функция вернула False для актива {asset_id}")
        except Exception as rpc_error:
            logger.warning(f"Ошибка при обновлении цены актива {asset_id}: {rpc_error}")

        min_trade_date = min([p.get('trade_date', '') for p in price_data_list], default=None)
        if min_trade_date:
            await update_portfolios_with_asset(asset_id, min_trade_date)

        return {
            "success": True,
            "message": f"Успешно добавлено {len(price_data_list)} цен",
            "count": len(price_data_list)
        }
    except Exception as e:
        logger.error(f"Ошибка при массовом добавлении цен актива: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def get_asset_price_history(asset_id: int, start_date: str = None, end_date: str = None, limit: int = 100000):
    try:
        from datetime import datetime, date as date_type

        currency_ticker = "RUB"
        asset = await _asset_repository.get_by_id(asset_id)
        if asset:
            quote_id = asset.get("quote_asset_id") or 1
            quote_asset = await _asset_repository.get_by_id(quote_id)
            if quote_asset and quote_asset.get("ticker"):
                currency_ticker = quote_asset.get("ticker", "RUB")

        query = await _asset_repository.get_price_history(asset_id, start_date=start_date, end_date=end_date, limit=limit)

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
                    if trade_date_normalized < start.replace(hour=0, minute=0, second=0, microsecond=0):
                        continue

                if end_date:
                    try:
                        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    except:
                        end = datetime.fromisoformat(end_date)
                    if trade_date_normalized > end.replace(hour=23, minute=59, second=59, microsecond=999999):
                        continue

                filtered.append(row)
            query = filtered

        return {"success": True, "prices": query, "count": len(query), "currency_ticker": currency_ticker}
    except Exception as e:
        return {"success": False, "error": str(e)}
