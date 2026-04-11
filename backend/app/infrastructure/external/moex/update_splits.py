"""
Синхронизация справочника дроблений и консолидаций с MOEX ISS
/iss/statistics/engines/stock/splits (поля before/after — количество бумаг до и после).
"""
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from app.infrastructure.database.postgres_async import (
    table_insert_async,
    table_select_async,
    table_update_async,
)
from app.infrastructure.external.moex.client import create_moex_session, fetch_json
from app.infrastructure.external.moex.urls import MOEX_STOCK_SPLITS_JSON
from app.infrastructure.external.moex.utils import iss_table
from app.core.reference_logging import get_reference_logger

logger = get_reference_logger("splits")

BATCH_SIZE = 500


def _as_date_field(d) -> Optional[date]:
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str) and len(d) >= 10:
        try:
            return date.fromisoformat(d[:10])
        except ValueError:
            return None
    return None


def _parse_trade_date(raw) -> Optional[date]:
    return _as_date_field(raw)


def _split_pair_key(asset_id: int, trade_date: date) -> Tuple[int, str]:
    return (asset_id, trade_date.isoformat())


def _build_ticker_map(assets: list) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for a in assets:
        if a.get("user_id") is not None:
            continue
        t = (a.get("ticker") or "").strip().upper()
        if t:
            out[t] = int(a["id"])
    return out


def _parse_splits_rows(data: dict) -> List[Tuple[str, date, int, int]]:
    table = iss_table(data, "splits")
    if not table:
        return []
    cols, rows = table
    try:
        i_date = cols.index("tradedate")
        i_sec = cols.index("secid")
        i_before = cols.index("before")
        i_after = cols.index("after")
    except ValueError:
        logger.warning("splits: неожиданная схема колонок %s", cols)
        return []
    out: List[Tuple[str, date, int, int]] = []
    for row in rows:
        if len(row) <= max(i_date, i_sec, i_before, i_after):
            continue
        d = _parse_trade_date(row[i_date])
        secid = row[i_sec]
        if not d or not secid:
            continue
        try:
            before = int(row[i_before])
            after = int(row[i_after])
        except (TypeError, ValueError):
            continue
        if before <= 0 or after <= 0:
            continue
        out.append((str(secid).strip().upper(), d, before, after))
    return out


def _ratios_equal(a, b, c, d) -> bool:
    return float(a) == float(c) and float(b) == float(d)


async def update_splits_from_moex_async() -> int:
    """
    Загружает список сплитов MOEX и синхронизирует asset_splits для глобальных активов.

    Returns:
        Число записей, затронутых вставкой или обновлением.
    """
    assets = await table_select_async("assets", limit=200000)
    ticker_map = _build_ticker_map(assets or [])
    if not ticker_map:
        logger.warning("splits: нет глобальных активов (user_id IS NULL)")
        return 0

    existing_rows = await table_select_async(
        "asset_splits",
        select="asset_id,trade_date,ratio_before,ratio_after",
        limit=500000,
    )
    existing_by_key: Dict[Tuple[int, str], dict] = {}
    for r in existing_rows or []:
        td = _as_date_field(r.get("trade_date"))
        if td is None:
            continue
        existing_by_key[_split_pair_key(int(r["asset_id"]), td)] = r

    async with create_moex_session() as session:
        data = await fetch_json(session, MOEX_STOCK_SPLITS_JSON, max_attempts=3)
    if not data:
        logger.warning("splits: пустой ответ MOEX")
        return 0

    parsed = _parse_splits_rows(data)
    to_insert: List[dict] = []
    updated_count = 0

    for secid, trade_date, before, after in parsed:
        aid = ticker_map.get(secid)
        if aid is None:
            continue
        key = _split_pair_key(aid, trade_date)
        row = {
            "asset_id": aid,
            "trade_date": trade_date,
            "ratio_before": before,
            "ratio_after": after,
        }
        ex = existing_by_key.get(key)
        if ex is None:
            to_insert.append(row)
            continue
        if _ratios_equal(ex["ratio_before"], ex["ratio_after"], before, after):
            continue
        await table_update_async(
            "asset_splits",
            {"ratio_before": before, "ratio_after": after},
            {"asset_id": aid, "trade_date": trade_date},
        )
        updated_count += 1

    inserted_count = 0
    if to_insert:
        for i in range(0, len(to_insert), BATCH_SIZE):
            batch = to_insert[i : i + BATCH_SIZE]
            await table_insert_async("asset_splits", batch)
            inserted_count += len(batch)

    touched = inserted_count + updated_count
    logger.info(
        "splits_done touched=%s inserted=%s updated=%s moex_rows=%s tickers_in_db=%s",
        touched,
        inserted_count,
        updated_count,
        len(parsed),
        len(ticker_map),
    )
    return touched


if __name__ == "__main__":
    from app.config import Config
    from app.core.logging import init_logging
    from app.utils.async_runner import run_async

    init_logging()
    Config.validate()
    run_async(update_splits_from_moex_async())
