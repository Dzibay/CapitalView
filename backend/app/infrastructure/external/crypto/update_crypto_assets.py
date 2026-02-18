"""
Импорт и обновление криптовалютных активов.
Скрипт проверяет активы в базе и обновляет их если они с ошибками или если появились новые - добавляет.
"""
import asyncio
import aiohttp
from typing import Optional, Dict, List
from app.infrastructure.database.supabase_async import table_select_async, table_insert_async, table_update_async
from app.core.logging import get_logger

logger = get_logger(__name__)

# CoinGecko API endpoint
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
COINGECKO_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
MAX_RETRIES = 5


async def fetch_json(session: aiohttp.ClientSession, url: str, max_attempts: int = MAX_RETRIES) -> Optional[dict]:
    """
    Выполняет HTTP GET запрос и возвращает JSON.
    
    Args:
        session: HTTP сессия
        url: URL для запроса
        max_attempts: Максимальное количество попыток
        
    Returns:
        JSON данные или None
    """
    for attempt in range(max_attempts):
        try:
            async with session.get(url) as resp:
                if resp.status == 429:  # Rate limit
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                if resp.status != 200:
                    logger.warning(f"Ошибка при запросе {url}: статус {resp.status}")
                    return None
                return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError) as e:
            if attempt < max_attempts - 1:
                delay = min(2 ** attempt, 10)
                logger.warning(f"Ошибка соединения (попытка {attempt + 1}/{max_attempts}), повтор через {delay}с")
                await asyncio.sleep(delay)
                continue
            logger.error(f"Критическая ошибка при запросе {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при запросе {url}: {e}")
            return None
    return None


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
    
    data = await fetch_json(session, url)
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
        # Проверяем, нужно ли обновление
        # Обновляем если:
        # 1. Изменились данные (name, properties)
        # 2. Есть ошибки в properties (пустые, некорректные)
        existing_props = existing.get("properties") or {}
        if isinstance(existing_props, str):
            try:
                import json
                existing_props = json.loads(existing_props)
            except:
                existing_props = {}
        
        # Проверяем на ошибки: пустые properties или отсутствие source
        has_errors = (
            not existing_props or
            existing_props.get("source") != "coingecko" or
            not existing_props.get("coingecko_id") or
            existing.get("name") != asset["name"]
        )
        
        # Всегда обновляем для синхронизации данных
        # Важно: обновляем quote_asset_id даже если он уже установлен (может быть NULL)
        update_data = {
            "asset_type_id": asset["asset_type_id"],
            "name": asset["name"],
            "properties": asset["properties"],
            "quote_asset_id": asset.get("quote_asset_id"),  # Всегда обновляем quote_asset_id
        }
        await table_update_async("assets", update_data, {"id": existing["id"]})
        return "updated"
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
    
    crypto_list = await get_crypto_list(session, limit=250)
    
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
        else:
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
    connector = aiohttp.TCPConnector(
        limit=10,
        limit_per_host=5,
        ttl_dns_cache=300,
        force_close=False,
        enable_cleanup_closed=True,
    )
    
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=COINGECKO_TIMEOUT,
        headers={"User-Agent": "CapitalView/1.0"}
    ) as session:
        inserted, updated = await process_crypto_assets(session, existing_assets, crypto_type_id)
    
    print(f"\n🎯 Готово!")
    print(f"   ➕ Всего добавлено: {inserted}")
    print(f"   ♻️ Всего обновлено: {updated}")
    return inserted, updated


if __name__ == "__main__":
    asyncio.run(import_crypto_assets_async())
