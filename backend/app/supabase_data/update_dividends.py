import asyncio
import aiohttp
import random
from bs4 import BeautifulSoup
from datetime import datetime, date
from app.services.supabase_service import table_select, table_insert

# URL страниц
SMARTLAB_INDEX_URL = "https://smart-lab.ru/dividends/index/order_by_yield/desc/"
# Базовый URL для истории с плейсхолдером для номера страницы
SMARTLAB_HISTORY_BASE_URL = "https://smart-lab.ru/dividends/history/order_by_cut_off_date/desc/page{}/"

async def fetch_html(session, url):
    """Загружает HTML страницы"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        # Добавляем случайную задержку перед запросом, чтобы не нагружать сервер
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                return await resp.text()
            elif resp.status == 404:
                print(f"⚠️ Страница не найдена (404): {url}")
                return None
            else:
                print(f"⚠️ SmartLab ({url}) вернул статус {resp.status}")
    except Exception as e:
        print(f"❌ Ошибка сети при запросе {url}: {e}")
    return None

def parse_date(date_str):
    """Преобразует дату из '25.12.2025' в объект date"""
    if not date_str or date_str == '-':
        return None
    try:
        return datetime.strptime(date_str.strip(), "%d.%m.%Y").date()
    except (ValueError, AttributeError):
        return None

def normalize_value(val_str):
    """Преобразует строку '9,17' или '<strong>902</strong>' в float"""
    if not val_str:
        return 0.0
    # Убираем пробелы, теги и заменяем запятую на точку
    clean_val = val_str.replace(',', '.').replace(' ', '').strip()
    try:
        return float("".join(c for c in clean_val if c.isdigit() or c == '.'))
    except ValueError:
        return 0.0

def parse_smartlab_row(row, mode="index"):
    """
    Парсит одну строку таблицы HTML.
    mode="index" — таблица будущих дивидендов
    mode="history" — таблица истории
    """
    cols = row.find_all("td")
    
    # В таблице истории может быть 10 или 11 колонок
    if len(cols) < 5:
        return None

    try:
        # Тикер обычно во второй колонке [1], но иногда внутри ссылки
        ticker_col = cols[1]
        ticker = ticker_col.get_text(strip=True)
        
        if not ticker: 
            return None

        last_buy_date = None
        record_date = None
        payment_date = None
        value = 0.0
        dividend_yield = None

        value = normalize_value(cols[3].get_text(strip=True))
        dividend_yield = normalize_value(cols[4].get_text(strip=True))
        last_buy_date = parse_date(cols[6].get_text(strip=True))
        record_date = parse_date(cols[7].get_text(strip=True))
        payment_date = parse_date(cols[8].get_text(strip=True))

        # Общая проверка валидности: должна быть хоть одна дата
        if not record_date and not payment_date and not last_buy_date:
            return None

        return {
            "ticker": ticker.upper(),
            'last_buy_date': last_buy_date,
            "record_date": record_date,
            "payment_date": payment_date,
            "value": value,
            'dividend_yield': dividend_yield
        }
    except Exception as e:
        # print(f"Ошибка парсинга строки ({mode}): {e}")
        return None

async def process_page(session, url, mode, ticker_map):
    """Обрабатывает одну страницу"""
    # print(f"⏳ Скачиваем {url}...")
    html = await fetch_html(session, url)
    if not html:
        return None # Возвращаем None при ошибке загрузки

    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_="trades-table")
    
    if not table:
        # Если таблицы нет, возможно это конец пагинации
        return []

    tbody = table.find("tbody")
    if not tbody:
        return []

    parsed_items = []
    rows = tbody.find_all("tr")
    
    for row in rows:
        item = parse_smartlab_row(row, mode=mode)
        
        # Проверяем, есть ли такой тикер у нас в базе
        if item and item["ticker"] in ticker_map:
            item["asset_id"] = ticker_map[item["ticker"]]
            parsed_items.append(item)
            
    return parsed_items

async def update_forecasts():
    # 1. Получаем ID активов
    assets = await asyncio.to_thread(table_select, "assets")
    ticker_map = {a["ticker"].upper(): a["id"] for a in assets if a.get("ticker")}
    
    # 2. Получаем существующие выплаты (чтобы не дублировать)
    existing_payouts = await asyncio.to_thread(table_select, "asset_payouts")
    
    # Ключ уникальности: (asset_id, record_date, value)
    existing_keys = set()
    for p in existing_payouts:
        # Используем дату отсечки как основной идентификатор, но если ее нет - payment_date
        date_key = str(p.get("record_date") or p.get("payment_date"))
        val = float(p["value"] or 0)
        existing_keys.add((p["asset_id"], date_key, val))

    all_items = []

    async with aiohttp.ClientSession() as session:
        # 3. Скачиваем БУДУЩИЕ дивиденды (одна страница)
        print("📥 Обработка будущих дивидендов...")
        future_items = await process_page(session, SMARTLAB_INDEX_URL, "index", ticker_map)
        if future_items:
            all_items.extend(future_items)

        # 4. Скачиваем ИСТОРИЮ (много страниц)
        print("📥 Обработка истории дивидендов...")
        page_num = 1
        max_errors = 3 # Защита от бесконечного цикла
        error_count = 0

        while True:
            url = SMARTLAB_HISTORY_BASE_URL.format(page_num)
            print(f"   Страница {page_num}...", end="\r")
            
            history_items = await process_page(session, url, "history", ticker_map)
            
            # Если вернулся None (ошибка 404 или сети) или пустой список - выходим
            if history_items is None:
                error_count += 1
                if error_count >= max_errors:
                    break
            elif len(history_items) == 0:
                # Пустая таблица - значит страницы кончились
                break
            else:
                all_items.extend(history_items)
                error_count = 0 # Сброс счетчика ошибок при успехе
            
            page_num += 1
            # Ограничитель на случай сбоя, чтобы не парсить вечно (например, 50 страниц)
            if page_num > 60: 
                break

    print(f"\n📊 Всего найдено записей для обработки: {len(all_items)}")

    # 5. Сбор данных для вставки
    payouts_to_insert = []
    
    for item in all_items:
        # Приоритет даты для ключа уникальности: Record -> Payment -> Buy
        check_date = item["record_date"] or item["payment_date"] or item["last_buy_date"]
        
        if not check_date:
            continue

        key = (item["asset_id"], check_date.isoformat(), float(item["value"]))

        if key in existing_keys:
            continue
        
        existing_keys.add(key)

        new_payout = {
            "asset_id": item["asset_id"],
            "value": item["value"],
            'dividend_yield': item['dividend_yield'],
            "last_buy_date": item["last_buy_date"].isoformat() if item["last_buy_date"] else None,
            "record_date": item["record_date"].isoformat() if item["record_date"] else None,
            "payment_date": item["payment_date"].isoformat() if item["payment_date"] else None,
            "type": "dividend"
        }
        
        payouts_to_insert.append(new_payout)

    # 6. Пакетная вставка (Batch Insert)
    added_count = 0
    BATCH_SIZE = 1000  # Размер пачки для вставки

    if payouts_to_insert:
        print(f"📦 Начинаем пакетную вставку {len(payouts_to_insert)} записей...")
        
        # Разбиваем на пакеты
        for i in range(0, len(payouts_to_insert), BATCH_SIZE):
            batch = payouts_to_insert[i : i + BATCH_SIZE]
            try:
                # table_insert обычно поддерживает вставку списка словарей
                await asyncio.to_thread(table_insert, "asset_payouts", batch)
                print(f"   ✅ Вставлен пакет {i // BATCH_SIZE + 1} ({len(batch)} записей)")
                added_count += len(batch)
            except Exception as e:
                print(f"⚠️ Ошибка вставки пакета {i // BATCH_SIZE + 1}: {e}")
    else:
        print("📭 Новых записей для вставки не найдено.")

    print(f"🏁 Готово. Всего добавлено новых записей: {added_count}")

if __name__ == "__main__":
    asyncio.run(update_forecasts())