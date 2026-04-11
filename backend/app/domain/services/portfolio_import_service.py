"""
Сервис импорта портфеля от брокера.

Стратегия: полная очистка + повторный импорт.
- clear_portfolio_full: удаляет дочерние портфели и все данные, сохраняет родительский
- Для каждого счёта брокера создаётся дочерний портфель с полным набором операций
- Broker connection пересоздаётся на родительском портфеле

Обоснование:
- Брокер ВСЕГДА возвращает полный список операций
- Bottleneck — API брокера (2-10 сек), а не БД
- Устраняет сложную дедупликацию и гарантирует консистентность

Если ISIN/FIGI нет в справочнике — создаётся пользовательский актив (тип «Другое»),
properties заполняются полями из данных брокера.

Переименования тикеров (FIVE → X5 и т.п.): файл data/broker_ticker_aliases.json — ключ: актуальный
тикер в справочнике (как в БД), значение: список старых тикеров с брокера. Путь переопределяется
переменной BROKER_TICKER_ALIASES_FILE.
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import Config
from app.domain.services.user_service import get_user_by_email
from app.infrastructure.database.database_service import (
    rpc_async,
    table_select_async,
    table_insert_async,
    get_connection_pool,
)
from app.infrastructure.database.repositories.operation_repository import OperationRepository
from app.utils.date import (
    normalize_date_to_day_string,
    normalize_date_to_string,
    parse_date,
    normalize_date_to_sql_date,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

_operation_repository = OperationRepository()

# asset_types: «Другое» — кастомные бумаги пользователя (в т.ч. импорт с брокера)
_BROKER_CUSTOM_ASSET_TYPE_ID = 11


def _norm_isin(v: Any) -> Optional[str]:
    if v is None or not str(v).strip():
        return None
    return str(v).strip().upper()


def _norm_figi(v: Any) -> Optional[str]:
    if v is None or not str(v).strip():
        return None
    return str(v).strip()


def _norm_broker_ticker(v: Any) -> Optional[str]:
    if v is None or not str(v).strip():
        return None
    return str(v).strip().upper()


def _ticker_alias_tokens_from_asset(asset: dict) -> List[str]:
    """Только основной тикер актива в справочнике. Исторические тикеры — из data/broker_ticker_aliases.json."""
    out: List[str] = []
    t = _norm_broker_ticker(asset.get("ticker"))
    if t:
        out.append(t)
    return out


def _parse_legacy_ticker_aliases_file_payload(raw: Any) -> Dict[str, List[str]]:
    """
    JSON: { "X5": ["FIVE"], "FIXR": ["FIXP", "OLD"] } — актуальный тикер → список бывших.
    """
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, List[str]] = {}
    for k, v in raw.items():
        ck = _norm_broker_ticker(k)
        if not ck:
            continue
        legacy: List[str] = []
        if isinstance(v, (list, tuple)):
            for x in v:
                t = _norm_broker_ticker(x)
                if t and t not in legacy:
                    legacy.append(t)
        elif isinstance(v, str) and v.strip():
            t = _norm_broker_ticker(v)
            if t:
                legacy.append(t)
        if legacy:
            out[ck] = legacy
    return out


def _load_legacy_ticker_aliases_file(path: Optional[str] = None) -> Dict[str, List[str]]:
    p = Path(path or Config.BROKER_TICKER_ALIASES_FILE)
    if not p.is_file():
        return {}
    try:
        text = p.read_text(encoding="utf-8")
        raw = json.loads(text)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Импорт: не удалось прочитать файл алиасов тикеров %s: %s", p, e)
        return {}
    return _parse_legacy_ticker_aliases_file_payload(raw)


def _apply_legacy_ticker_aliases_file(
    broker_ticker_to_asset: Dict[str, int],
    canonical_to_legacy: Dict[str, List[str]],
) -> None:
    """Старые тикеры указывают на тот же asset_id, что и актуальный тикер из справочника."""
    applied_groups = 0
    for canonical, legacy_list in canonical_to_legacy.items():
        aid = broker_ticker_to_asset.get(canonical)
        if aid is None:
            logger.warning(
                "Импорт: в файле алиасов указан тикер «%s», но актив с таким тикером нет в справочнике — строка пропущена",
                canonical,
            )
            continue
        for leg in legacy_list:
            if leg == canonical:
                continue
            broker_ticker_to_asset[leg] = aid
        applied_groups += 1
    if applied_groups:
        logger.info(
            "Импорт: применён файл алиасов тикеров (%s групп из %s в файле)",
            applied_groups,
            len(canonical_to_legacy),
        )


def _register_broker_ticker_aliases(asset: dict, broker_ticker_to_asset: Dict[str, int]) -> None:
    """Валютные активы (asset_type_id=7) не трогаем — иначе пересечение с USD/EUR."""
    if asset.get("asset_type_id") == 7:
        return
    aid = int(asset["id"])
    for t in _ticker_alias_tokens_from_asset(asset):
        broker_ticker_to_asset.setdefault(t, aid)


def _register_new_asset_ticker_aliases(
    aid: int,
    ticker: str,
    properties: Optional[dict],
    broker_ticker_to_asset: Dict[str, int],
) -> None:
    pseudo = {
        "id": aid,
        "ticker": ticker,
        "properties": properties or {},
        "asset_type_id": _BROKER_CUSTOM_ASSET_TYPE_ID,
    }
    _register_broker_ticker_aliases(pseudo, broker_ticker_to_asset)


def _broker_position_is_cash(pos: dict) -> bool:
    ticker = (pos.get("ticker") or "").upper()
    name = (pos.get("name") or "").lower()
    return ticker.startswith("RUB") or ticker.startswith("RUR") or "рубль" in name


def _merge_instrument_meta(target: dict, src: dict) -> None:
    for k, v in src.items():
        if v is None or v == "":
            continue
        prev = target.get(k)
        if prev in (None, ""):
            target[k] = v
        elif k == "name" and isinstance(v, str) and isinstance(prev, str) and len(v) > len(prev):
            target[k] = v


def _instrument_merge_key(isin: Optional[str], figi: Optional[str]) -> Optional[str]:
    if isin:
        return f"isin:{isin}"
    if figi:
        return f"figi:{figi}"
    return None


def _canonical_merge_key_for_broker_row(
    isin: Optional[str],
    figi: Optional[str],
    ticker: Optional[str],
    broker_ticker_to_asset: Dict[str, int],
    assets_by_id: Dict[int, dict],
) -> Optional[str]:
    """
    Ключ слияния инструментов: ISIN/FIGI; иначе тикер → актив из справочника → его ISIN/FIGI;
    иначе стабильный ключ по asset_id (редко, если в БД нет ISIN).
    """
    ni = _norm_isin(isin)
    nf = _norm_figi(figi)
    base = _instrument_merge_key(ni, nf)
    if base:
        return base
    nt = _norm_broker_ticker(ticker)
    if not nt or nt not in broker_ticker_to_asset:
        return None
    aid = broker_ticker_to_asset[nt]
    a = assets_by_id.get(aid)
    if not a:
        return f"asset_id:{aid}"
    props = a.get("properties") or {}
    isin2 = _norm_isin(props.get("isin"))
    figi2 = _norm_figi(props.get("figi"))
    return _instrument_merge_key(isin2, figi2) or f"asset_id:{aid}"


def collect_broker_instruments(
    broker_data: dict,
    broker_ticker_to_asset: Optional[Dict[str, int]] = None,
    assets_by_id: Optional[Dict[int, dict]] = None,
) -> List[dict]:
    """Уникальные инструменты из позиций и транзакций (без валютных остатков)."""
    bmap = broker_ticker_to_asset or {}
    amap = assets_by_id or {}
    merged: Dict[str, dict] = {}
    for pdata in broker_data.values():
        for pos in pdata.get("positions") or []:
            if _broker_position_is_cash(pos):
                continue
            isin = _norm_isin(pos.get("isin"))
            figi = _norm_figi(pos.get("figi"))
            key = _canonical_merge_key_for_broker_row(
                isin, figi, pos.get("ticker"), bmap, amap,
            )
            if not key:
                continue
            if key not in merged:
                merged[key] = {}
            _merge_instrument_meta(merged[key], pos)
            if isin:
                merged[key]["isin"] = isin
            if figi:
                merged[key]["figi"] = figi

        for tx in pdata.get("transactions") or []:
            isin = _norm_isin(tx.get("isin"))
            figi = _norm_figi(tx.get("figi"))
            key = _canonical_merge_key_for_broker_row(
                isin, figi, tx.get("ticker"), bmap, amap,
            )
            if not key:
                continue
            if key not in merged:
                merged[key] = {}
            _merge_instrument_meta(merged[key], tx)
            if isin:
                merged[key]["isin"] = isin
            if figi:
                merged[key]["figi"] = figi

    return list(merged.values())


def _fmt_currency_code(cur: Any) -> str:
    if cur is None:
        return ""
    if hasattr(cur, "name"):
        return str(cur.name).lower().strip()
    return str(cur).lower().strip()


def _build_ticker_to_quote_asset_id(all_assets: List[dict]) -> Dict[str, int]:
    """Тикеры валют (user_id IS NULL) → id актива для quote_asset_id."""
    out: Dict[str, int] = {}
    for a in all_assets or []:
        if a.get("user_id") is not None:
            continue
        tid = a.get("asset_type_id")
        if tid != 7:
            continue
        t = (a.get("ticker") or "").upper().strip()
        if t:
            out[t] = int(a["id"])
    if "RUB" not in out:
        out["RUB"] = 1
    return out


def _quote_asset_id_for_broker_instrument(meta: dict, ticker_to_quote: Dict[str, int]) -> int:
    cur = _fmt_currency_code(meta.get("currency"))
    if cur in ("rub", "rur", ""):
        return 1
    code = cur.upper()[:8] if cur else ""
    if code and code in ticker_to_quote:
        return int(ticker_to_quote[code])
    aliases = {"usd": "USD", "eur": "EUR", "gbp": "GBP", "cny": "CNY", "hkd": "HKD", "chf": "CHF"}
    if cur in aliases and aliases[cur] in ticker_to_quote:
        return int(ticker_to_quote[aliases[cur]])
    return 1


def _sanitize_asset_ticker(ticker: Optional[str], isin: Optional[str], figi: Optional[str]) -> str:
    raw = (ticker or "").strip().upper()
    if raw:
        raw = re.sub(r"[^\w\.\-]", "_", raw, flags=re.UNICODE)
        raw = raw[:48] if len(raw) > 48 else raw
        return raw or "UNK"
    if isin:
        return f"I_{isin.replace('-', '')[:10]}"
    if figi:
        return f"F_{figi[-8:]}"
    return "BROKER_UNK"


def resolve_broker_asset_id(
    isin: Optional[str],
    figi: Optional[str],
    ticker: Optional[str],
    isin_to_asset: Dict[str, int],
    figi_to_asset: Dict[str, int],
    broker_ticker_to_asset: Dict[str, int],
) -> Optional[int]:
    ni = _norm_isin(isin)
    nf = _norm_figi(figi)
    if ni and ni in isin_to_asset:
        return isin_to_asset[ni]
    if nf and nf in figi_to_asset:
        return figi_to_asset[nf]
    nt = _norm_broker_ticker(ticker)
    if nt and nt in broker_ticker_to_asset:
        return broker_ticker_to_asset[nt]
    return None


async def _load_reference_data_for_import(user_id):
    """
    Справочники для импорта: ISIN/FIGI только по глобальным активам и активам текущего пользователя
    (чужие user_id не подмешиваются).
    """
    op_types_task = table_select_async("operations_type", select="id, name")
    all_assets_task = rpc_async("get_all_assets", {})

    op_types, all_assets = await asyncio.gather(op_types_task, all_assets_task)

    op_type_map = {o["name"].lower(): o["id"] for o in (op_types or [])}

    isin_to_asset: Dict[str, int] = {}
    figi_to_asset: Dict[str, int] = {}
    broker_ticker_to_asset: Dict[str, int] = {}
    currency_assets_map: Dict[int, int] = {}

    def _register_asset_maps(asset: dict) -> None:
        props = asset.get("properties") or {}
        aid = int(asset["id"])
        isin = _norm_isin(props.get("isin"))
        if isin and isin not in isin_to_asset:
            isin_to_asset[isin] = aid
        figi = _norm_figi(props.get("figi"))
        if figi and figi not in figi_to_asset:
            figi_to_asset[figi] = aid
        quote_id = asset.get("quote_asset_id")
        if quote_id and quote_id != 1:
            currency_assets_map[aid] = int(quote_id)

    for asset in all_assets or []:
        if asset.get("user_id") is not None:
            continue
        _register_asset_maps(asset)
        _register_broker_ticker_aliases(asset, broker_ticker_to_asset)

    for asset in all_assets or []:
        uid = asset.get("user_id")
        if uid != user_id:
            continue
        _register_asset_maps(asset)
        _register_broker_ticker_aliases(asset, broker_ticker_to_asset)

    file_map = _load_legacy_ticker_aliases_file()
    if file_map:
        _apply_legacy_ticker_aliases_file(broker_ticker_to_asset, file_map)

    return (
        op_type_map,
        all_assets,
        isin_to_asset,
        figi_to_asset,
        broker_ticker_to_asset,
        currency_assets_map,
    )


def _register_broker_ticker_tokens_from_meta(
    aid: int,
    meta: dict,
    broker_ticker_to_asset: Dict[str, int],
) -> None:
    t = _norm_broker_ticker(meta.get("ticker"))
    if t:
        broker_ticker_to_asset.setdefault(t, aid)


async def _ensure_user_broker_assets(
    user_id,
    instruments: List[dict],
    isin_to_asset: Dict[str, int],
    figi_to_asset: Dict[str, int],
    broker_ticker_to_asset: Dict[str, int],
    currency_assets_map: Dict[int, int],
    ticker_to_quote: Dict[str, int],
) -> None:
    if not instruments:
        return

    pool = await get_connection_pool()
    async with pool.acquire() as conn:
        for meta in instruments:
            isin = _norm_isin(meta.get("isin"))
            figi = _norm_figi(meta.get("figi"))
            if resolve_broker_asset_id(
                isin, figi, meta.get("ticker"), isin_to_asset, figi_to_asset, broker_ticker_to_asset,
            ) is not None:
                continue

            row = None
            existing_id: Optional[int] = None
            if isin:
                row = await conn.fetchrow(
                    "SELECT id, quote_asset_id FROM assets WHERE user_id = $1 AND properties->>'isin' = $2 LIMIT 1",
                    user_id,
                    isin,
                )
                if row:
                    existing_id = int(row["id"])
            if existing_id is None and figi:
                row = await conn.fetchrow(
                    "SELECT id, quote_asset_id FROM assets WHERE user_id = $1 AND properties->>'figi' = $2 LIMIT 1",
                    user_id,
                    figi,
                )
                if row:
                    existing_id = int(row["id"])

            if existing_id is not None:
                q = int(row["quote_asset_id"]) if row else 1
                if isin:
                    isin_to_asset[isin] = existing_id
                if figi:
                    figi_to_asset[figi] = existing_id
                if q != 1:
                    currency_assets_map[existing_id] = q
                logger.info(
                    "Импорт: найден существующий пользовательский актив id=%s isin=%s figi=%s",
                    existing_id,
                    isin,
                    figi,
                )
                _register_broker_ticker_tokens_from_meta(existing_id, meta, broker_ticker_to_asset)
                continue

            name = (meta.get("name") or "").strip() or None
            ticker_base = _sanitize_asset_ticker(meta.get("ticker"), isin, figi)
            ticker = ticker_base
            clash = await conn.fetchrow(
                "SELECT id, properties FROM assets WHERE user_id = $1 AND UPPER(ticker) = UPPER($2) LIMIT 1",
                user_id,
                ticker,
            )
            if clash:
                p = clash["properties"] or {}
                same = (isin and _norm_isin(p.get("isin")) == isin) or (
                    figi and _norm_figi(p.get("figi")) == figi
                )
                if same:
                    aid = int(clash["id"])
                    rowq = await conn.fetchrow("SELECT quote_asset_id FROM assets WHERE id = $1", aid)
                    q = int(rowq["quote_asset_id"]) if rowq else 1
                    if isin:
                        isin_to_asset[isin] = aid
                    if figi:
                        figi_to_asset[figi] = aid
                    if q != 1:
                        currency_assets_map[aid] = q
                    _register_broker_ticker_tokens_from_meta(aid, meta, broker_ticker_to_asset)
                    continue
                suffix = (isin or figi or "X")[-6:].replace("-", "")
                ticker = f"{ticker_base[:34]}_{suffix}"[:48]

            quote_id = _quote_asset_id_for_broker_instrument(meta, ticker_to_quote)
            props: Dict[str, Any] = {"source": "broker_import"}
            _skip_props = frozenset({
                "payment", "date", "type", "price", "quantity",
                "average_price", "current_price",
                "tinkoff_operation_type",
            })
            for k, v in meta.items():
                if v is None or k in _skip_props:
                    continue
                if isinstance(v, (str, int, float, bool)):
                    props[k] = v
                elif hasattr(v, "name"):
                    props[k] = str(v.name)
            if isin:
                props["isin"] = isin
            if figi:
                props["figi"] = figi

            insert_row = {
                "asset_type_id": _BROKER_CUSTOM_ASSET_TYPE_ID,
                "user_id": user_id,
                "name": (name or ticker)[:512],
                "ticker": ticker[:64],
                "properties": props,
                "quote_asset_id": quote_id,
            }
            created = await table_insert_async("assets", insert_row)
            if not created:
                logger.error("Импорт: не удалось создать актив брокера meta=%s", meta)
                continue
            aid = int(created[0]["id"])
            if isin:
                isin_to_asset[isin] = aid
            if figi:
                figi_to_asset[figi] = aid
            if quote_id != 1:
                currency_assets_map[aid] = quote_id
            _register_new_asset_ticker_aliases(aid, ticker, props, broker_ticker_to_asset)
            _register_broker_ticker_tokens_from_meta(aid, meta, broker_ticker_to_asset)
            logger.info(
                "Импорт: создан пользовательский актив id=%s ticker=%s isin=%s (quote_asset_id=%s)",
                aid,
                ticker,
                isin,
                quote_id,
            )


async def _load_currency_rates(currency_assets_map: dict):
    """Загружает курсы валют одним запросом."""
    currency_asset_ids = list(set(currency_assets_map.values()))
    if not currency_asset_ids:
        return {}

    currency_rates = {}
    pool = await get_connection_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT asset_id, trade_date, price
            FROM asset_prices
            WHERE asset_id = ANY($1::bigint[])
            ORDER BY asset_id, trade_date DESC
            """,
            currency_asset_ids,
        )
        for row in rows:
            aid = row["asset_id"]
            if aid not in currency_rates:
                currency_rates[aid] = {}
            currency_rates[aid][str(row["trade_date"])] = float(row["price"])

    latest_prices = await table_select_async(
        "asset_latest_prices",
        select="asset_id, curr_price",
        in_filters={"asset_id": currency_asset_ids},
        limit=None,
    )
    today_str = datetime.utcnow().date().isoformat()
    for lp in (latest_prices or []):
        cid = lp.get("asset_id")
        if cid not in currency_rates:
            currency_rates[cid] = {}
        if today_str not in currency_rates[cid]:
            currency_rates[cid][today_str] = float(lp.get("curr_price") or 1)

    logger.info(f"Загружено курсов для {len(currency_rates)} валют (1 batch-запрос)")
    return currency_rates


