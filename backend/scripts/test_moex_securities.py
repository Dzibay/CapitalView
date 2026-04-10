"""
Тестовый скрипт для сравнения активов из MOEX API с базой данных.

Использование:
    python scripts/test_moex_securities.py
"""
import asyncio
import sys
from pathlib import Path
from collections import defaultdict

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.external.moex.client import (
    MOEX_HTTP_PER_HOST_LIMIT,
    MOEX_HTTP_TOTAL_LIMIT,
    create_moex_session,
    fetch_json,
)
from app.infrastructure.external.moex.urls import MOEX_SECURITIES_JSON
from app.infrastructure.database.postgres_async import table_select_async
from app.utils.async_runner import run_async


async def fetch_all_securities(session, market: str):
    """
    Получает все ценные бумаги из MOEX API с учетом пагинации.
    
    Args:
        session: HTTP сессия
        market: Рынок ("shares" или "bonds")
        
    Returns:
        Список всех тикеров (secid)
    """
    base_url = MOEX_SECURITIES_JSON
    params = {"engine": "stock", "market": market}
    
    all_tickers = set()
    start = 0
    limit = 100  # MOEX обычно возвращает по 100 записей на страницу
    
    print(f"   📥 Загрузка {market}...")
    
    while True:
        params_with_start = {**params, "start": start}
        url = f"{base_url}?{'&'.join(f'{k}={v}' for k, v in params_with_start.items())}"
        
        data = await fetch_json(session, url, max_attempts=3)
        
        if not data or "securities" not in data:
            break
        
        cols = data["securities"].get("columns", [])
        rows = data["securities"].get("data", [])
        
        if not cols or not rows:
            break
        
        # Находим индекс колонки secid (в нижнем регистре)
        try:
            i_secid = cols.index("secid")
        except ValueError:
            # Пробуем в верхнем регистре
            try:
                i_secid = cols.index("SECID")
            except ValueError:
                print(f"   ⚠️ Колонка secid не найдена в {market}")
                break
        
        # Собираем тикеры
        page_tickers = set()
        for row in rows:
            ticker = row[i_secid] if i_secid is not None else None
            if ticker:
                ticker_upper = ticker.upper().strip()
                if ticker_upper:
                    page_tickers.add(ticker_upper)
                    all_tickers.add(ticker_upper)
        
        print(f"      Страница {start // limit + 1}: получено {len(page_tickers)} тикеров (всего: {len(all_tickers)})")
        
        # Если получили меньше записей чем limit, значит это последняя страница
        if len(rows) < limit:
            break
        
        # Проверяем, есть ли еще данные (MOEX может вернуть пустой массив если данных больше нет)
        if len(page_tickers) == 0:
            break
        
        start += limit
        
        # Небольшая задержка между запросами
        await asyncio.sleep(0.1)
    
    return all_tickers


async def get_db_assets():
    """
    Получает все MOEX активы из базы данных.
    
    Returns:
        Словарь {ticker: asset_data} для активов с source="moex"
    """
    print("   📥 Загрузка активов из базы данных...")
    
    # Получаем все активы с типом акция, облигация, фонд, фьючерс
    moex_asset_types = [1, 2, 3, 4, 5]  # как в init.sql / moex_price_worker
    
    raw_assets = await table_select_async(
        "assets",
        "id, ticker, asset_type_id, properties",
        in_filters={"asset_type_id": moex_asset_types}
    )
    
    db_assets = {}
    for asset in raw_assets:
        ticker = asset.get("ticker")
        if not ticker:
            continue
        
        # Проверяем source = "moex"
        props = asset.get("properties") or {}
        if isinstance(props, str):
            try:
                import json
                props = json.loads(props)
            except:
                props = {}
        
        if props.get("source") == "moex" and asset.get("user_id") is None:
            ticker_upper = ticker.upper().strip()
            if ticker_upper:
                db_assets[ticker_upper] = {
                    "id": asset.get("id"),
                    "ticker": ticker_upper,
                    "asset_type_id": asset.get("asset_type_id"),
                }
    
    print(f"      Получено {len(db_assets)} активов из БД")
    return db_assets


