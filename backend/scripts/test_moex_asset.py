"""
Тестовый скрипт для проверки всех эндпоинтов MOEX API, используемых в update_moex_assets.

Использование:
    python scripts/test_moex_asset.py SBER
    python scripts/test_moex_asset.py SU26238RMFS4
"""
import asyncio
import sys
import json
import os
from datetime import date, timedelta
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import aiohttp

# Добавляем корневую директорию проекта в путь
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.infrastructure.external.moex.client import create_moex_session, fetch_json
from app.infrastructure.external.moex.utils import get_column_index
from app.infrastructure.external.moex.constants import FUND_BOARDIDS, PRIORITY_BOARDIDS
from app.infrastructure.external.moex.price_service import get_price_moex_history


MOEX_BASE_URL = "https://iss.moex.com/iss/engines/stock/markets"


def determine_asset_type(board_id: Optional[str], market: str) -> str:
    """Определяет тип актива по BOARDID и рынку."""
    if market == "bonds":
        return "Облигация"
    
    if market == "shares":
        if board_id and board_id.upper() in FUND_BOARDIDS:
            return "Фонд"
        return "Акция"
    
    return "Акция"


async def find_asset_in_markets(session: aiohttp.ClientSession, ticker: str) -> Optional[Dict[str, Any]]:
    """
    Ищет актив во всех рынках MOEX с учетом приоритета BOARDID.
    
    Returns:
        dict с информацией об активе: {market, board_id, type, name, ...} или None
    """
    markets = ["shares", "bonds"]
    
    # Собираем все найденные записи для тикера
    found_records = []
    
    for market in markets:
        url = f"{MOEX_BASE_URL}/{market}/securities/{ticker}.json"
        try:
            data = await fetch_json(session, url, max_attempts=2)
            
            if not data or "securities" not in data:
                continue
            
            sec_cols = data.get("securities", {}).get("columns", [])
            sec_data = data.get("securities", {}).get("data", [])
            
            if not sec_cols or not sec_data:
                continue
            
            # Обрабатываем все записи (может быть несколько BOARDID для одного тикера)
            for row in sec_data:
                sec = dict(zip(sec_cols, row))
                
                board_id = sec.get("BOARDID") or sec.get("boardid")
                shortname = sec.get("SHORTNAME") or sec.get("shortname") or sec.get("SECNAME") or sec.get("secname")
                name = sec.get("NAME") or sec.get("name")
                
                asset_type = determine_asset_type(board_id, market)
                
                found_records.append({
                    "market": market,
                    "board_id": board_id,
                    "type": asset_type,
                    "ticker": ticker.upper(),
                    "shortname": shortname,
                    "name": name,
                    "data": sec,
                    "full_response": data
                })
        except Exception as e:
            continue
    
    if not found_records:
        return None
    
    # Если найдена только одна запись, возвращаем её
    if len(found_records) == 1:
        return found_records[0]
    
    # Если найдено несколько записей, выбираем с наивысшим приоритетом BOARDID
    # Логика такая же, как в update_moex_assets.py
    best_record = found_records[0]
    
    for record in found_records[1:]:
        existing_board_id = best_record["board_id"]
        current_board_id = record["board_id"]
        
        # Проверяем, является ли один из BOARDID фондом
        existing_is_fund = existing_board_id and existing_board_id.upper() in FUND_BOARDIDS
        current_is_fund = current_board_id and current_board_id.upper() in FUND_BOARDIDS
        
        # Если один из них фонд, а другой нет - выбираем фонд
        if current_is_fund and not existing_is_fund:
            best_record = record
        elif existing_is_fund and not current_is_fund:
            # Оставляем существующий (фонд)
            pass
        else:
            # Оба одинакового типа (оба фонды или оба акции) - используем приоритет
            existing_priority = PRIORITY_BOARDIDS.index(existing_board_id) if existing_board_id in PRIORITY_BOARDIDS else 999
            current_priority = PRIORITY_BOARDIDS.index(current_board_id) if current_board_id in PRIORITY_BOARDIDS else 999
            
            # Оставляем запись с более высоким приоритетом (меньший индекс)
            if current_priority < existing_priority:
                best_record = record
    
    return best_record


