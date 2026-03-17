"""
Импорт и обновление активов MOEX.
"""
import asyncio
from typing import Optional, List, Dict, Tuple
from tqdm import tqdm
from app.infrastructure.database.postgres_async import (
    table_select_async,
    table_insert_async,
    table_update_async,
    table_delete_async
)
from app.infrastructure.external.moex.client import create_moex_session, fetch_json
from app.infrastructure.external.moex.constants import FUND_BOARDIDS, PRIORITY_BOARDIDS
from app.infrastructure.external.moex.utils import (
    get_column_index,
    parse_json_properties,
    get_asset_type_name
)
from app.core.logging import get_logger

logger = get_logger(__name__)

SHARES_ENDPOINT = "https://iss.moex.com/iss/engines/stock/markets/shares/securities.json"
BONDS_SECURITIES_ENDPOINT = "https://iss.moex.com/iss/securities.json"
BONDS_ACTIVE_ENDPOINT = "https://iss.moex.com/iss/engines/stock/markets/bonds/securities.json"
BONDS_HISTORY_TICKER_ENDPOINT = "https://iss.moex.com/iss/history/engines/stock/markets/bonds/securities"

MAX_EXAMPLES = 10


# ---------------------------------------------------------------------------
#  Вспомогательные функции
# ---------------------------------------------------------------------------

def determine_asset_type(board_id: str, market: str) -> str:
    if market == "bonds":
        return "Облигация"
    if market == "shares":
        if board_id and board_id.upper() in FUND_BOARDIDS:
            return "Фонд"
        return "Акция"
    return "Акция"


def normalize_properties(props, asset_type_name):
    normalized = {"source": "moex"}

    isin = props.get("isin")
    if isin and (isin.strip() if isinstance(isin, str) else isin):
        normalized["isin"] = isin

    if asset_type_name == "Облигация":
        for key in ("board_id",):
            val = props.get(key)
            if val and (val.strip() if isinstance(val, str) else val):
                normalized[key] = val

        for key in ("face_value", "mat_date", "coupon_value", "coupon_percent",
                     "coupon_period", "coupon_frequency", "issue_size"):
            val = props.get(key)
            if val is not None:
                if isinstance(val, str) and not val.strip():
                    continue
                normalized[key] = val

    return normalized


def compare_assets(existing_asset, new_asset):
    needs_update = False
    update_data = {}
    differences = []

    existing_type_id = existing_asset.get("asset_type_id")
    new_type_id = new_asset.get("asset_type_id")
    new_type_name = get_asset_type_name(new_type_id)

    if existing_type_id != new_type_id:
        needs_update = True
        update_data["asset_type_id"] = new_type_id
        differences.append(f"type: {existing_type_id}->{new_type_id}")

    existing_name = (existing_asset.get("name") or "").strip()
    new_name = (new_asset.get("name") or "").strip()
    if existing_name != new_name:
        needs_update = True
        update_data["name"] = new_asset["name"]
        differences.append(f"name: '{existing_name}'->'{new_name}'")

    existing_props = parse_json_properties(existing_asset.get("properties"))
    new_props = parse_json_properties(new_asset.get("properties"))
    existing_norm = normalize_properties(existing_props, new_type_name)
    new_norm = normalize_properties(new_props, new_type_name)
    has_extra = len(existing_props) > len(existing_norm)

    if existing_norm != new_norm or has_extra:
        needs_update = True
        update_data["properties"] = new_norm
        differences.append("properties")

    existing_quote = existing_asset.get("quote_asset_id")
    new_quote = new_asset.get("quote_asset_id")
    if existing_quote != new_quote:
        needs_update = True
        update_data["quote_asset_id"] = new_quote
        differences.append(f"quote: {existing_quote}->{new_quote}")

    return needs_update, update_data, differences


def get_bond_currency(ticker: str, existing_asset=None, historical_bonds_currency=None) -> Optional[str]:
    if existing_asset:
        props = parse_json_properties(existing_asset.get("properties"))
        if "currency" in props:
            c = props["currency"]
            if c.startswith("SUR"):
                c = "RUB"
            elif len(c) > 3:
                c = c[:3]
            return c

    if historical_bonds_currency and ticker in historical_bonds_currency:
        val = historical_bonds_currency[ticker]
        if isinstance(val, dict):
            return val.get("currency")
        return val

    return None


