import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, date
from app.services.supabase_service import table_select, table_insert

# URL страницы дивидендов (как в вашем файле)
SMARTLAB_URL = "https://smart-lab.ru/dividends/index/order_by_yield/desc/"

async def fetch_html(session, url):
    """Загружает HTML страницы"""
    try:
        # Используем заголовки, чтобы сайт не блокировал бота
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                return await resp.text()
            else:
                print(f"⚠️ SmartLab вернул статус {resp.status}")
    except Exception as e:
        print(f"❌ Ошибка сети: {e}")
    return None

def parse_date(date_str):
    """Преобразует дату из '25.12.2025' в объект date"""
    try:
        return datetime.strptime(date_str.strip(), "%d.%m.%Y").date()
    except (ValueError, AttributeError):
        return None

def normalize_value(val_str):
    """Преобразует строку '9,17' или '<strong>902</strong>' в float"""
    if not val_str:
        return 0.0
    # Убираем пробелы и заменяем запятую на точку
    clean_val = val_str.replace(',', '.').replace(' ', '').strip()
    try:
        return float("".join(c for c in clean_val if c.isdigit() or c == '.'))
    except ValueError:
        return 0.0

def parse_smartlab_row(row):
    """Парсит одну строку таблицы HTML"""
    cols = row.find_all("td")
    
    # Проверка структуры: в вашем файле таблица имеет 11 колонок (индексы 0-10)
    if len(cols) < 8:
        return None

    try:
        # 1. Тикер - Индекс 1 (напр. <td>SFIN</td>)
        ticker = cols[1].get_text(strip=True)
        
        # 2. Значение дивиденда - Индекс 3 (напр. <td><strong>902</strong></td>)
        value_text = cols[3].get_text(strip=True)
        value = normalize_value(value_text)

        # 3. Дата закрытия реестра - Индекс 7 (напр. <td>25.12.2025</td>)
        # Важно: берем именно дату реестра, а не дату покупки (которая индекс 6)
        date_text = cols[7].get_text(strip=True)
        record_date = parse_date(date_text)

        # Если даты нет (или стоит '?'), пропускаем, так как не можем записать в БД
        if not record_date:
            return None

        # 4. Определение статуса на основе классов строки
        # В вашем файле утвержденные строки имеют класс "dividend_approved"
        row_classes = row.get("class", [])
        
        if "dividend_approved" in row_classes:
            status = "confirmed" # Утверждено
        elif "gray" in row_classes or "?" in date_text:
            status = "forecast"  # Прогноз
        else:
            status = "recommended" # Рекомендовано (обычно белые строки без класса approved)

        return {
            "ticker": ticker.upper(),
            "record_date": record_date,
            "value": value,
            "status": status
        }
    except Exception as e:
        # print(f"Ошибка парсинга строки: {e}")
        return None

async def update_forecasts():
    # 1. Получаем ID активов из нашей базы
    assets = await asyncio.to_thread(table_select, "assets")
    # Карта {TICKER: ID}
    ticker_map = {a["ticker"].upper(): a["id"] for a in assets if a.get("ticker")}
    
    async with aiohttp.ClientSession() as session:
        print("⏳ Скачиваем данные со Smart-Lab...")
        html = await fetch_html(session, SMARTLAB_URL)
    
    if not html:
        return

    soup = BeautifulSoup(html, "lxml")
    
    # Ищем таблицу по классам из вашего файла
    table = soup.find("table", class_="trades-table")
    if not table:
        print("⚠️ Таблица не найдена")
        return

    # 2. Собираем данные с сайта
    parsed_items = []
    # Пропускаем заголовок (thead) и идем по строкам (tbody -> tr)
    tbody = table.find("tbody")
    if tbody:
        rows = tbody.find_all("tr")
        for row in rows:
            item = parse_smartlab_row(row)
            if item and item["ticker"] in ticker_map:
                item["asset_id"] = ticker_map[item["ticker"]]
                parsed_items.append(item)

    print(f"📊 Найдено выплат для ваших активов: {len(parsed_items)}")

    # 3. Получаем существующие выплаты, чтобы не дублировать
    # (Особенно важно для статусов: если в базе уже confirmed, не менять на forecast)
    existing_payouts = await asyncio.to_thread(table_select, "asset_payouts")
    
    # Ключ: (asset_id, record_date, value) -> status
    existing_map = {
        (p["asset_id"], str(p["record_date"]), float(p["value"] or 0)): p.get("status") 
        for p in existing_payouts if p["record_date"]
    }

    added_count = 0
    today = date.today()

    for item in parsed_items:
        # Нас интересуют только будущие или сегодняшние события
        if item["record_date"] < today:
            continue

        key = (item["asset_id"], str(item["record_date"]), item["value"])
        
        # Если запись уже есть
        if key in existing_map:
            # Можно добавить логику обновления статуса, если он изменился 
            # (например, был forecast, стал confirmed)
            current_status_in_db = existing_map[key]
            if current_status_in_db != "confirmed" and item["status"] == "confirmed":
                # Тут можно вызвать table_update, если нужно обновить статус
                pass 
            continue

        # Формируем запись
        new_payout = {
            "asset_id": item["asset_id"],
            "value": item["value"],
            "declared_date": None,
            "record_date": item["record_date"].isoformat(),
            "payment_date": None, 
            "type": "dividend",
            "status": item["status"] # Поле, которое мы добавили в SQL
        }

        try:
            await asyncio.to_thread(table_insert, "asset_payouts", new_payout)
            print(f"✅ +{item['status']}: {item['ticker']} {item['value']}р ({item['record_date']})")
            added_count += 1
        except Exception as e:
            # Ошибка может возникнуть из-за Unique Constraint, если он есть
            print(f"⚠️ Пропуск {item['ticker']}: {e}")

    print(f"🏁 Готово. Добавлено новых записей: {added_count}")

if __name__ == "__main__":
    asyncio.run(update_forecasts())