async def get_bond_currency(session: aiohttp.ClientSession, ticker: str) -> Optional[str]:
    """Получает валюту облигации."""
    url = f"{MOEX_BASE_URL}/bonds/securities/{ticker}.json"
    try:
        data = await fetch_json(session, url, max_attempts=2)
        
        if not data or "securities" not in data:
            return None
        
        cols = data["securities"].get("columns", [])
        rows = data["securities"].get("data", [])
        
        if not cols or not rows:
            return None
        
        i_FACEUNIT = get_column_index(cols, "FACEUNIT", "faceunit")
        i_CURRENCYID = get_column_index(cols, "CURRENCYID", "currencyid")
        
        row = rows[0]
        currency = None
        
        # Приоритет FACEUNIT, затем CURRENCYID
        if i_FACEUNIT is not None and row[i_FACEUNIT]:
            currency = str(row[i_FACEUNIT]).upper().strip()
        elif i_CURRENCYID is not None and row[i_CURRENCYID]:
            currency = str(row[i_CURRENCYID]).upper().strip()
        
        if currency:
            if currency.startswith("SUR"):
                currency = "RUB"
            elif len(currency) > 3:
                currency = currency[:3]
            return currency
        
        return None
    except Exception as e:
        return None


async def get_bond_details(session: aiohttp.ClientSession, ticker: str) -> Dict[str, Any]:
    """Получает детальную информацию об облигации."""
    url = f"{MOEX_BASE_URL}/bonds/securities/{ticker}.json"
    try:
        data = await fetch_json(session, url, max_attempts=2)
        
        if not data or "securities" not in data:
            return {}
        
        cols = data["securities"].get("columns", [])
        rows = data["securities"].get("data", [])
        
        if not cols or not rows:
            return {}
        
        row = rows[0]
        details = {}
        
        # Извлекаем все поля
        field_mappings = {
            "FACEVALUE": "face_value",
            "MATDATE": "mat_date",
            "COUPONVALUE": "coupon_value",
            "COUPONPERCENT": "coupon_percent",
            "COUPONPERIOD": "coupon_period",
            "ISSUESIZE": "issue_size",
            "FACEUNIT": "face_unit",
            "CURRENCYID": "currency_id",
            "NEXTCOUPON": "next_coupon",
            "ACCRUEDINT": "accrued_interest",
            "PREVPRICE": "prev_price",
            "PREVWAPRICE": "prev_waprice",
            "YIELDATPREVWAPRICE": "yield_at_prev_waprice",
        }
        
        for col_name, key in field_mappings.items():
            idx = get_column_index(cols, col_name, col_name.lower())
            if idx is not None and row[idx] is not None:
                details[key] = row[idx]
        
        # Вычисляем частоту купонов
        if "coupon_period" in details:
            try:
                period_days = float(details["coupon_period"])
                if period_days > 0:
                    details["coupon_frequency"] = round(365 / period_days, 1)
            except (ValueError, TypeError):
                pass
        
        return details
    except Exception as e:
        return {}