# ---------------------------------------------------------------------------
#  Вставка/обновление
# ---------------------------------------------------------------------------

async def upsert_asset(asset, existing_assets) -> Tuple[str, List[str]]:
    """Returns (status, differences)  where status is inserted/updated/no_change."""
    ticker = asset["ticker"].upper()
    existing = existing_assets.get(ticker)

    if existing:
        needs_update, update_data, diffs = compare_assets(existing, asset)
        if needs_update:
            await table_update_async("assets", update_data, {"id": existing["id"]})
            return "updated", diffs
        return "no_change", []

    dup_check = await table_select_async(
        "assets", "id, ticker, asset_type_id, name, properties, quote_asset_id",
        filters={"ticker": ticker, "user_id": None}, limit=1,
    )
    if dup_check:
        dup = dup_check[0]
        dup["properties"] = parse_json_properties(dup.get("properties"))
        needs_update, update_data, diffs = compare_assets(dup, asset)
        if needs_update:
            await table_update_async("assets", update_data, {"id": dup["id"]})
            return "updated", diffs
        return "no_change", []

    await table_insert_async("assets", asset)
    return "inserted", []


# ---------------------------------------------------------------------------
#  Загрузчики данных MOEX
# ---------------------------------------------------------------------------

async def fetch_all_bonds(session):
    all_rows = []
    all_cols = None
    start = 0
    limit = 100

    logger.info("Загрузка списка облигаций...")

    while True:
        url = f"{BONDS_SECURITIES_ENDPOINT}?engine=stock&market=bonds&start={start}&limit={limit}"
        js = await fetch_json(session, url)
        if not js or "securities" not in js:
            break

        cols = js["securities"].get("columns", [])
        rows = js["securities"].get("data", [])
        if not cols or not rows:
            break

        if all_cols is None:
            all_cols = cols

        all_rows.extend(rows)
        if len(rows) < limit:
            break

        start += limit
        await asyncio.sleep(0.1)

    logger.info(f"Загружено {len(all_rows)} облигаций")
    return all_rows, all_cols


async def fetch_active_bonds_currency(session) -> Dict:
    logger.info("Загрузка данных активных облигаций...")
    js = await fetch_json(session, BONDS_ACTIVE_ENDPOINT)
    active_data: Dict = {}

    if not js or "securities" not in js:
        return active_data

    cols = js["securities"].get("columns", [])
    rows = js["securities"].get("data", [])
    if not cols or not rows:
        return active_data

    i_SECID = get_column_index(cols, "SECID", "secid")
    i_CURRENCYID = get_column_index(cols, "CURRENCYID", "currencyid")
    i_FACEUNIT = get_column_index(cols, "FACEUNIT", "faceunit")
    i_FACEVALUE = get_column_index(cols, "FACEVALUE", "facevalue")
    i_COUPONPERCENT = get_column_index(cols, "COUPONPERCENT", "couponpercent")
    i_COUPONVALUE = get_column_index(cols, "COUPONVALUE", "couponvalue")
    i_PREVPRICE = get_column_index(cols, "PREVPRICE", "prevprice")
    i_PREVWAPRICE = get_column_index(cols, "PREVWAPRICE", "prevwaprice")

    if i_SECID is None:
        return active_data

    for row in rows:
        ticker = row[i_SECID]
        if not ticker:
            continue
        ticker = ticker.upper().strip()

        currency = None
        if i_FACEUNIT is not None and row[i_FACEUNIT]:
            currency = str(row[i_FACEUNIT]).upper().strip()
        elif i_CURRENCYID is not None and row[i_CURRENCYID]:
            currency = str(row[i_CURRENCYID]).upper().strip()
        if currency:
            currency = "RUB" if currency.startswith("SUR") else currency[:3]

        def _float(idx):
            if idx is not None and row[idx] is not None:
                try:
                    return float(row[idx])
                except (ValueError, TypeError):
                    pass
            return None

        face_value = _float(i_FACEVALUE)
        coupon_percent = _float(i_COUPONPERCENT)
        coupon_value = _float(i_COUPONVALUE)

        prev_price = _float(i_PREVPRICE)
        prev_wap = _float(i_PREVWAPRICE)
        has_prices = (prev_price is not None and prev_price > 0) or \
                     (prev_wap is not None and prev_wap > 0)

        if currency or face_value is not None or coupon_percent is not None or coupon_value is not None:
            active_data[ticker] = {
                "currency": currency, "face_value": face_value,
                "coupon_percent": coupon_percent, "coupon_value": coupon_value,
                "has_prices": has_prices,
            }

    logger.info(f"Активных облигаций с данными: {len(active_data)}")
    return active_data


