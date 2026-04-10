"""
Обновление прогнозов дивидендов: SmartLab и dohod.ru (ДОХОДЪ).
Перенесено из supabase_data/update_dividends.py
"""
import asyncio
import aiohttp
import random
from collections import defaultdict
from itertools import groupby
from bs4 import BeautifulSoup
from datetime import datetime, date
from tqdm import tqdm
from app.infrastructure.database.postgres_async import (
    table_select_async,
    table_insert_async,
    table_update_async,
    table_delete_async,
)
from app.core.reference_logging import get_reference_logger, reference_progress_enabled
from app.domain.constants.payout_types import PAYOUT_TYPE_DIVIDEND_ID

logger = get_reference_logger("dividends")

# Порядок слияния дубликатов (одинаковые asset_id + record_date): меньше — раньше в merge, позже идут «дополнения».
_SOURCE_SMARTLAB_INDEX = 0
_SOURCE_SMARTLAB_HISTORY = 1
_SOURCE_DOHOD = 2

# Если у актива одна и та же выплата на бумагу, но record_date отличается на день (dohod vs SmartLab) —
# склеиваем в одну строку, каноническая дата — у источника с меньшим _source_rank (SmartLab).
FUZZY_RECORD_GAP_DAYS = 14

# URL страниц
SMARTLAB_INDEX_URL = "https://smart-lab.ru/dividends/index/order_by_yield/desc/"
SMARTLAB_HISTORY_BASE_URL = "https://smart-lab.ru/dividends/history/order_by_cut_off_date/desc/page{}/"
DOHOD_DIVIDEND_URL = "https://www.dohod.ru/ik/analytics/dividend"


async def fetch_html(session, url):
    """Загружает HTML страницы"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                return await resp.text()
            elif resp.status == 404:
                logger.warning(f"Страница не найдена (404): {url}")
                return None
            else:
                logger.warning(f"HTTP ({url}) вернул статус {resp.status}")
    except Exception as e:
        logger.error(f"Ошибка сети при запросе {url}: {e}")
    return None


def parse_date(date_str):
    """Преобразует дату из '25.12.2025' в объект date"""
    if not date_str or date_str == '-':
        return None
    lowered = date_str.strip().lower()
    if lowered in ("n/a", "na", "—"):
        return None
    try:
        return datetime.strptime(date_str.strip(), "%d.%m.%Y").date()
    except (ValueError, AttributeError):
        return None


def normalize_value(val_str):
    """Преобразует строку '9,17' или '<strong>902</strong>' в float"""
    if not val_str:
        return 0.0
    clean_val = val_str.replace(',', '.').replace(' ', '').strip()
    try:
        return float("".join(c for c in clean_val if c.isdigit() or c == '.'))
    except ValueError:
        return 0.0


def parse_smartlab_row(row, mode="index"):
    """Парсит одну строку таблицы HTML."""
    cols = row.find_all("td")
    
    if len(cols) < 5:
        return None

    try:
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
        return None


def _dohod_ticker_from_row(row, cols):
    if len(cols) > 20:
        t = cols[20].get_text(strip=True)
        if t:
            return t.upper()
    link = row.find("a", href=True)
    if link and "/dividend/" in (link.get("href") or ""):
        slug = link["href"].rstrip("/").split("/")[-1]
        if slug:
            return slug.upper()
    return None


def parse_dohod_row(row):
    """Строка таблицы #table-dividend на dohod.ru (индексы колонок по разметке страницы)."""
    cols = row.find_all("td")
    if len(cols) < 21:
        return None

    ticker = _dohod_ticker_from_row(row, cols)
    if not ticker or ticker == "XXXX":
        return None

    record_date = parse_date(cols[8].get_text(strip=True))
    if not record_date:
        return None

    value = normalize_value(cols[3].get_text(strip=True))
    if value <= 0:
        return None

    dividend_yield = normalize_value(cols[6].get_text(strip=True))
    last_buy_date = parse_date(cols[19].get_text(strip=True))

    return {
        "ticker": ticker,
        "last_buy_date": last_buy_date,
        "record_date": record_date,
        "payment_date": None,
        "value": value,
        "dividend_yield": dividend_yield,
    }


async def process_dohod_page(session, ticker_map):
    html = await fetch_html(session, DOHOD_DIVIDEND_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id="table-dividend")
    if not table:
        logger.warning("dohod.ru: не найдена таблица #table-dividend")
        return []

    tbody = table.find("tbody")
    if not tbody:
        return []

    out = []
    for row in tbody.find_all("tr"):
        item = parse_dohod_row(row)
        if not item:
            continue
        if item["ticker"] not in ticker_map:
            continue
        item["asset_id"] = ticker_map[item["ticker"]]
        out.append(item)
    return out