async def get_current_price(session: aiohttp.ClientSession, ticker: str, market: str, preferred_board_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Получает текущую цену актива с учетом приоритета BOARDID.
    
    Args:
        session: HTTP сессия
        ticker: Тикер актива
        market: Рынок (shares или bonds)
        preferred_board_id: Предпочтительный BOARDID (если известен из find_asset_in_markets)
    """
    url = f"{MOEX_BASE_URL}/{market}/securities/{ticker}.json"
    try:
        data = await fetch_json(session, url, max_attempts=2)
        
        if not data:
            return None
        
        md_cols = data.get("marketdata", {}).get("columns", [])
        md_data = data.get("marketdata", {}).get("data", [])
        sec_cols = data.get("securities", {}).get("columns", [])
        sec_data = data.get("securities", {}).get("data", [])
        
        if not md_data or not sec_data:
            return None
        
        # Создаем словари для сопоставления (BOARDID) -> данные
        md_records = {}
        sec_records = {}
        
        i_BOARDID_md = get_column_index(md_cols, "BOARDID", "boardid")
        i_BOARDID_sec = get_column_index(sec_cols, "BOARDID", "boardid")
        
        # Собираем все записи из marketdata
        for md_row in md_data:
            if i_BOARDID_md is not None:
                board_id = md_row[i_BOARDID_md]
                if board_id:
                    md_records[board_id] = dict(zip(md_cols, md_row))
        
        # Собираем все записи из securities
        for sec_row in sec_data:
            if i_BOARDID_sec is not None:
                board_id = sec_row[i_BOARDID_sec]
                if board_id:
                    sec_records[board_id] = dict(zip(sec_cols, sec_row))
        
        # Выбираем запись с приоритетным BOARDID и валидной ценой
        selected_board_id = None
        
        # Фильтруем записи с валидной ценой
        valid_md_records = {}
        for board_id, md_record in md_records.items():
            last_price = md_record.get("LAST")
            # Проверяем, что цена есть и не равна нулю
            if last_price is not None and (isinstance(last_price, (int, float)) and float(last_price) > 0):
                valid_md_records[board_id] = md_record
        
        if not valid_md_records:
            return None
        
        # Выбираем BOARDID с наивысшим приоритетом из записей с валидной ценой
        available_board_ids = list(valid_md_records.keys())
        
        if len(available_board_ids) == 1:
            selected_board_id = available_board_ids[0]
        else:
            # Если есть предпочтительный BOARDID и у него есть валидная цена, используем его
            if preferred_board_id and preferred_board_id in valid_md_records:
                selected_board_id = preferred_board_id
            else:
                # Используем ту же логику приоритета, что и в основном скрипте
                best_board_id = available_board_ids[0]
                
                for board_id in available_board_ids[1:]:
                    existing_is_fund = best_board_id and best_board_id.upper() in FUND_BOARDIDS
                    current_is_fund = board_id and board_id.upper() in FUND_BOARDIDS
                    
                    if current_is_fund and not existing_is_fund:
                        best_board_id = board_id
                    elif existing_is_fund and not current_is_fund:
                        pass  # Оставляем существующий
                    else:
                        existing_priority = PRIORITY_BOARDIDS.index(best_board_id) if best_board_id in PRIORITY_BOARDIDS else 999
                        current_priority = PRIORITY_BOARDIDS.index(board_id) if board_id in PRIORITY_BOARDIDS else 999
                        
                        if current_priority < existing_priority:
                            best_board_id = board_id
                
                selected_board_id = best_board_id
        
        if not selected_board_id or selected_board_id not in valid_md_records:
            return None
        
        md = valid_md_records[selected_board_id]
        sec = sec_records.get(selected_board_id, {})
        
        last_price = md.get("LAST")
        face_value = sec.get("FACEVALUE") or sec.get("facevalue")
        
        price_info = {
            "board_id": selected_board_id,
            "last": last_price,
            "face_value": face_value,
        }
        
        # Для облигаций конвертируем цену из процентов в абсолютное значение
        if market == "bonds" and face_value and last_price:
            try:
                absolute_price = (float(last_price) / 100) * float(face_value)
                price_info["absolute_price"] = absolute_price
                price_info["price_percent"] = float(last_price)
            except (ValueError, TypeError):
                pass
        
        # Добавляем другие поля из marketdata
        for key in ["OPEN", "HIGH", "LOW", "VOLUME", "VALUE", "NUMTRADES", "WAPRICE", "TRADINGSTATUS"]:
            if key in md and md[key] is not None:
                price_info[key.lower()] = md[key]
        
        return price_info
    except Exception as e:
        return None


async def get_price_history(session: aiohttp.ClientSession, ticker: str, market: str, days: int = 30) -> List[Tuple[str, float]]:
    """Получает историю цен актива."""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    url = f"{MOEX_BASE_URL}/{market}/securities/{ticker}/candles.json?interval=24&from={start_date}&to={end_date}"
    
    try:
        data = await fetch_json(session, url, max_attempts=2)
        
        if not data:
            return []
        
        candles = data.get('candles', {}).get('data', [])
        
        if not candles:
            return []
        
        if market == "shares":
            return [(row[6], row[1]) for row in candles if row[1] is not None]
        elif market == "bonds":
            # Для облигаций используем close цену (row[1]) - это цена в процентах от номинала
            return [
                (row[6], row[1])  # (date, close_price в процентах)
                for row in candles
                if row[1] is not None and row[1] > 0
            ]
        
        return []
    except Exception as e:
        return []


def print_section(title: str):
    """Печатает заголовок секции."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_dict(data: Dict[str, Any], indent: int = 2):
    """Печатает словарь в читаемом формате."""
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"{' ' * indent}{key}:")
            print_dict(value, indent + 2)
        elif isinstance(value, list):
            print(f"{' ' * indent}{key}: [{len(value)} элементов]")
        else:
            print(f"{' ' * indent}{key}: {value}")