async def fetch_bond_currency_single(session, ticker: str) -> Optional[dict]:
    url = f"{BONDS_HISTORY_TICKER_ENDPOINT}/{ticker}.json"
    js = await fetch_json(session, url, max_attempts=2)

    if not js or "history" not in js:
        return None

    cols = js["history"].get("columns", [])
    rows = js["history"].get("data", [])
    if not cols or not rows:
        return None

    i_CURRENCYID = get_column_index(cols, "CURRENCYID", "currencyid")
    i_FACEUNIT = get_column_index(cols, "FACEUNIT", "faceunit")
    i_COUPONPERCENT = get_column_index(cols, "COUPONPERCENT", "couponpercent")
    i_COUPONVALUE = get_column_index(cols, "COUPONVALUE", "couponvalue")
    i_CLOSE = get_column_index(cols, "CLOSE", "close")
    i_NUMTRADES = get_column_index(cols, "NUMTRADES", "numtrades")

    has_prices = False
    if i_CLOSE is not None:
        has_prices = any(row[i_CLOSE] is not None and row[i_CLOSE] > 0 for row in rows)
    if not has_prices and i_NUMTRADES is not None:
        has_prices = any(row[i_NUMTRADES] is not None and row[i_NUMTRADES] > 0 for row in rows)

    row = rows[-1]
    currency = None
    if i_FACEUNIT is not None and row[i_FACEUNIT]:
        currency = str(row[i_FACEUNIT]).upper().strip()
    elif i_CURRENCYID is not None and row[i_CURRENCYID]:
        currency = str(row[i_CURRENCYID]).upper().strip()
    if currency:
        currency = "RUB" if currency.startswith("SUR") else currency[:3]

    def _fval(idx):
        if idx is not None and row[idx] is not None:
            try:
                return float(row[idx])
            except (ValueError, TypeError):
                pass
        return None

    coupon_percent = _fval(i_COUPONPERCENT)
    coupon_value = _fval(i_COUPONVALUE)

    if not currency and coupon_percent is None and coupon_value is None and not has_prices:
        return None

    return {
        "currency": currency, "coupon_percent": coupon_percent,
        "coupon_value": coupon_value, "has_prices": has_prices,
    }