def _find_currency_rate(currency_rates: dict, quote_asset_id: int, date_str: str):
    """Находит ближайший курс валюты не позднее указанной даты."""
    rates = currency_rates.get(quote_asset_id)
    if not rates:
        return None
    for date_key in sorted(rates.keys(), reverse=True):
        if date_key <= date_str:
            return rates[date_key]
    return None


def _convert_price_payment_to_rub_if_needed(
    asset_id: Optional[int],
    currency_assets_map: Dict[int, int],
    currency_rates: dict,
    tx_date: Any,
    price: float,
    payment: float,
) -> Tuple[float, float]:
    """
    Для активов с валютной котировкой (не RUB) пересчитывает цену и payment в рубли по курсу на дату.
    """
    if not asset_id or asset_id not in currency_assets_map:
        return price, payment
    quote_asset_id = currency_assets_map[asset_id]
    tx_date_obj = parse_date(tx_date)
    if not tx_date_obj:
        return price, payment
    date_str = (
        tx_date_obj.date() if isinstance(tx_date_obj, datetime) else tx_date_obj
    ).isoformat()
    rate = _find_currency_rate(currency_rates, quote_asset_id, date_str)
    if not rate or rate <= 0:
        return price, payment
    # payment в рублях с полной точностью (как у API nano), иначе сумма по многим операциям
    # расходится с остатком кэша в позициях на десятки копеек.
    return round(price / rate, 6), round(payment / rate, 6)