async def process_page(session, url, mode, ticker_map):
    """Обрабатывает одну страницу"""
    html = await fetch_html(session, url)
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_="trades-table")
    
    if not table:
        return []

    tbody = table.find("tbody")
    if not tbody:
        return []

    parsed_items = []
    rows = tbody.find_all("tr")
    
    for row in rows:
        item = parse_smartlab_row(row, mode=mode)
        
        if item and item["ticker"] in ticker_map:
            item["asset_id"] = ticker_map[item["ticker"]]
            parsed_items.append(item)
            
    return parsed_items


def _payout_pair_key(asset_id: int, record_date) -> tuple:
    iso = record_date.isoformat() if isinstance(record_date, date) else str(record_date)
    return (asset_id, iso)


def _as_date_field(d):
    """Дата из БД / merge: date, datetime или 'YYYY-MM-DD'."""
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        return date.fromisoformat(d[:10])
    return None


def build_existing_by_pair(existing_payouts: list) -> dict:
    """Одна строка на ключ (asset_id, record_date) — с минимальным id."""
    by_pair_lists = defaultdict(list)
    for p in existing_payouts:
        record_date = p.get("record_date")
        if not record_date:
            continue
        key = _payout_pair_key(p["asset_id"], record_date)
        by_pair_lists[key].append(p)
    out = {}
    for key, rows in by_pair_lists.items():
        rows.sort(key=lambda r: r.get("id") or 0)
        out[key] = rows[0]
    return out


def collect_fuzzy_obsolete_dividend_ids(merged_payouts: list, existing_payouts: list) -> set:
    """Строки в БД: тот же актив и сумма на бумагу, record_date на ≤FUZZY_RECORD_GAP_DAYS от канона merge, но не равна ему."""
    ids = set()
    for m in merged_payouts:
        m_rd = _as_date_field(m.get("record_date"))
        if m_rd is None:
            continue
        m_val = _value_cluster_key(m.get("value"))
        if m_val is None:
            continue
        for p in existing_payouts:
            if p.get("type_id") != PAYOUT_TYPE_DIVIDEND_ID:
                continue
            p_rd = _as_date_field(p.get("record_date"))
            if p_rd is None:
                continue
            if p["asset_id"] != m["asset_id"]:
                continue
            p_val = _value_cluster_key(p.get("value"))
            if p_val is None or p_val != m_val:
                continue
            if p_rd == m_rd:
                continue
            if abs((p_rd - m_rd).days) <= FUZZY_RECORD_GAP_DAYS:
                ids.add(p["id"])
    return ids


def merge_dividend_sources(items: list) -> dict:
    """Порядок items — по возрастанию _source_rank (SmartLab раньше dohod).

    Приоритет первого источника: value, dividend_yield, record_date не перетираются
    данными из следующих; из dohod только дополняем пустые поля.
    """
    m = {k: v for k, v in items[0].items() if k != "_source_rank"}
    for nxt in items[1:]:
        nxt = {k: v for k, v in nxt.items() if k != "_source_rank"}
        if nxt.get("last_buy_date"):
            m["last_buy_date"] = m.get("last_buy_date") or nxt["last_buy_date"]
        if nxt.get("payment_date"):
            m["payment_date"] = m.get("payment_date") or nxt["payment_date"]
        if nxt.get("record_date") and not m.get("record_date"):
            m["record_date"] = nxt["record_date"]
        nxt_val = float(nxt.get("value") or 0)
        if nxt_val > 0 and float(m.get("value") or 0) <= 0:
            m["value"] = nxt["value"]
        if nxt.get("dividend_yield") is not None and m.get("dividend_yield") is None:
            m["dividend_yield"] = nxt["dividend_yield"]
    return m


def _norm_payout_value_for_compare(v, nd: int = 2):
    if v is None:
        return None
    return round(float(v), nd)