async def fetch_inactive_bonds_currency_batch(session, tickers: list, batch_size: int = 20) -> dict:
    if not tickers:
        return {}

    logger.info(f"Загрузка данных {len(tickers)} неактивных облигаций...")
    inactive_data: Dict = {}

    pbar = tqdm(total=len(tickers), desc="Неактивные облигации", unit="шт", leave=False)
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        tasks = [fetch_bond_currency_single(session, t) for t in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for t, data in zip(batch, results):
            if isinstance(data, Exception):
                continue
            if data:
                inactive_data[t] = data

        pbar.update(len(batch))
        if i + batch_size < len(tickers):
            await asyncio.sleep(0.2)
    pbar.close()

    logger.info(f"Получено данных для {len(inactive_data)} неактивных облигаций")
    return inactive_data


# ---------------------------------------------------------------------------
#  Обработка акций / облигаций
# ---------------------------------------------------------------------------

async def process_shares(session, existing_assets, type_map, currency_map):
    js = await fetch_json(session, SHARES_ENDPOINT)
    if not js or "securities" not in js:
        logger.warning("Нет данных для shares")
        return 0, 0

    cols = js["securities"].get("columns", [])
    rows = js["securities"].get("data", [])
    if not cols or not rows:
        return 0, 0

    logger.info(f"Shares: получено {len(rows)} записей от MOEX")

    i_SECID = get_column_index(cols, "secid", "SECID")
    i_SHORTNAME = get_column_index(cols, "shortname", "SHORTNAME", "name")
    i_NAME = get_column_index(cols, "name", "NAME")
    i_ISIN = get_column_index(cols, "isin", "ISIN")
    i_BOARDID = get_column_index(cols, "boardid", "BOARDID")

    if i_SECID is None:
        logger.warning("Shares: колонка SECID не найдена")
        return 0, 0

    return await _process_assets(
        rows, cols, i_SECID, i_SHORTNAME, i_NAME, i_ISIN, i_BOARDID,
        "shares", existing_assets, type_map, currency_map, None, None,
    )


async def process_bonds(all_rows, all_cols, existing_assets, type_map, currency_map,
                        bonds_currency, active_bonds_data=None, historical_bonds_data=None):
    if not all_rows or not all_cols:
        logger.warning("Нет данных для bonds")
        return 0, 0

    logger.info(f"Bonds: получено {len(all_rows)} записей от MOEX")

    i_SECID = get_column_index(all_cols, "secid", "SECID")
    i_SHORTNAME = get_column_index(all_cols, "shortname", "SHORTNAME", "name")
    i_NAME = get_column_index(all_cols, "name", "NAME")
    i_ISIN = get_column_index(all_cols, "isin", "ISIN")
    i_PRIMARY_BOARDID = get_column_index(all_cols, "primary_boardid", "PRIMARY_BOARDID")
    i_MARKETPRICE_BOARDID = get_column_index(all_cols, "marketprice_boardid", "MARKETPRICE_BOARDID")

    if i_SECID is None:
        logger.warning("Bonds: колонка SECID не найдена")
        return 0, 0

    i_BOARDID = i_PRIMARY_BOARDID if i_PRIMARY_BOARDID is not None else i_MARKETPRICE_BOARDID

    return await _process_assets(
        all_rows, all_cols, i_SECID, i_SHORTNAME, i_NAME, i_ISIN, i_BOARDID,
        "bonds", existing_assets, type_map, currency_map,
        historical_bonds_data, bonds_currency, active_bonds_data,
    )


async def _process_assets(rows, cols, i_SECID, i_SHORTNAME, i_NAME, i_ISIN, i_BOARDID,
                          market, existing_assets, type_map, currency_map,
                          historical_bonds_data=None, historical_bonds_currency=None,
                          active_bonds_data=None):
    if i_SECID is None:
        return 0, 0

    # Удаление дубликатов по тикеру, сохраняя BOARDID с наивысшим приоритетом
    ticker_records: Dict = {}
    for r in rows:
        ticker = r[i_SECID] if i_SECID is not None else None
        if not ticker:
            continue
        ticker = ticker.upper().strip()
        board_id = r[i_BOARDID] if i_BOARDID is not None and r[i_BOARDID] else None

        if ticker in ticker_records:
            existing_bid = ticker_records[ticker]["board_id"]
            ex_fund = existing_bid and existing_bid.upper() in FUND_BOARDIDS
            cur_fund = board_id and board_id.upper() in FUND_BOARDIDS
            if cur_fund and not ex_fund:
                ticker_records[ticker] = {"row": r, "board_id": board_id}
            elif not (ex_fund and not cur_fund):
                ex_pri = PRIORITY_BOARDIDS.index(existing_bid) if existing_bid in PRIORITY_BOARDIDS else 999
                cu_pri = PRIORITY_BOARDIDS.index(board_id) if board_id in PRIORITY_BOARDIDS else 999
                if cu_pri < ex_pri:
                    ticker_records[ticker] = {"row": r, "board_id": board_id}
        else:
            ticker_records[ticker] = {"row": r, "board_id": board_id}

    inserted = 0
    updated = 0
    no_change = 0
    skipped_no_prices = 0

    inserted_examples: List[str] = []
    updated_examples: List[str] = []

    pbar = tqdm(total=len(ticker_records), desc=f"Обработка {market}", unit="шт", leave=False)

    for ticker, rec in ticker_records.items():
        r = rec["row"]
        board_id = rec["board_id"]
        actual_type_name = determine_asset_type(board_id, market)

        name = None
        if i_SHORTNAME is not None and r[i_SHORTNAME]:
            name = r[i_SHORTNAME]
        elif i_NAME is not None and r[i_NAME]:
            name = r[i_NAME]
        if not name:
            name = ticker

        currency = "RUB"
        props: Dict = {"source": "moex"}

        isin = r[i_ISIN] if i_ISIN is not None and r[i_ISIN] else None
        if isin:
            props["isin"] = isin

        if actual_type_name == "Облигация":
            is_active_bond = active_bonds_data and ticker in active_bonds_data

            bond_has_prices = False
            if is_active_bond:
                bond_has_prices = active_bonds_data[ticker].get("has_prices", False)
            if not bond_has_prices and historical_bonds_data is not None:
                hist = historical_bonds_data.get(ticker)
                if hist:
                    bond_has_prices = hist.get("has_prices", False)

            if not bond_has_prices:
                skipped_no_prices += 1
                pbar.update(1)
                continue

            if board_id:
                props["board_id"] = board_id

            existing_bond = existing_assets.get(ticker)
            bond_currency = get_bond_currency(ticker, existing_bond, historical_bonds_currency)
            if bond_currency:
                currency = bond_currency
                props["currency"] = currency

            face_value = None
            if active_bonds_data and ticker in active_bonds_data:
                face_value = active_bonds_data[ticker].get("face_value")
            if face_value is None and existing_bond:
                ep = parse_json_properties(existing_bond.get("properties"))
                face_value = ep.get("face_value")
            if face_value is not None:
                props["face_value"] = face_value

            coupon_percent = coupon_value = None
            if active_bonds_data and ticker in active_bonds_data:
                bd = active_bonds_data[ticker]
                coupon_percent = bd.get("coupon_percent")
                coupon_value = bd.get("coupon_value")
            elif historical_bonds_data and ticker in historical_bonds_data:
                bd = historical_bonds_data[ticker]
                coupon_percent = bd.get("coupon_percent")
                coupon_value = bd.get("coupon_value")
            if existing_bond and (coupon_percent is None or coupon_value is None):
                ep = parse_json_properties(existing_bond.get("properties"))
                coupon_percent = coupon_percent if coupon_percent is not None else ep.get("coupon_percent")
                coupon_value = coupon_value if coupon_value is not None else ep.get("coupon_value")
            if coupon_percent is not None:
                props["coupon_percent"] = coupon_percent
            if coupon_value is not None:
                props["coupon_value"] = coupon_value

        props = normalize_properties(props, actual_type_name)

        asset_type_id = type_map.get(actual_type_name)
        if not asset_type_id:
            pbar.update(1)
            continue

        quote_asset_id = None
        if currency in ("RUB", "SUR"):
            quote_asset_id = 1
        elif currency and currency_map:
            quote_asset_id = currency_map.get(currency.upper())

        asset = {
            "asset_type_id": asset_type_id,
            "user_id": None,
            "name": name,
            "ticker": ticker,
            "properties": props,
            "quote_asset_id": quote_asset_id or (1 if currency in ("RUB", "SUR") else None),
        }

        status, diffs = await upsert_asset(asset, existing_assets)
        if status == "inserted":
            inserted += 1
            if len(inserted_examples) < MAX_EXAMPLES:
                inserted_examples.append(f"  {ticker} ({name}, {actual_type_name})")
        elif status == "updated":
            updated += 1
            if len(updated_examples) < MAX_EXAMPLES:
                updated_examples.append(f"  {ticker}: {', '.join(diffs)}")
        else:
            no_change += 1

        pbar.update(1)

    pbar.close()

    # Итоги
    logger.info(
        f"[{market}] Добавлено: {inserted}, обновлено: {updated}, "
        f"без изменений: {no_change}, пропущено (нет цен): {skipped_no_prices}"
    )
    if inserted_examples:
        logger.info(f"[{market}] Добавленные активы (до {MAX_EXAMPLES}):\n" + "\n".join(inserted_examples))
    if updated_examples:
        logger.info(f"[{market}] Обновлённые активы (до {MAX_EXAMPLES}):\n" + "\n".join(updated_examples))

    return inserted, updated


# ---------------------------------------------------------------------------
#  Удаление дубликатов
# ---------------------------------------------------------------------------

async def remove_duplicate_assets():
    logger.info("Поиск дубликатов...")
    raw = await table_select_async(
        "assets", "id, name, ticker, properties, user_id, quote_asset_id", limit=None,
    )

    ticker_groups: Dict[str, list] = {}
    for a in raw:
        if not a.get("ticker") or a.get("user_id") is not None:
            continue
        ticker = a["ticker"].upper()
        ticker_groups.setdefault(ticker, []).append(a)

    duplicates = {t: assets for t, assets in ticker_groups.items() if len(assets) > 1}
    if not duplicates:
        logger.info("Дубликатов не найдено")
        return 0, 0

    total_dups = sum(len(v) - 1 for v in duplicates.values())
    logger.info(f"Найдено {len(duplicates)} тикеров с дубликатами ({total_dups} лишних)")

    deleted_count = 0
    skipped_count = 0
    to_delete: List[int] = []
    deleted_examples: List[str] = []

    pbar = tqdm(total=len(duplicates), desc="Проверка дубликатов", unit="тикер", leave=False)
    for ticker, assets in duplicates.items():
        assets_sorted = sorted(assets, key=lambda x: x.get("id", 0))
        for dup in assets_sorted[1:]:
            dup_id = dup["id"]
            refs = []
            for tbl, col in [("portfolio_assets", "asset_id"), ("cash_operations", "asset_id"),
                             ("asset_prices", "asset_id"), ("asset_latest_prices", "asset_id")]:
                r = await table_select_async(tbl, "id" if col != "asset_id" else col,
                                             filters={col: dup_id}, limit=1)
                if r:
                    refs.append(tbl)
            if refs:
                skipped_count += 1
            else:
                to_delete.append(dup_id)
                if len(deleted_examples) < MAX_EXAMPLES:
                    deleted_examples.append(f"  {ticker} (id={dup_id})")
        pbar.update(1)
    pbar.close()

    if to_delete:
        batch_size = 100
        for i in range(0, len(to_delete), batch_size):
            batch = to_delete[i:i + batch_size]
            try:
                await table_delete_async("asset_prices", in_filters={"asset_id": batch})
                await table_delete_async("asset_latest_prices", in_filters={"asset_id": batch})
                result = await table_delete_async("assets", in_filters={"id": batch})
                deleted_count += len(result) if result else len(batch)
            except Exception as e:
                logger.error(f"Ошибка удаления дубликатов: {e}")

    logger.info(f"Дубликаты: удалено {deleted_count}, сохранено (используются) {skipped_count}")
    if deleted_examples:
        logger.info(f"Удалённые дубликаты (до {MAX_EXAMPLES}):\n" + "\n".join(deleted_examples))

    return deleted_count, skipped_count


# ---------------------------------------------------------------------------
#  Очистка активов без цен
# ---------------------------------------------------------------------------

async def cleanup_priceless_assets(pre_existing_ids: Optional[set] = None) -> int:
    """
    Удаляет MOEX-активы без ценовых данных.
    Проверяет только активы из pre_existing_ids (если передан) —
    чтобы не удалять свежедобавленные, для которых price worker ещё не отработал.
    """
    logger.info("Очистка активов без ценовых данных...")

    moex_types = [1, 2, 10, 11]
    all_moex = await table_select_async(
        "assets", "id, ticker, name, properties, user_id",
        in_filters={"asset_type_id": moex_types}, limit=None,
    )

    candidates: List[Dict] = []
    for a in all_moex:
        if a.get("user_id") is not None:
            continue
        props = parse_json_properties(a.get("properties"))
        if props.get("source") != "moex":
            continue
        if pre_existing_ids is not None and a["id"] not in pre_existing_ids:
            continue
        candidates.append(a)

    if not candidates:
        return 0

    candidate_ids = [a["id"] for a in candidates]
    id_to_asset = {a["id"]: a for a in candidates}

    has_prices = set()
    batch_size = 500
    for i in range(0, len(candidate_ids), batch_size):
        batch = candidate_ids[i:i + batch_size]
        for tbl in ("asset_prices", "asset_latest_prices"):
            col = "asset_id"
            rows = await table_select_async(tbl, col, in_filters={col: batch}, limit=None)
            if rows:
                for r in rows:
                    has_prices.add(r[col])

    priceless_ids = [aid for aid in candidate_ids if aid not in has_prices]
    if not priceless_ids:
        logger.info("Все активы имеют ценовые данные")
        return 0

    logger.info(f"Найдено {len(priceless_ids)} активов без цен")

    used = set()
    for tbl, col in [("portfolio_assets", "asset_id"), ("cash_operations", "asset_id"),
                     ("cash_operations", "currency")]:
        for i in range(0, len(priceless_ids), batch_size):
            batch = priceless_ids[i:i + batch_size]
            rows = await table_select_async(tbl, col, in_filters={col: batch}, limit=None)
            if rows:
                for r in rows:
                    v = r.get(col)
                    if v:
                        used.add(v)

    for i in range(0, len(priceless_ids), batch_size):
        batch = priceless_ids[i:i + batch_size]
        rows = await table_select_async("assets", "quote_asset_id",
                                        in_filters={"quote_asset_id": batch}, limit=None)
        if rows:
            for r in rows:
                v = r.get("quote_asset_id")
                if v:
                    used.add(v)

    to_delete = [aid for aid in priceless_ids if aid not in used]
    if not to_delete:
        logger.info(f"Все {len(priceless_ids)} активов без цен используются — сохранены")
        return 0

    deleted_examples: List[str] = []
    for aid in to_delete[:MAX_EXAMPLES]:
        a = id_to_asset.get(aid)
        if a:
            deleted_examples.append(f"  {a.get('ticker', '?')} ({a.get('name', '?')}, id={aid})")

    deleted = 0
    pbar = tqdm(total=len(to_delete), desc="Удаление активов без цен", unit="шт", leave=False)
    for i in range(0, len(to_delete), batch_size):
        batch = to_delete[i:i + batch_size]
        try:
            await table_delete_async("asset_payouts", in_filters={"asset_id": batch})
            await table_delete_async("asset_prices", in_filters={"asset_id": batch})
            await table_delete_async("asset_latest_prices", in_filters={"asset_id": batch})
            result = await table_delete_async("assets", in_filters={"id": batch})
            deleted += len(result) if result else len(batch)
        except Exception as e:
            logger.error(f"Ошибка удаления активов без цен: {e}")
        pbar.update(len(batch))
    pbar.close()

    logger.info(
        f"Активы без цен: удалено {deleted}, "
        f"сохранено (используются) {len(priceless_ids) - len(to_delete)}"
    )
    if deleted_examples:
        logger.info(f"Удалённые активы без цен (до {MAX_EXAMPLES}):\n" + "\n".join(deleted_examples))

    return deleted


# ---------------------------------------------------------------------------
#  Главная точка входа
# ---------------------------------------------------------------------------

async def import_moex_assets_async():
    """Импортирует и обновляет активы MOEX."""
    logger.info("=" * 50)
    logger.info("Импорт и обновление активов MOEX")
    logger.info("=" * 50)

    # 1. Дубликаты
    logger.info("--- Этап 1: Удаление дубликатов ---")
    await remove_duplicate_assets()

    # 2. Загрузка существующих активов
    logger.info("--- Этап 2: Загрузка существующих активов из БД ---")
    type_map = {"Акция": 1, "Облигация": 2, "Фонд": 10, "Валюта": 7, "Фьючерс": 11}

    raw = await table_select_async(
        "assets", "id, ticker, asset_type_id, name, properties, user_id, quote_asset_id",
        limit=None,
    )

    existing_assets: Dict = {}
    for a in raw:
        if not a.get("ticker") or a.get("user_id") is not None:
            continue
        ticker = a["ticker"].upper()
        props = parse_json_properties(a.get("properties"))
        if props.get("source") != "moex":
            continue
        entry = {
            "id": a["id"], "ticker": ticker,
            "asset_type_id": a.get("asset_type_id"),
            "name": a.get("name", ""),
            "properties": props,
            "quote_asset_id": a.get("quote_asset_id"),
        }
        if ticker in existing_assets:
            if a["id"] < existing_assets[ticker]["id"]:
                existing_assets[ticker] = entry
        else:
            existing_assets[ticker] = entry

    logger.info(f"Существующих MOEX-активов в БД: {len(existing_assets)}")

    # 3. Загрузка данных из MOEX
    logger.info("--- Этап 3: Загрузка данных из MOEX ---")

    currency_assets = await table_select_async(
        "assets", "id, ticker", filters={"asset_type_id": 7}, limit=None,
    )
    currency_map: Dict = {"RUB": 1, "SUR": 1}
    for c in currency_assets:
        t = c.get("ticker")
        if t:
            currency_map[t.upper()] = c["id"]

    async with create_moex_session() as session:
        # 3.1. Акции — быстрый запрос, обрабатываем первыми
        logger.info("--- Этап 3.1: Загрузка акций ---")
        shares_result = await process_shares(session, existing_assets, type_map, currency_map)

        # 3.2. Облигации — долгая загрузка
        logger.info("--- Этап 3.2: Загрузка облигаций ---")
        bonds_rows, bonds_cols = await fetch_all_bonds(session)
        active_bonds_data = await fetch_active_bonds_currency(session)

        active_bonds_currency = {
            t: d.get("currency") for t, d in active_bonds_data.items() if d.get("currency")
        }

        active_no_prices = {
            t for t, d in active_bonds_data.items() if not d.get("has_prices", True)
        }
        if active_no_prices:
            logger.info(f"Активных облигаций без PREVPRICE: {len(active_no_prices)}, проверяем историю...")

        inactive_bonds_data: Dict = {}
        if bonds_rows and bonds_cols:
            i_SECID = get_column_index(bonds_cols, "secid", "SECID")
            if i_SECID is not None:
                all_tickers = {
                    row[i_SECID].upper().strip()
                    for row in bonds_rows if row[i_SECID]
                }
                inactive_tickers = list(
                    (all_tickers - set(active_bonds_data.keys())) | active_no_prices
                )
                inactive_bonds_data = await fetch_inactive_bonds_currency_batch(
                    session, inactive_tickers,
                )

        inactive_bonds_currency = {
            t: d.get("currency") for t, d in inactive_bonds_data.items() if d.get("currency")
        }
        bonds_currency = {**active_bonds_currency, **inactive_bonds_currency}
        logger.info(f"Валют облигаций загружено: {len(bonds_currency)}")

        # 4. Обработка облигаций
        logger.info("--- Этап 4: Обработка облигаций ---")
        bonds_result = await process_bonds(
            bonds_rows, bonds_cols, existing_assets, type_map, currency_map,
            bonds_currency, active_bonds_data, inactive_bonds_data,
        )

        results = [shares_result, bonds_result]

    # 5. Очистка (только среди активов, которые были в БД до импорта)
    pre_existing_ids = {a["id"] for a in existing_assets.values()}
    logger.info("--- Этап 5: Очистка активов без цен ---")
    await cleanup_priceless_assets(pre_existing_ids)

    # Итоги
    total_inserted = sum(r[0] for r in results)
    total_updated = sum(r[1] for r in results)
    logger.info("=" * 50)
    logger.info(f"ИТОГО: добавлено {total_inserted}, обновлено {total_updated}")
    logger.info("=" * 50)

    return total_inserted, total_updated


if __name__ == "__main__":
    from app.utils.async_runner import run_async
    run_async(import_moex_assets_async())
