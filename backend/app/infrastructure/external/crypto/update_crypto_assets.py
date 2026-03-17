"""
Импорт и обновление криптовалютных активов.
Скрипт проверяет активы в базе и обновляет их если они с ошибками или если появились новые - добавляет.
"""
import aiohttp
from typing import Dict, List
from app.infrastructure.database.postgres_async import table_select_async, table_insert_async, table_update_async
from app.infrastructure.external.common.client import create_http_session, fetch_json
from app.infrastructure.external.crypto.price_service import COINGECKO_API_URL, COINGECKO_RATE_LIMIT_DELAY
from app.infrastructure.external.moex.utils import parse_json_properties
from app.core.logging import get_logger

logger = get_logger(__name__)


async def get_crypto_list(session: aiohttp.ClientSession, limit: int = 250) -> List[Dict]:
    """
    Получает список криптовалют с CoinGecko API.
    
    Args:
        session: HTTP сессия
        limit: Максимальное количество криптовалют (по умолчанию 250)
        
    Returns:
        Список словарей с данными криптовалют
    """
    # Получаем топ криптовалют по рыночной капитализации
    # Используем только markets endpoint для оптимизации (без дополнительных запросов)
    url = f"{COINGECKO_API_URL}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page={limit}&page=1&sparkline=false"
    
    data = await fetch_json(session, url, rate_limit_delay=COINGECKO_RATE_LIMIT_DELAY)
    if not data:
        logger.error("Не удалось получить список криптовалют")
        return []
    
    crypto_list = []
    for coin in data:
        coin_id = coin.get("id")
        symbol = coin.get("symbol", "").upper()
        if not coin_id or not symbol:
            continue
        
        crypto_list.append({
            "id": coin_id,
            "symbol": symbol,
            "name": coin.get("name", symbol),
            "market_cap_rank": coin.get("market_cap_rank"),
        })
    
    return crypto_list


async def upsert_asset(asset: Dict, existing_assets: Dict) -> str:
    """
    Обновляет существующий актив или добавляет новый.
    Проверяет активы с ошибками (пустые properties, некорректные данные) и обновляет их.
    
    Args:
        asset: Словарь с данными актива
        existing_assets: Словарь существующих активов {ticker: asset_data}
        
    Returns:
        "updated" или "inserted"
    """
    ticker = asset["ticker"].upper()
    existing = existing_assets.get(ticker)
    
    if existing:
        # Парсим properties
        existing_props = parse_json_properties(existing.get("properties"))
        new_props = parse_json_properties(asset.get("properties"))
        
        # Проверяем, нужно ли обновление
        needs_update = False
        update_data = {}
        
        if existing.get("asset_type_id") != asset["asset_type_id"]:
            needs_update = True
            update_data["asset_type_id"] = asset["asset_type_id"]
        
        if existing.get("name") != asset["name"]:
            needs_update = True
            update_data["name"] = asset["name"]
        
        if existing_props != new_props:
            needs_update = True
            update_data["properties"] = asset["properties"]
        
        if existing.get("quote_asset_id") != asset.get("quote_asset_id"):
            needs_update = True
            update_data["quote_asset_id"] = asset.get("quote_asset_id")
        
        if needs_update:
            await table_update_async("assets", update_data, {"id": existing["id"]})
            return "updated"
        
        return "no_change"
    else:
        await table_insert_async("assets", asset)
        return "inserted"


async def process_crypto_assets(session: aiohttp.ClientSession, existing_assets: Dict, asset_type_id: int) -> tuple:
    """
    Обрабатывает список криптовалют и обновляет/добавляет их в базу данных.
    
    Args:
        session: HTTP сессия
        existing_assets: Словарь существующих активов {ticker: asset_data}
        asset_type_id: ID типа актива для криптовалют
        
    Returns:
        Кортеж (количество добавленных, количество обновленных)
    """
    print(f"\n🔹 Обработка криптовалют...")
    
    # Находим ID актива USD один раз для всех криптовалют
    usd_asset = await table_select_async(
        "assets",
        "id",
        filters={"ticker": "USD", "user_id": None}
    )
    quote_asset_id = usd_asset[0]["id"] if usd_asset and len(usd_asset) > 0 else None
    
    if not quote_asset_id:
        logger.warning("⚠️ Актив USD не найден в базе данных. quote_asset_id будет NULL для всех криптовалют")
    else:
        print(f"   💵 Найден актив USD с ID: {quote_asset_id}")
    
    crypto_list = await get_crypto_list(session, limit=10)
    
    if not crypto_list:
        print(f"   ⚠️ Нет данных о криптовалютах")
        return 0, 0
    
    inserted = 0
    updated = 0
    
    for crypto in crypto_list:
        ticker = crypto.get("symbol", "").upper()
        if not ticker:
            continue
        
        name = crypto.get("name", ticker)
        
        # Формируем properties (только необходимые метаданные, без ценовых данных)
        props = {
            "source": "coingecko",
            "coingecko_id": crypto.get("id"),
            "market_cap_rank": crypto.get("market_cap_rank"),
        }
        
        asset = {
            "asset_type_id": asset_type_id,
            "user_id": None,
            "name": name,
            "ticker": ticker,
            "properties": props,
            "quote_asset_id": quote_asset_id,
        }
        
        result = await upsert_asset(asset, existing_assets)
        if result == "inserted":
            inserted += 1
        elif result == "updated":
            updated += 1
    
    print(f"   ➕ Добавлено: {inserted}")
    print(f"   ♻️ Обновлено: {updated}")
    return inserted, updated


async def import_crypto_assets_async():
    """
    Импортирует и обновляет криптовалютные активы.
    Проверяет активы в базе и обновляет их если они с ошибками или если появились новые - добавляет.
    """
    print("📥 Асинхронный импорт и обновление криптовалютных активов...\n")

    crypto_type_id = 6
    
    # Получаем существующие активы из базы с фильтром по asset_type_id
    # Это эффективнее, чем запрашивать все активы и фильтровать в коде
    raw = await table_select_async(
        "assets",
        "id, ticker, properties, asset_type_id, name, user_id",
        filters={"asset_type_id": crypto_type_id}
    )
    
    existing_assets = {}
    
    # Обрабатываем активы с нужным asset_type_id и user_id IS NULL (системные активы)
    for a in raw:
        if not a.get("ticker"):
            continue
        # Пропускаем пользовательские активы
        if a.get("user_id") is not None:
            continue
        
        ticker = a["ticker"].upper()
        existing_assets[ticker] = a
    
    # Создаем HTTP сессию
    async with create_http_session(limit=10, limit_per_host=5) as session:
        inserted, updated = await process_crypto_assets(session, existing_assets, crypto_type_id)
    
    print(f"\n🎯 Готово!")
    print(f"   ➕ Всего добавлено: {inserted}")
    print(f"   ♻️ Всего обновлено: {updated}")
    return inserted, updated


if __name__ == "__main__":
    from app.utils.async_runner import run_async
    run_async(import_crypto_assets_async())
