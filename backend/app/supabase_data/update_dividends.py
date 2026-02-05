import asyncio
import aiohttp
import random
from bs4 import BeautifulSoup
from datetime import datetime, date
from app.services.supabase_async import table_select_async, table_insert_async

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
    assets = await table_select_async("assets")
    ticker_map = {a["ticker"].upper(): a["id"] for a in assets if a.get("ticker")}
    
    # 2. Получаем существующие выплаты типа "dividend" (оптимизация: только нужные поля)
    # Загружаем только записи с типом "dividend" для экономии памяти
    existing_payouts = await table_select_async(
        "asset_payouts", 
        select="asset_id,record_date,value,type",
        filters={"type": "dividend"}
    )
    
    # Ключ уникальности соответствует БД: (asset_id, record_date, value, type)
    # ВАЖНО: используем только record_date, так как в БД уникальность по record_date
    existing_keys = set()
    for p in existing_payouts:
        record_date = p.get("record_date")
        # Пропускаем записи без record_date, так как они не могут быть частью уникального ключа
        if not record_date:
            continue
        # Нормализуем значение для сравнения (округление до 2 знаков)
        val = round(float(p.get("value") or 0), 2)
        p_type = p.get("type") or "dividend"
        # Используем ISO формат даты для ключа (YYYY-MM-DD)
        existing_keys.add((p["asset_id"], record_date.isoformat() if isinstance(record_date, date) else str(record_date), val, p_type))

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
        # ВАЖНО: для уникальности используем только record_date (как в БД)
        # Если record_date нет, пропускаем запись (не можем создать уникальный ключ)
        record_date = item.get("record_date")
        if not record_date:
            continue

        # Нормализуем значение для сравнения
        val = round(float(item.get("value") or 0), 2)
        p_type = "dividend"
        
        # Ключ должен соответствовать уникальному ограничению БД
        key = (item["asset_id"], record_date.isoformat(), val, p_type)

        if key in existing_keys:
            continue
        
        # Добавляем в множество для предотвращения дубликатов в текущем запуске
        existing_keys.add(key)

        new_payout = {
            "asset_id": item["asset_id"],
            "value": item["value"],
            'dividend_yield': item.get('dividend_yield'),
            "last_buy_date": item["last_buy_date"].isoformat() if item.get("last_buy_date") else None,
            "record_date": record_date.isoformat(),
            "payment_date": item["payment_date"].isoformat() if item.get("payment_date") else None,
            "type": p_type
        }
        
        payouts_to_insert.append(new_payout)

    # 6. Пакетная вставка с обработкой дубликатов
    added_count = 0
    skipped_count = 0
    BATCH_SIZE = 1000  # Размер пачки для вставки

    if payouts_to_insert:
        print(f"📦 Начинаем пакетную вставку {len(payouts_to_insert)} записей...")
        
        # Разбиваем на пакеты
        for i in range(0, len(payouts_to_insert), BATCH_SIZE):
            batch = payouts_to_insert[i : i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            
            try:
                # Пытаемся вставить пакет
                await table_insert_async("asset_payouts", batch)
                print(f"   ✅ Вставлен пакет {batch_num} ({len(batch)} записей)")
                added_count += len(batch)
            except Exception as e:
                # Если ошибка дублирования, пробуем вставлять по одной записи
                error_str = str(e)
                if "23505" in error_str or "duplicate" in error_str.lower():
                    print(f"   ⚠️ Обнаружены дубликаты в пакете {batch_num}, вставляем по одной...")
                    for record in batch:
                        try:
                            await table_insert_async("asset_payouts", record)
                            added_count += 1
                        except Exception as inner_e:
                            # Игнорируем дубликаты при индивидуальной вставке
                            inner_error_str = str(inner_e)
                            if "23505" not in inner_error_str and "duplicate" not in inner_error_str.lower():
                                print(f"      ⚠️ Ошибка вставки записи: {inner_e}")
                            else:
                                skipped_count += 1
                else:
                    print(f"   ❌ Ошибка вставки пакета {batch_num}: {e}")
    else:
        print("📭 Новых записей для вставки не найдено.")

    if skipped_count > 0:
        print(f"⏭️ Пропущено дубликатов: {skipped_count}")
    print(f"🏁 Готово. Всего добавлено новых записей: {added_count}")

if __name__ == "__main__":
    asyncio.run(update_forecasts())