async def _asset_ids_that_exist(asset_ids: List[int]) -> set[int]:
    """Проверка, что id есть в assets (защита от гонок и устаревших id в картах)."""
    if not asset_ids:
        return set()
    pool = await get_connection_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id FROM assets WHERE id = ANY($1::bigint[])",
            asset_ids,
        )
    return {int(r["id"]) for r in rows}


async def import_broker_portfolio(
    email: str,
    parent_portfolio_id: int,
    broker_data: dict,
    broker_id: int,
    clear_before_import: bool = False,
    api_key: str = "",
):
    user = await get_user_by_email(email)
    if not user:
        raise ValueError(f"Пользователь с email {email} не найден")
    user_id = user["id"]

    # ======================================================================
    # Сначала очистка: clear_portfolio_full удаляет неиспользуемые кастомные
    # активы (см. database/clear_portfolio_full.sql). Справочники isin/figi/
    # ticker → asset_id нужно строить ПОСЛЕ очистки, иначе в памяти остаются
    # id уже удалённых строк assets → FK при batch_create_portfolio_assets.
    # ======================================================================
    try:
        await rpc_async("clear_portfolio_full", {"p_portfolio_id": parent_portfolio_id})
        logger.info(f"Очистка портфеля {parent_portfolio_id} завершена")
    except Exception as e:
        logger.error(f"Ошибка при очистке портфеля: {e}", exc_info=True)
        raise

    (
        op_type_map,
        all_assets,
        isin_to_asset,
        figi_to_asset,
        broker_ticker_to_asset,
        currency_assets_map,
    ) = await _load_reference_data_for_import(user_id)
    assets_by_id: Dict[int, dict] = {int(a["id"]): a for a in (all_assets or [])}

    instruments = collect_broker_instruments(broker_data, broker_ticker_to_asset, assets_by_id)
    ticker_to_quote = _build_ticker_to_quote_asset_id(all_assets)
    await _ensure_user_broker_assets(
        user_id,
        instruments,
        isin_to_asset,
        figi_to_asset,
        broker_ticker_to_asset,
        currency_assets_map,
        ticker_to_quote,
    )
    currency_rates = await _load_currency_rates(currency_assets_map)

    imported_portfolio_ids = []

    for portfolio_name, pdata in broker_data.items():
        logger.info(f"Импортируем портфель '{portfolio_name}'")

        # ==================================================================
        # Создаём дочерний портфель
        # ==================================================================
        child = await table_insert_async("portfolios", {
            "user_id": user_id,
            "parent_portfolio_id": parent_portfolio_id,
            "name": portfolio_name,
        })
        if not child:
            logger.error(f"Не удалось создать дочерний портфель '{portfolio_name}'")
            continue
        portfolio_id = child[0]["id"]

        # ==================================================================
        # Собираем нужные asset_id из брокерских данных
        # ==================================================================
        needed_asset_ids = set()
        broker_positions_map = {}
        if "positions" in pdata:
            for pos in pdata["positions"]:
                if _broker_position_is_cash(pos):
                    continue
                aid = resolve_broker_asset_id(
                    pos.get("isin"),
                    pos.get("figi"),
                    pos.get("ticker"),
                    isin_to_asset,
                    figi_to_asset,
                    broker_ticker_to_asset,
                )
                if aid:
                    needed_asset_ids.add(aid)
                    broker_positions_map[aid] = {
                        "quantity": float(pos.get("quantity", 0)),
                        "average_price": float(pos.get("average_price", 0)),
                    }

        sorted_transactions = sorted(
            pdata["transactions"],
            key=lambda x: (x.get("date", ""), x.get("type", "")),
        )

        for tx in sorted_transactions:
            aid = resolve_broker_asset_id(
                tx.get("isin"),
                tx.get("figi"),
                tx.get("ticker"),
                isin_to_asset,
                figi_to_asset,
                broker_ticker_to_asset,
            )
            if aid:
                needed_asset_ids.add(aid)

        # ==================================================================
        # Batch создание portfolio_assets
        # ==================================================================
        pa_map = {}
        if needed_asset_ids:
            existing_aids = await _asset_ids_that_exist(list(needed_asset_ids))
            phantom = needed_asset_ids - existing_aids
            if phantom:
                logger.error(
                    "Импорт: resolve вернул asset_id, которых нет в таблице assets: %s. "
                    "Они исключены из batch_create_portfolio_assets.",
                    sorted(phantom),
                )
            needed_asset_ids = needed_asset_ids & existing_aids
        if needed_asset_ids:
            new_pa = await rpc_async("batch_create_portfolio_assets", {
                "p_portfolio_id": portfolio_id,
                "p_asset_ids": list(needed_asset_ids),
            })
            if new_pa and isinstance(new_pa, dict):
                for asset_id_str, pa_id in new_pa.items():
                    pa_map[int(asset_id_str)] = int(pa_id)
            logger.debug(f"Создано {len(needed_asset_ids)} portfolio_assets")

        # ==================================================================
        # Обработка транзакций и операций
        # Дедупликация не нужна: портфель чистый после clear_portfolio_full
        # ==================================================================
        new_tx = []
        new_ops = []

        for tx in sorted_transactions:
            tx_type = tx["type"]
            tx_date = tx["date"]
            isin = tx.get("isin")
            payment = float(tx.get("payment") or 0)
            asset_id = resolve_broker_asset_id(
                isin,
                tx.get("figi"),
                tx.get("ticker"),
                isin_to_asset,
                figi_to_asset,
                broker_ticker_to_asset,
            )

            if tx_type in ("Buy", "Sell", "Amortization"):
                if not asset_id:
                    if tx_type == "Buy":
                        logger.warning(
                            "Импорт: пропуск покупки — нет ISIN/FIGI/тикера в справочнике "
                            f"(isin={isin!r}, figi={tx.get('figi')!r}, ticker={tx.get('ticker')!r}, "
                            f"date={tx_date}). Старые тикеры задайте в data/broker_ticker_aliases.json."
                        )
                    continue

                pa_id = pa_map.get(asset_id)
                if not pa_id:
                    if tx_type == "Buy":
                        logger.warning(
                            "Импорт: пропуск покупки — нет portfolio_asset "
                            f"(asset_id={asset_id}, date={tx_date})."
                        )
                    continue

                tx_date_normalized = normalize_date_to_string(tx_date, include_time=True)
                if not tx_date_normalized:
                    tx_date_normalized = normalize_date_to_day_string(tx_date)
                    if not tx_date_normalized:
                        continue

                if tx_type == "Amortization":
                    op_quantity = float(tx.get("quantity") or 0)

                    if op_quantity <= 0:
                        tx_date_sql = normalize_date_to_sql_date(tx_date_normalized) or ""
                        calculated_qty = _calculate_amortization_quantity(
                            pa_id, tx_date_sql, new_tx, broker_positions_map, asset_id,
                        )
                        if calculated_qty <= 0:
                            logger.warning(f"Amortization: qty=0, пропускаем: {tx}")
                            continue
                        op_quantity = calculated_qty

                    price = round(payment / op_quantity, 6) if op_quantity > 0 else 0.0
                    qty = round(op_quantity, 6)
                else:
                    price = round(float(tx.get("price") or 0), 6)
                    qty = round(float(tx.get("quantity") or 0), 6)

                currency_id_for_tx = 1
                comm_val = float(tx.get("commission") or 0)
                comm_rub = None
                if asset_id in currency_assets_map:
                    currency_id_for_tx = currency_assets_map[asset_id]
                    price, payment = _convert_price_payment_to_rub_if_needed(
                        asset_id, currency_assets_map, currency_rates, tx_date, price, payment,
                    )
                    if abs(comm_val) >= 1e-12:
                        _, comm_val = _convert_price_payment_to_rub_if_needed(
                            asset_id, currency_assets_map, currency_rates, tx_date, 0.0, comm_val,
                        )
                        comm_rub = round(comm_val, 6)
                elif abs(comm_val) >= 1e-12:
                    comm_rub = round(comm_val, 6)

                tx_type_id = {"Buy": 1, "Sell": 2, "Amortization": 3}[tx_type]

                tx_row = {
                    "portfolio_id": portfolio_id,
                    "portfolio_asset_id": pa_id,
                    "transaction_type": tx_type_id,
                    "price": price,
                    "quantity": qty,
                    "payment": payment,
                    "currency_id": currency_id_for_tx,
                    "transaction_date": tx_date_normalized,
                    "user_id": user_id,
                }
                if abs(comm_val) >= 1e-12:
                    tx_row["commission"] = comm_val
                if comm_rub is not None:
                    tx_row["commission_rub"] = comm_rub
                new_tx.append(tx_row)
            else:
                # Cash operations: Dividend, Coupon, Commission, Tax, Deposit, Withdraw
                if abs(payment) < 1e-8:
                    continue

                op_type_id = op_type_map.get(tx_type.lower())
                if not op_type_id:
                    continue

                op_date_normalized = normalize_date_to_string(tx_date, include_time=True)
                if not op_date_normalized:
                    op_date_normalized = normalize_date_to_day_string(tx_date)
                    if not op_date_normalized:
                        continue

                currency_id_for_op = 1
                comm_cash = float(tx.get("commission") or 0)
                comm_cash_rub = None
                if op_type_id not in (5, 6) and asset_id and asset_id in currency_assets_map:
                    currency_id_for_op = currency_assets_map[asset_id]
                    _, payment = _convert_price_payment_to_rub_if_needed(
                        asset_id, currency_assets_map, currency_rates, tx_date, 0.0, payment,
                    )
                    if abs(comm_cash) >= 1e-12:
                        _, comm_cash = _convert_price_payment_to_rub_if_needed(
                            asset_id, currency_assets_map, currency_rates, tx_date, 0.0, comm_cash,
                        )
                        comm_cash_rub = round(comm_cash, 6)
                elif abs(comm_cash) >= 1e-12:
                    comm_cash_rub = round(comm_cash, 6)

                pa_id_for_op = pa_map.get(asset_id) if asset_id else None

                op_row = {
                    "user_id": user_id,
                    "portfolio_id": portfolio_id,
                    "type": op_type_id,
                    "amount": payment,
                    "currency": currency_id_for_op,
                    "date": tx_date,
                    "asset_id": asset_id,
                    "portfolio_asset_id": pa_id_for_op,
                    "transaction_id": None,
                }
                if abs(comm_cash) >= 1e-12:
                    op_row["commission"] = comm_cash
                if comm_cash_rub is not None:
                    op_row["commission_rub"] = comm_cash_rub
                new_ops.append(op_row)

        # ==================================================================
        # Отправляем в БД одним батчем
        # ==================================================================
        if new_tx or new_ops:
            operations_batch = _build_operations_batch(new_tx, new_ops, op_type_map)
            operations_batch.sort(key=lambda x: parse_date(
                x.get("operation_date") or x.get("date") or ""
            ) or datetime.min)

            try:
                result = await _operation_repository.apply_operations_batch(operations_batch)
                inserted = (result or {}).get("inserted_count", 0)
                failed = (result or {}).get("failed_count", 0)
                logger.info(
                    f"Портфель '{portfolio_name}': batch insert — "
                    f"inserted={inserted}, failed={failed}"
                )
                if failed > 0:
                    for f_op in (result or {}).get("failed_operations", []):
                        logger.warning(f"  failed: {f_op.get('error', '?')}")
            except Exception as e:
                logger.error(f"Ошибка при apply_operations_batch: {e}", exc_info=True)
        else:
            logger.info(f"Портфель '{portfolio_name}': операций нет")

        imported_portfolio_ids.append(portfolio_id)

    # ======================================================================
    # Broker connection — только на родительский портфель
    # ======================================================================
    if imported_portfolio_ids:
        from app.domain.services.broker_connections_service import upsert_broker_connection

        await upsert_broker_connection(
            user_id, broker_id, parent_portfolio_id, api_key,
        )

    return {"success": True, "imported_portfolio_ids": imported_portfolio_ids}