async def test_asset(ticker: str):
    """Тестирует все эндпоинты для указанного актива."""
    ticker = ticker.upper().strip()
    
    print_section(f"Тестирование актива: {ticker}")
    
    async with create_moex_session() as session:
        # 1. Поиск актива во всех рынках
        print_section("1. Поиск актива")
        asset_info = await find_asset_in_markets(session, ticker)
        
        if not asset_info:
            print(f"❌ Актив {ticker} не найден ни на одном рынке MOEX")
            return
        
        print(f"✅ Актив найден:")
        print(f"   Рынок: {asset_info['market']}")
        print(f"   Тип: {asset_info['type']}")
        print(f"   BOARDID: {asset_info['board_id']}")
        print(f"   Короткое название: {asset_info['shortname']}")
        if asset_info['name']:
            print(f"   Полное название: {asset_info['name']}")
        
        market = asset_info['market']
        asset_type = asset_info['type']
        
        # 2. Детальная информация
        print_section("2. Детальная информация")
        if asset_type == "Облигация":
            bond_details = await get_bond_details(session, ticker)
            if bond_details:
                print("Детали облигации:")
                print_dict(bond_details)
            else:
                print("⚠️ Не удалось получить детальную информацию об облигации")
        else:
            print("Детальная информация:")
            print_dict(asset_info['data'])
        
        # 3. Валюта
        print_section("3. Валюта")
        if asset_type == "Облигация":
            currency = await get_bond_currency(session, ticker)
            if currency:
                print(f"✅ Валюта облигации: {currency}")
            else:
                print("⚠️ Не удалось определить валюту (по умолчанию: RUB)")
        else:
            print("Акции и фонды торгуются в рублях (RUB)")
        
        # 4. Текущая цена
        print_section("4. Текущая цена")
        price_info = await get_current_price(session, ticker, market, preferred_board_id=asset_info['board_id'])
        if price_info:
            print("Текущая цена:")
            print_dict(price_info)
        else:
            print("⚠️ Не удалось получить текущую цену")
        
        # 5. История цен
        print_section("5. История цен (последние 30 дней)")
        price_history = await get_price_history(session, ticker, market, days=30)
        if price_history:
            print(f"✅ Получено {len(price_history)} записей:")
            print("\nПоследние 10 записей:")
            for date_str, price in price_history[-10:]:
                if asset_type == "Облигация":
                    print(f"   {date_str}: {price:.2f}%")
                else:
                    print(f"   {date_str}: {price:.2f}")
            
            if len(price_history) > 10:
                print(f"\n... и еще {len(price_history) - 10} записей")
        else:
            print("⚠️ Не удалось получить историю цен")
        
        # 6. Проверка эндпоинтов
        print_section("6. Проверка всех используемых эндпоинтов")
        
        endpoints_to_check = []
        
        if market == "shares":
            endpoints_to_check = [
                ("Акции (массовый)", f"{MOEX_BASE_URL}/shares/securities.json"),
                ("Акция (детально)", f"{MOEX_BASE_URL}/shares/securities/{ticker}.json"),
                ("История цен", f"{MOEX_BASE_URL}/shares/securities/{ticker}/candles.json?interval=24&from={date.today() - timedelta(days=7)}&to={date.today()}"),
            ]
        elif market == "bonds":
            endpoints_to_check = [
                ("Облигации (все)", f"https://iss.moex.com/iss/securities.json?engine=stock&market=bonds"),
                ("Активные облигации", f"{MOEX_BASE_URL}/bonds/securities.json"),
                ("Облигация (детально)", f"{MOEX_BASE_URL}/bonds/securities/{ticker}.json"),
                ("История цен", f"{MOEX_BASE_URL}/bonds/securities/{ticker}/candles.json?interval=24&from={date.today() - timedelta(days=7)}&to={date.today()}"),
            ]
        
        for name, url in endpoints_to_check:
            try:
                data = await fetch_json(session, url, max_attempts=1)
                if data:
                    print(f"✅ {name}: OK")
                else:
                    print(f"⚠️ {name}: Пустой ответ")
            except Exception as e:
                print(f"❌ {name}: Ошибка - {e}")
        
        print_section("Тестирование завершено")


def main():
    """Главная функция."""
    if len(sys.argv) < 2:
        print("Использование: python scripts/test_moex_asset.py <TICKER>")
        print("\nПримеры:")
        print("  python scripts/test_moex_asset.py SBER")
        print("  python scripts/test_moex_asset.py SU26238RMFS4")
        print("  python scripts/test_moex_asset.py FXIT")
        sys.exit(1)
    
    ticker = sys.argv[1]
    
    try:
        asyncio.run(test_asset(ticker))
    except KeyboardInterrupt:
        print("\n\n⚠️ Прервано пользователем")
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