def _norm_date_iso(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    s = str(v)
    return s[:10] if s else None


def payout_row_changed(existing: dict, new_payout: dict) -> bool:
    """existing — строка из БД; new_payout — поля для записи (даты ISO-строками или None)."""
    if _norm_payout_value_for_compare(existing.get("value")) != _norm_payout_value_for_compare(
        new_payout.get("value")
    ):
        return True
    if _norm_payout_value_for_compare(existing.get("dividend_yield"), nd=4) != _norm_payout_value_for_compare(
        new_payout.get("dividend_yield"), nd=4
    ):
        return True
    if (_norm_date_iso(existing.get("last_buy_date")) or None) != (new_payout.get("last_buy_date") or None):
        return True
    if (_norm_date_iso(existing.get("payment_date")) or None) != (new_payout.get("payment_date") or None):
        return True
    return False


def _build_payout_row(merged: dict, type_id: int | None = None) -> dict:
    record_date = merged["record_date"]
    tid = type_id if type_id is not None else PAYOUT_TYPE_DIVIDEND_ID
    return {
        "asset_id": merged["asset_id"],
        "value": merged["value"],
        "dividend_yield": merged.get("dividend_yield"),
        "last_buy_date": merged["last_buy_date"].isoformat() if merged.get("last_buy_date") else None,
        "record_date": record_date.isoformat() if isinstance(record_date, date) else record_date,
        "payment_date": merged["payment_date"].isoformat() if merged.get("payment_date") else None,
        "type_id": tid,
    }


def _value_cluster_key(value):
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    return round(v, 4)


def fuzzy_dedupe_dividend_rows_by_near_record_date(all_items: list) -> list:
    """Схлопывает строки одного актива с одинаковой суммой на бумагу, если record_date
    отличается не более чем на FUZZY_RECORD_GAP_DAYS (типичный сдвиг dohod.ru).

    Канонические дата/сумма/доходность — от источника с минимальным _source_rank (SmartLab).
    Строки без record_date не участвуют в fuzzy и возвращаются как есть.
    """
    with_rd: list = []
    without_rd: list = []
    for it in all_items:
        if it.get("record_date"):
            with_rd.append(it)
        else:
            without_rd.append(it)

    with_rd.sort(
        key=lambda x: (
            x["asset_id"],
            _value_cluster_key(x.get("value")) is None,
            _value_cluster_key(x.get("value")) or 0,
            x["record_date"],
        )
    )

    result: list = []

    for (aid, vk), group_iter in groupby(
        with_rd,
        key=lambda x: (x["asset_id"], _value_cluster_key(x.get("value"))),
    ):
        block = list(group_iter)
        if vk is None:
            result.extend(block)
            continue

        block.sort(key=lambda x: x["record_date"])
        clusters: list[list] = []
        cur = [block[0]]
        for it in block[1:]:
            delta = (it["record_date"] - cur[-1]["record_date"]).days
            if delta <= FUZZY_RECORD_GAP_DAYS:
                cur.append(it)
            else:
                clusters.append(cur)
                cur = [it]
        clusters.append(cur)

        for cl in clusters:
            if len(cl) == 1:
                result.append(cl[0])
                continue
            cl_sorted = sorted(cl, key=lambda x: x.get("_source_rank", 99))
            merged = merge_dividend_sources(cl_sorted)
            merged["_source_rank"] = cl_sorted[0].get("_source_rank", _SOURCE_SMARTLAB_INDEX)
            result.append(merged)

    return result + without_rd


def group_and_merge_incoming_dividends(all_items: list) -> list:
    """После загрузки всех источников: группировка по (asset_id, record_date), детерминированный порядок слияния, одна запись на ключ."""
    incoming_by_pair = defaultdict(list)
    for item in all_items:
        record_date = item.get("record_date")
        if not record_date:
            continue
        key = _payout_pair_key(item["asset_id"], record_date)
        incoming_by_pair[key].append(item)

    merged_list = []
    for _key, raw_items in incoming_by_pair.items():
        raw_items.sort(key=lambda x: x.get("_source_rank", 99))
        merged_list.append(merge_dividend_sources(raw_items))
    return merged_list


_DUPLICATE_DELETE_CHUNK = 500


async def delete_duplicate_dividend_payout_rows(payouts: list) -> tuple[int, list]:
    """Удаляет лишние строки type=dividend с тем же (asset_id, record_date); оставляет запись с минимальным id."""
    by_pair = defaultdict(list)
    for p in payouts:
        record_date = p.get("record_date")
        if not record_date:
            continue
        key = _payout_pair_key(p["asset_id"], record_date)
        by_pair[key].append(p)

    ids_to_delete: list = []
    for _key, rows in by_pair.items():
        if len(rows) <= 1:
            continue
        rows.sort(key=lambda r: r.get("id") or 0)
        for dup in rows[1:]:
            ids_to_delete.append(dup["id"])

    if not ids_to_delete:
        return 0, payouts

    delete_set = set(ids_to_delete)
    removed = 0
    for i in range(0, len(ids_to_delete), _DUPLICATE_DELETE_CHUNK):
        chunk = ids_to_delete[i : i + _DUPLICATE_DELETE_CHUNK]
        deleted = await table_delete_async("asset_payouts", in_filters={"id": chunk})
        removed += len(deleted)

    surviving = [p for p in payouts if p["id"] not in delete_set]
    return removed, surviving


def dedupe_payout_insert_rows(rows: list) -> list:
    """На случай повторов в списке вставок — один ключ (asset_id, record_date, type)."""
    seen = set()
    out = []
    for r in rows:
        rd = r.get("record_date")
        if hasattr(rd, "isoformat"):
            rd = rd.isoformat()
        k = (r["asset_id"], rd, r.get("type_id", PAYOUT_TYPE_DIVIDEND_ID))
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


async def update_forecasts(show_progress: bool | None = None):
    """Обновляет прогнозы дивидендов (SmartLab, затем dohod.ru).

    show_progress: полоса tqdm в stderr. None — см. REFERENCE_PROGRESS и TTY.
    """
    if show_progress is None:
        show_progress = reference_progress_enabled()

    assets = await table_select_async("assets")
    ticker_map = {a["ticker"].upper(): a["id"] for a in assets if a.get("ticker")}
    
    existing_payouts = await table_select_async(
        "asset_payouts",
        select="id,asset_id,record_date,value,dividend_yield,last_buy_date,payment_date,type_id",
        filters={"type_id": PAYOUT_TYPE_DIVIDEND_ID},
    )

    removed_dupes, existing_payouts = await delete_duplicate_dividend_payout_rows(existing_payouts)
    logger.info(
        "Удалено дубликатов дивидендов в БД (лишние строки по asset_id + record_date): %s",
        removed_dupes,
    )

    existing_by_pair = build_existing_by_pair(existing_payouts)

    all_items = []

    async with aiohttp.ClientSession() as session:
        logger.info("Обработка будущих дивидендов...")
        with tqdm(
            total=1,
            desc="SmartLab: прогноз",
            unit="запрос",
            disable=not show_progress,
            leave=False,
            dynamic_ncols=True,
        ) as p_future:
            future_items = await process_page(session, SMARTLAB_INDEX_URL, "index", ticker_map)
            if future_items:
                for it in future_items:
                    it["_source_rank"] = _SOURCE_SMARTLAB_INDEX
                all_items.extend(future_items)
            p_future.update(1)

        logger.info("Обработка истории дивидендов...")
        page_num = 1
        max_errors = 3
        error_count = 0

        with tqdm(
            desc="SmartLab: история",
            unit="стр",
            disable=not show_progress,
            leave=False,
            dynamic_ncols=True,
        ) as p_hist:
            while True:
                url = SMARTLAB_HISTORY_BASE_URL.format(page_num)

                history_items = await process_page(session, url, "history", ticker_map)

                if history_items is None:
                    error_count += 1
                    p_hist.set_postfix_str(f"ошибка {error_count}/{max_errors}")
                    if error_count >= max_errors:
                        break
                elif len(history_items) == 0:
                    break
                else:
                    for it in history_items:
                        it["_source_rank"] = _SOURCE_SMARTLAB_HISTORY
                    all_items.extend(history_items)
                    error_count = 0
                    p_hist.set_postfix_str(f"страница {page_num}")

                p_hist.update(1)
                page_num += 1
                if page_num > 60:
                    break

        logger.info("Обработка прогнозов dohod.ru...")
        with tqdm(
            total=1,
            desc="dohod.ru",
            unit="запрос",
            disable=not show_progress,
            leave=False,
            dynamic_ncols=True,
        ) as p_dohod:
            dohod_items = await process_dohod_page(session, ticker_map)
            if dohod_items:
                for it in dohod_items:
                    it["_source_rank"] = _SOURCE_DOHOD
                all_items.extend(dohod_items)
            p_dohod.update(1)

    logger.info(f"Всего сырых строк из источников: {len(all_items)}")

    all_items = fuzzy_dedupe_dividend_rows_by_near_record_date(all_items)
    logger.info(
        "После fuzzy-dedupe (одинаковый asset + сумма на бумагу, record_date в пределах ±%s дн.): %s строк",
        FUZZY_RECORD_GAP_DAYS,
        len(all_items),
    )

    merged_payouts = group_and_merge_incoming_dividends(all_items)
    logger.info(f"После слияния по (asset_id, record_date): {len(merged_payouts)} записей")

    fuzzy_ids = collect_fuzzy_obsolete_dividend_ids(merged_payouts, existing_payouts)
    if fuzzy_ids:
        id_list = list(fuzzy_ids)
        removed_fuzzy = 0
        for i in range(0, len(id_list), _DUPLICATE_DELETE_CHUNK):
            chunk = id_list[i : i + _DUPLICATE_DELETE_CHUNK]
            deleted = await table_delete_async("asset_payouts", in_filters={"id": chunk})
            removed_fuzzy += len(deleted)
        logger.info(
            "Удалено строк с record_date в пределах ±%s дн. от канона (та же сумма на бумагу): %s",
            FUZZY_RECORD_GAP_DAYS,
            removed_fuzzy,
        )
        existing_payouts = [p for p in existing_payouts if p["id"] not in fuzzy_ids]
        existing_by_pair = build_existing_by_pair(existing_payouts)

    payouts_to_insert = []
    payouts_to_update = []

    for merged in merged_payouts:
        record_date = merged["record_date"]
        key = _payout_pair_key(merged["asset_id"], record_date)
        new_payout = _build_payout_row(merged, type_id=PAYOUT_TYPE_DIVIDEND_ID)
        val = round(float(merged.get("value") or 0), 2)

        existing = existing_by_pair.get(key)
        if not existing:
            if val <= 0:
                continue
            payouts_to_insert.append(new_payout)
            continue

        if not payout_row_changed(existing, new_payout):
            continue

        rd = existing["record_date"]
        filters = {"asset_id": merged["asset_id"], "record_date": rd, "type_id": PAYOUT_TYPE_DIVIDEND_ID}
        payouts_to_update.append(
            (
                filters,
                {
                    "value": new_payout["value"],
                    "dividend_yield": new_payout["dividend_yield"],
                    "last_buy_date": new_payout["last_buy_date"],
                    "payment_date": new_payout["payment_date"],
                },
            )
        )

    added_count = 0
    updated_count = 0
    skipped_count = 0
    BATCH_SIZE = 1000

    if payouts_to_update:
        logger.info(f"Обновление записей с изменившимися полями: {len(payouts_to_update)}...")
        upd_iter = tqdm(
            payouts_to_update,
            desc="Обновление БД",
            unit="стр",
            disable=not show_progress,
            leave=False,
            dynamic_ncols=True,
        )
        for filters, data in upd_iter:
            try:
                rows = await table_update_async("asset_payouts", data, filters)
                updated_count += len(rows)
            except Exception as e:
                logger.warning("Ошибка UPDATE asset_payouts %s: %s", filters, e)

    if payouts_to_insert:
        _before_ins = len(payouts_to_insert)
        payouts_to_insert = dedupe_payout_insert_rows(payouts_to_insert)
        if len(payouts_to_insert) < _before_ins:
            logger.info(
                "Перед вставкой убрано дубликатов по (asset_id, record_date, type): %s",
                _before_ins - len(payouts_to_insert),
            )
        logger.info(f"Пакетная вставка {len(payouts_to_insert)} записей...")
        batch_indices = list(range(0, len(payouts_to_insert), BATCH_SIZE))
        batch_iter = tqdm(
            batch_indices,
            desc="Запись в БД",
            unit="пакет",
            disable=not show_progress,
            leave=False,
            dynamic_ncols=True,
        )
        for i in batch_iter:
            batch = payouts_to_insert[i : i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            try:
                await table_insert_async("asset_payouts", batch)
                logger.debug(f"Вставлен пакет {batch_num} ({len(batch)} записей)")
                added_count += len(batch)
            except Exception as e:
                error_str = str(e)
                if "23505" in error_str or "duplicate" in error_str.lower():
                    logger.warning(f"Дубликаты в пакете {batch_num}, вставляем по одной...")
                    for record in batch:
                        try:
                            await table_insert_async("asset_payouts", record)
                            added_count += 1
                        except Exception as inner_e:
                            inner_error_str = str(inner_e)
                            if "23505" not in inner_error_str and "duplicate" not in inner_error_str.lower():
                                logger.warning(f"Ошибка вставки записи: {inner_e}")
                            else:
                                skipped_count += 1
                else:
                    logger.error(f"Ошибка вставки пакета {batch_num}: {e}")
    elif not payouts_to_update:
        logger.info("Новых и изменённых записей для записи в БД нет.")

    if skipped_count > 0:
        logger.info(f"Пропущено дубликатов при вставке: {skipped_count}")
    logger.info(f"Готово. Добавлено: {added_count}, обновлено строк: {updated_count}")


if __name__ == "__main__":
    from app.core.logging import init_logging
    from app.utils.async_runner import run_async
    init_logging()
    run_async(update_forecasts(show_progress=True))