def _calculate_amortization_quantity(
    pa_id, tx_date_sql, new_tx_list, broker_positions_map, asset_id,
):
    """Рассчитывает количество бумаг для амортизации на дату по списку новых транзакций."""
    calculated_qty = 0.0

    for ntx in new_tx_list:
        if ntx["portfolio_asset_id"] != pa_id:
            continue
        ntx_date = normalize_date_to_sql_date(ntx.get("transaction_date", "")) or ""
        if ntx_date < tx_date_sql:
            ntx_type = ntx.get("transaction_type")
            ntx_qty = ntx.get("quantity", 0)
            if ntx_type == 1:
                calculated_qty += ntx_qty
            elif ntx_type in (2, 3):
                calculated_qty -= ntx_qty

    if calculated_qty <= 0 and asset_id in broker_positions_map:
        broker_qty = broker_positions_map[asset_id].get("quantity", 0)
        if broker_qty > 0:
            calculated_qty = broker_qty

    return calculated_qty


def _build_operations_batch(new_tx: list, new_ops: list, op_type_map: dict) -> list:
    """Формирует единый массив операций для apply_operations_batch."""
    batch = []

    for tx in new_tx:
        tx_type_id = tx.get("transaction_type")
        op_type_id = op_type_map.get(
            "buy" if tx_type_id == 1 else ("sell" if tx_type_id == 2 else "amortization")
        )
        if not op_type_id:
            continue
        op_date = normalize_date_to_string(tx.get("transaction_date"), include_time=True) or ""
        tx_payload = {
            "user_id": str(tx["user_id"]),
            "portfolio_id": tx["portfolio_id"],
            "operation_type": op_type_id,
            "operation_date": op_date,
            "portfolio_asset_id": tx["portfolio_asset_id"],
            "quantity": float(tx["quantity"]),
            "price": float(tx["price"]),
            "payment": float(tx.get("payment") or 0),
            "amount": float(tx.get("payment") or 0),
            "currency_id": tx.get("currency_id"),
        }
        if tx.get("commission") is not None and abs(float(tx.get("commission") or 0)) >= 1e-12:
            tx_payload["commission"] = float(tx["commission"])
        if tx.get("commission_rub") is not None:
            tx_payload["commission_rub"] = float(tx["commission_rub"])
        batch.append(tx_payload)

    for op in new_ops:
        op_date = normalize_date_to_string(op["date"], include_time=True) or ""
        op_payload = {
            "user_id": str(op["user_id"]),
            "portfolio_id": op["portfolio_id"],
            "operation_type": op["type"],
            "amount": float(op["amount"]),
            "currency_id": op.get("currency", 1),
            "operation_date": op_date,
            "asset_id": op.get("asset_id"),
            "portfolio_asset_id": op.get("portfolio_asset_id"),
        }
        if op.get("commission") is not None and abs(float(op.get("commission") or 0)) >= 1e-12:
            op_payload["commission"] = float(op["commission"])
        if op.get("commission_rub") is not None:
            op_payload["commission_rub"] = float(op["commission_rub"])
        batch.append(op_payload)

    return batch