async def compare_securities():
    """Сравнивает активы из MOEX API с базой данных."""
    
    print("\n" + "="*80)
    print("СРАВНЕНИЕ АКТИВОВ MOEX API С БАЗОЙ ДАННЫХ")
    print("="*80)
    
    async with create_moex_session(
        limit=MOEX_HTTP_TOTAL_LIMIT,
        limit_per_host=MOEX_HTTP_PER_HOST_LIMIT,
    ) as session:
        # Получаем все тикеры из MOEX API
        print("\n📊 Получение данных из MOEX API:")
        moex_shares = await fetch_all_securities(session, "shares")
        moex_bonds = await fetch_all_securities(session, "bonds")
        moex_all = moex_shares | moex_bonds
        
        print(f"\n   ✅ Всего получено из MOEX API:")
        print(f"      Акции: {len(moex_shares)}")
        print(f"      Облигации: {len(moex_bonds)}")
        print(f"      Всего: {len(moex_all)}")
    
    # Получаем активы из базы данных
    print("\n📊 Получение данных из базы данных:")
    db_assets = await get_db_assets()
    
    # Группируем активы из БД по типу
    db_shares = {t: a for t, a in db_assets.items() if a["asset_type_id"] == 1}
    db_funds = {t: a for t, a in db_assets.items() if a["asset_type_id"] == 3}
    db_bonds = {t: a for t, a in db_assets.items() if a["asset_type_id"] == 2}
    db_futures = {t: a for t, a in db_assets.items() if a["asset_type_id"] == 5}
    
    # Объединяем акции и фонды для сравнения с MOEX shares
    db_options = {t: a for t, a in db_assets.items() if a["asset_type_id"] == 4}
    db_shares_all = db_shares | db_funds | db_futures | db_options
    
    print(f"\n   ✅ Всего в базе данных:")
    print(f"      Акции: {len(db_shares)}")
    print(f"      Фонды: {len(db_funds)}")
    print(f"      Фьючерсы: {len(db_futures)}")
    print(f"      Облигации: {len(db_bonds)}")
    print(f"      Всего (акции+фонды+фьючерсы): {len(db_shares_all)}")
    print(f"      Всего (облигации): {len(db_bonds)}")
    
    # Сравнение акций
    print("\n" + "="*80)
    print("СРАВНЕНИЕ АКЦИЙ (shares)")
    print("="*80)
    
    only_in_moex_shares = moex_shares - set(db_shares_all.keys())
    only_in_db_shares = set(db_shares_all.keys()) - moex_shares
    in_both_shares = moex_shares & set(db_shares_all.keys())
    
    print(f"\n📈 Статистика:")
    print(f"   В MOEX API: {len(moex_shares)}")
    print(f"   В базе данных: {len(db_shares_all)}")
    print(f"   В обоих источниках: {len(in_both_shares)}")
    print(f"   Только в MOEX API: {len(only_in_moex_shares)}")
    print(f"   Только в базе данных: {len(only_in_db_shares)}")
    
    if only_in_moex_shares:
        print(f"\n🔍 Тикеры только в MOEX API (первые 20):")
        for ticker in sorted(list(only_in_moex_shares))[:20]:
            print(f"   {ticker}")
        if len(only_in_moex_shares) > 20:
            print(f"   ... и еще {len(only_in_moex_shares) - 20}")
    
    if only_in_db_shares:
        print(f"\n🔍 Тикеры только в базе данных (первые 20):")
        for ticker in sorted(list(only_in_db_shares))[:20]:
            asset = db_shares_all[ticker]
            asset_type = {1: "Акция", 3: "Фонд", 4: "Опцион", 5: "Фьючерс"}.get(
                asset["asset_type_id"], "Неизвестно"
            )
            print(f"   {ticker:<15} ({asset_type})")
        if len(only_in_db_shares) > 20:
            print(f"   ... и еще {len(only_in_db_shares) - 20}")
    
    # Сравнение облигаций
    print("\n" + "="*80)
    print("СРАВНЕНИЕ ОБЛИГАЦИЙ (bonds)")
    print("="*80)
    
    only_in_moex_bonds = moex_bonds - set(db_bonds.keys())
    only_in_db_bonds = set(db_bonds.keys()) - moex_bonds
    in_both_bonds = moex_bonds & set(db_bonds.keys())
    
    print(f"\n📈 Статистика:")
    print(f"   В MOEX API: {len(moex_bonds)}")
    print(f"   В базе данных: {len(db_bonds)}")
    print(f"   В обоих источниках: {len(in_both_bonds)}")
    print(f"   Только в MOEX API: {len(only_in_moex_bonds)}")
    print(f"   Только в базе данных: {len(only_in_db_bonds)}")
    
    if only_in_moex_bonds:
        print(f"\n🔍 Тикеры только в MOEX API (первые 20):")
        for ticker in sorted(list(only_in_moex_bonds))[:20]:
            print(f"   {ticker}")
        if len(only_in_moex_bonds) > 20:
            print(f"   ... и еще {len(only_in_moex_bonds) - 20}")
    
    if only_in_db_bonds:
        print(f"\n🔍 Тикеры только в базе данных (первые 20):")
        for ticker in sorted(list(only_in_db_bonds))[:20]:
            print(f"   {ticker}")
        if len(only_in_db_bonds) > 20:
            print(f"   ... и еще {len(only_in_db_bonds) - 20}")
    
    # Общая статистика
    print("\n" + "="*80)
    print("ОБЩАЯ СТАТИСТИКА")
    print("="*80)
    
    only_in_moex_all = only_in_moex_shares | only_in_moex_bonds
    only_in_db_all = only_in_db_shares | only_in_db_bonds
    in_both_all = in_both_shares | in_both_bonds
    
    print(f"\n📊 Итого:")
    print(f"   В MOEX API всего: {len(moex_all)}")
    print(f"   В базе данных всего: {len(db_assets)}")
    print(f"   В обоих источниках: {len(in_both_all)}")
    print(f"   Только в MOEX API: {len(only_in_moex_all)}")
    print(f"   Только в базе данных: {len(only_in_db_all)}")
    
    # Процент покрытия
    if moex_all:
        coverage = (len(in_both_all) / len(moex_all)) * 100
        print(f"\n📈 Покрытие базы данных:")
        print(f"   {coverage:.2f}% активов из MOEX API есть в базе данных")
    
    if db_assets:
        db_coverage = (len(in_both_all) / len(db_assets)) * 100
        print(f"   {db_coverage:.2f}% активов из базы данных есть в MOEX API")


async def main():
    """Основная функция."""
    try:
        await compare_securities()
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_async(main())
