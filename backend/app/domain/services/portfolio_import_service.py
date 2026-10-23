"""
Сервис импорта портфеля от брокера.

Стратегия: очистка брокерских записей + повторный импорт.
- clear_broker_portfolio_data: удаляет только то, что пришло от брокера (source <> 'manual');
  ручные сделки и операции пользователя, дочерние портфели и их настройки остаются
- Каждый счёт брокера — дочерний портфель, привязанный по broker_account_id
  (пользователь может переименовать его — привязка сохранится)
- Операции брокера, которые пользователь удалил или изменил, запоминаются
  (broker_operation_suppressions, триггер в broker_sync_tracking.sql) и не возвращаются
- Операция брокера, которую пользователь уже добавил вручную, второй раз не пишется
- Broker connection пересоздаётся на родительском портфеле
- Очистка и запись идут в одной транзакции под advisory-lock родительского портфеля:
  любая ошибка откатывает всё, и у пользователя остаются прежние данные

Обоснование:
- Брокер ВСЕГДА возвращает полный список операций
- Bottleneck — API брокера (2-10 сек), а не БД

Если ISIN/FIGI нет в справочнике — создаётся пользовательский актив (тип «Другое»),
properties заполняются полями из данных брокера.

Переименования тикеров (FIVE → X5 и т.п.): файл data/broker_ticker_aliases.json — ключ: актуальный
тикер в справочнике (как в БД), значение: список старых тикеров с брокера. Путь переопределяется
переменной BROKER_TICKER_ALIASES_FILE.
"""
import hashlib
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
    table_update_async,
    acquire_connection,
    db_transaction,
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

# Частичное погашение номинала (амортизация) — денежная выплата, бумаги остаются у инвестора.
# Полное погашение (BOND_REPAYMENT_FULL, DFA_REDEMPTION) списывает бумаги (транзакция Redemption).
_PARTIAL_AMORTIZATION_BROKER_TYPES = frozenset({"OPERATION_TYPE_BOND_REPAYMENT"})

# Сколько неудачных операций сохранять в результате задачи (для показа пользователю)
_FAILED_OPERATIONS_REPORT_LIMIT = 50


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
    # Последовательно: внутри db_transaction у всех запросов одно соединение
    op_types = await table_select_async("operations_type", select="id, name")
    all_assets = await rpc_async("get_all_assets", {})

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

    async with acquire_connection() as conn:
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
                "average_price", "average_price_currency", "current_price",
                "tinkoff_operation_type", "transfer",
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
    async with acquire_connection() as conn:
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


def _quote_code_by_asset_id(ticker_to_quote: Dict[str, int]) -> Dict[int, str]:
    """id валютного актива → код валюты в нижнем регистре (как отдаёт брокер: 'usd')."""
    return {int(aid): code.lower() for code, aid in ticker_to_quote.items()}


def _rate_on_date(currency_rates: dict, quote_asset_id: int, tx_date: Any) -> Optional[float]:
    tx_date_obj = parse_date(tx_date)
    if not tx_date_obj:
        return None
    date_str = (
        tx_date_obj.date() if isinstance(tx_date_obj, datetime) else tx_date_obj
    ).isoformat()
    rate = _find_currency_rate(currency_rates, quote_asset_id, date_str)
    if not rate or rate <= 0:
        return None
    return rate


def _is_in_quote_currency(
    src_currency: Any, quote_asset_id: int, quote_code_by_id: Optional[Dict[int, str]],
) -> bool:
    """Брокер прислал сумму уже в валюте котировки (например, USD для бумаги в USD)."""
    if not quote_code_by_id:
        return False
    src = _fmt_currency_code(src_currency)
    quote = quote_code_by_id.get(int(quote_asset_id), "")
    return bool(src) and src not in ("rub", "rur") and src == quote


def _convert_price_payment_to_rub_if_needed(
    asset_id: Optional[int],
    currency_assets_map: Dict[int, int],
    currency_rates: dict,
    tx_date: Any,
    price: float,
    payment: float,
    *,
    price_currency: Any = None,
    payment_currency: Any = None,
    quote_code_by_id: Optional[Dict[int, str]] = None,
) -> Tuple[float, float]:
    """
    Для активов с валютной котировкой: если брокер отдал price/payment в RUB —
    переводим в валюту котировки (деление на курс quote→RUB на дату).
    Если сумма уже в валюте котировки (price_currency/payment_currency = код котировки),
    её не трогаем: иначе USD-сумма делится на курс второй раз.
    SQL затем считает amount_rub = payment_quote × курс.
    """
    if not asset_id or asset_id not in currency_assets_map:
        return price, payment
    quote_asset_id = currency_assets_map[asset_id]
    rate = _rate_on_date(currency_rates, quote_asset_id, tx_date)
    if rate is None:
        return price, payment
    if not _is_in_quote_currency(price_currency, quote_asset_id, quote_code_by_id):
        price = round(price / rate, 6)
    if not _is_in_quote_currency(payment_currency, quote_asset_id, quote_code_by_id):
        payment = round(payment / rate, 6)
    return price, payment


def _commission_quote_and_rub(
    asset_id: Optional[int],
    currency_assets_map: Dict[int, int],
    currency_rates: dict,
    tx_date: Any,
    commission: float,
    commission_currency: Any,
    quote_code_by_id: Optional[Dict[int, str]],
) -> Tuple[float, Optional[float]]:
    """
    Комиссия в валюте операции (quote для FX-активов) и её рублёвый эквивалент.
    Раньше commission_rub для FX-активов заполнялся суммой в валюте котировки
    (≈ в 90 раз меньше рублёвой), из-за чего комиссии в аналитике были занижены.
    """
    if abs(commission) < 1e-12:
        return commission, None
    if not asset_id or asset_id not in currency_assets_map:
        return commission, round(commission, 6)
    quote_asset_id = currency_assets_map[asset_id]
    rate = _rate_on_date(currency_rates, quote_asset_id, tx_date)
    if _is_in_quote_currency(commission_currency, quote_asset_id, quote_code_by_id):
        # Брокер прислал комиссию в валюте котировки; рубли — по курсу (если курс неизвестен — SQL пересчитает)
        return commission, (round(commission * rate, 6) if rate is not None else None)
    if rate is None:
        return commission, round(commission, 6)
    return round(commission / rate, 6), round(commission, 6)


async def _asset_ids_that_exist(asset_ids: List[int]) -> set[int]:
    """Проверка, что id есть в assets (защита от гонок и устаревших id в картах)."""
    if not asset_ids:
        return set()
    async with acquire_connection() as conn:
        rows = await conn.fetch(
            "SELECT id FROM assets WHERE id = ANY($1::bigint[])",
            asset_ids,
        )
    return {int(r["id"]) for r in rows}


def _validate_broker_data(broker_data: Any) -> None:
    """
    Проверка ответа брокера ДО любых изменений в БД: пустой или битый ответ
    (сбой API, отозванный токен, частичная выгрузка) не должен стирать портфель.
    """
    if not isinstance(broker_data, dict) or not broker_data:
        raise ValueError(
            "Брокер не вернул ни одного счёта — импорт отменён, данные портфеля не изменены"
        )
    for name, pdata in broker_data.items():
        if not isinstance(pdata, dict) or not isinstance(pdata.get("transactions"), list):
            raise ValueError(
                f"Некорректные данные счёта «{name}» — импорт отменён, данные портфеля не изменены"
            )


def _is_partial_amortization(tx: dict) -> bool:
    return (
        tx.get("tinkoff_operation_type") in _PARTIAL_AMORTIZATION_BROKER_TYPES
        or tx.get("amortization_kind") == "partial"
    )


async def import_broker_portfolio(
    email: str,
    parent_portfolio_id: int,
    broker_data: dict,
    broker_id: int,
    clear_before_import: bool = False,
    api_key: Optional[str] = "",
    progress_callback=None,
):
    """Полный импорт ответа брокера в портфель (одна транзакция).

    api_key — токен для сохранения в подключении; пустой — токен подключения не меняется.
    progress_callback(index, total, account_name) — async, вызывается перед записью каждого счёта.
    """
    _validate_broker_data(broker_data)

    user = await get_user_by_email(email)
    if not user:
        raise ValueError(f"Пользователь с email {email} не найден")
    user_id = user["id"]

    # Очистка и запись — одна транзакция: при любой ошибке откатывается всё,
    # включая clear_portfolio_full, и пользователь видит прежние данные.
    async with db_transaction() as conn:
        # Один импорт на портфель одновременно: параллельная задача дождётся
        # окончания текущей и выполнит полный реимпорт поверх (без дублей).
        await conn.execute(
            "SELECT pg_advisory_xact_lock(hashtext('broker_import_' || $1::bigint::text))",
            int(parent_portfolio_id),
        )
        owner_id = await conn.fetchval(
            "SELECT user_id FROM portfolios WHERE id = $1", int(parent_portfolio_id),
        )
        if owner_id is None or str(owner_id) != str(user_id):
            raise ValueError("Портфель не найден или не принадлежит пользователю")

        return await _import_broker_portfolio_locked(
            user_id, parent_portfolio_id, broker_data, broker_id, api_key,
            progress_callback=progress_callback,
        )


async def _report_progress(progress_callback, index: int, total: int, account_name: str) -> None:
    if not progress_callback:
        return
    try:
        await progress_callback(index, total, account_name)
    except Exception:
        logger.debug("progress_callback failed", exc_info=True)


_CURRENCY_ASSET_TYPE_ID = 7
_RECONCILIATION_REPORT_LIMIT = 50


def _qty_differs(a: float, b: float) -> bool:
    return abs(a - b) > max(1e-6, 1e-6 * max(abs(a), abs(b)))


def _reconcile_positions(
    broker_positions: Dict[int, dict],
    unresolved_positions: List[dict],
    portfolio_rows: List[dict],
    assets_by_id: Dict[int, dict],
) -> dict:
    """Сверка остатков бумаг после импорта с позициями, которые вернул брокер.

    Валюты не сверяем (остатки денег считаются операциями, у брокера — отдельные позиции).
    Нераспознанные позиции брокера (ISIN не нашёлся в справочнике) — тоже расхождение:
    по ним в портфеле ничего нет.
    """
    def _is_currency(aid: int) -> bool:
        return (assets_by_id.get(aid) or {}).get("asset_type_id") == _CURRENCY_ASSET_TYPE_ID

    ours = {
        int(r["asset_id"]): float(r.get("quantity") or 0)
        for r in portfolio_rows or []
        if r.get("asset_id") is not None
    }
    asset_ids = {aid for aid, pos in broker_positions.items() if abs(pos.get("quantity") or 0) > 1e-9}
    asset_ids |= {aid for aid, qty in ours.items() if abs(qty) > 1e-9}

    mismatches = []
    checked = 0
    for aid in sorted(a for a in asset_ids if not _is_currency(a)):
        checked += 1
        pos = broker_positions.get(aid) or {}
        broker_qty = float(pos.get("quantity") or 0)
        our_qty = ours.get(aid, 0.0)
        if not _qty_differs(broker_qty, our_qty):
            continue
        asset = assets_by_id.get(aid) or {}
        mismatches.append({
            "asset_id": aid,
            "ticker": pos.get("ticker") or asset.get("ticker"),
            "name": pos.get("name") or asset.get("name"),
            "broker_quantity": round(broker_qty, 6),
            "portfolio_quantity": round(our_qty, 6),
        })
    for pos in unresolved_positions:
        checked += 1
        mismatches.append({
            "asset_id": None,
            "ticker": pos.get("ticker"),
            "name": pos.get("name"),
            "isin": pos.get("isin"),
            "broker_quantity": round(float(pos.get("quantity") or 0), 6),
            "portfolio_quantity": 0.0,
            "reason": "asset_not_found",
        })
    return {
        "checked": checked,
        "matched": checked - len(mismatches),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:_RECONCILIATION_REPORT_LIMIT],
    }


def _fp_value(v: Any) -> str:
    if v is None or v == "":
        return ""
    try:
        return f"{float(v):.6f}"
    except (TypeError, ValueError):
        return str(v)


def _broker_external_ids(transactions: List[dict]) -> List[str]:
    """Стабильный идентификатор каждой операции брокера — по нему запоминаем,
    что пользователь удалил или изменил операцию, и не возвращаем её.

    Есть id операции у брокера — берём его; нет — отпечаток полей операции.
    Совпадающие (две одинаковые сделки в одну секунду) нумеруются по порядку.
    """
    seen: Dict[str, int] = {}
    out: List[str] = []
    for tx in transactions:
        op_id = tx.get("operation_id")
        if op_id:
            base = f"op:{op_id}"
        else:
            raw = "|".join([
                str(tx.get("type") or ""),
                normalize_date_to_string(tx.get("date"), include_time=True) or str(tx.get("date") or ""),
                str(tx.get("isin") or tx.get("figi") or tx.get("ticker") or ""),
                _fp_value(tx.get("quantity")),
                _fp_value(tx.get("price")),
                _fp_value(tx.get("payment")),
                str(tx.get("currency") or ""),
            ])
            base = "fp:" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]
        n = seen.get(base, 0)
        seen[base] = n + 1
        out.append(base if n == 0 else f"{base}#{n}")
    return out


_MANUAL_PRICE_TOLERANCE = 0.01


def _ts(value: Any) -> str:
    return normalize_date_to_string(value, include_time=True) or str(value or "")


def _day(value: Any) -> str:
    return _ts(value)[:10]


def _transfer_direction(tx: dict, price: float, payment: float) -> Optional[str]:
    """Ввод ('in') или вывод ('out') бумаг между брокерами — не сделка, цены у брокера нет.

    Записанный по цене 0 ввод показывал бы «прибыль» на всю стоимость бумаг,
    а вывод — такой же убыток. Себестоимость для них считаем сами.
    """
    if price > 0 or tx.get("type") not in ("Buy", "Sell"):
        return None
    if tx.get("transfer") or abs(payment) < 1e-8:
        return "in" if tx["type"] == "Buy" else "out"
    return None


def _fifo_cost_price(events: List[tuple], date: str, qty: float) -> Optional[float]:
    """Средняя цена лотов, которые FIFO спишет при выводе qty бумаг на дату date.

    events — (дата, тип транзакции, количество, цена): 1 — покупка, 2/3 — списание.
    """
    lots: List[List[float]] = []
    for ev_date, ev_type, ev_qty, ev_price in sorted(events, key=lambda e: e[0]):
        if ev_date > date:
            break
        if ev_type == 1:
            lots.append([float(ev_qty), float(ev_price)])
            continue
        rest = float(ev_qty)
        while rest > 1e-9 and lots:
            take = min(rest, lots[0][0])
            lots[0][0] -= take
            rest -= take
            if lots[0][0] <= 1e-9:
                lots.pop(0)
    rest, cost = float(qty), 0.0
    for lot_qty, lot_price in lots:
        take = min(rest, lot_qty)
        cost += take * lot_price
        rest -= take
        if rest <= 1e-9:
            break
    taken = float(qty) - rest
    return round(cost / taken, 6) if taken > 1e-9 else None


async def _market_price_on(asset_id: int, date: Any) -> Optional[float]:
    """Цена закрытия бумаги на дату перевода (не старше двух недель), в валюте котировки."""
    day = normalize_date_to_sql_date(date)
    if not day:
        return None
    async with acquire_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT price FROM asset_prices
            WHERE asset_id = $1 AND trade_date <= $2::date AND trade_date >= $2::date - 14
            ORDER BY trade_date DESC
            LIMIT 1
            """,
            asset_id, datetime.strptime(day, "%Y-%m-%d").date(),
        )
    return float(row["price"]) if row and row["price"] else None


def _opt_int(v: Any) -> Optional[int]:
    return int(v) if v is not None else None


class _ManualRows:
    """Ручные записи, оставшиеся в портфеле после очистки.

    Операция брокера, которую пользователь уже добавил сам (тот же день, бумага,
    количество, цена ±1% / сумма), второй раз не записывается. Каждая ручная запись
    закрывает не больше одной операции брокера.
    """

    def __init__(self, rows: Optional[List[dict]]):
        self._cash: Dict[tuple, int] = {}
        self._tx: Dict[tuple, List[float]] = {}
        self._lots: Dict[Optional[int], List[tuple]] = {}
        for r in rows or []:
            if r.get("kind") == "tx":
                key = self._tx_key(r.get("asset_id"), r.get("type"), r.get("date"), r.get("quantity"))
                self._tx.setdefault(key, []).append(float(r.get("price") or 0))
                self._lots.setdefault(_opt_int(r.get("asset_id")), []).append((
                    _ts(r.get("date")), int(r.get("type") or 0),
                    abs(float(r.get("quantity") or 0)), float(r.get("price") or 0),
                ))
            elif r.get("kind") == "cash":
                key = self._cash_key(r.get("type"), r.get("date"), r.get("asset_id"), r.get("amount"))
                self._cash[key] = self._cash.get(key, 0) + 1

    @staticmethod
    def _tx_key(asset_id, tx_type, date, qty) -> tuple:
        return (_opt_int(asset_id), int(tx_type or 0), _day(date), round(abs(float(qty or 0)), 6))

    @staticmethod
    def _cash_key(op_type, date, asset_id, amount) -> tuple:
        return (int(op_type or 0), _day(date), _opt_int(asset_id), round(abs(float(amount or 0)), 2))

    def lots(self, asset_id) -> List[tuple]:
        """Ручные транзакции по бумаге: (дата, тип, количество, цена) — для FIFO."""
        return list(self._lots.get(_opt_int(asset_id), []))

    def take_tx(self, asset_id, tx_type, date, qty, price) -> bool:
        """price=None — без сравнения цены (у перевода бумаг цену считаем сами)."""
        prices = self._tx.get(self._tx_key(asset_id, tx_type, date, qty))
        if not prices:
            return False
        if price is None:
            prices.pop(0)
            return True
        price = float(price or 0)
        for i, p in enumerate(prices):
            if abs(p - price) <= max(1e-6, _MANUAL_PRICE_TOLERANCE * max(abs(p), abs(price))):
                prices.pop(i)
                return True
        return False

    def take_cash(self, op_type, date, asset_id, amount) -> bool:
        key = self._cash_key(op_type, date, asset_id, amount)
        if self._cash.get(key, 0) <= 0:
            return False
        self._cash[key] -= 1
        return True


def _match_child_portfolio(
    children: List[dict], used_ids: set, account_id: Optional[str], name: str,
) -> Optional[dict]:
    """Дочерний портфель прошлой синхронизации для счёта брокера:
    сначала по номеру счёта, затем (портфели до привязки) — по названию."""
    if account_id:
        for c in children:
            if c["id"] not in used_ids and str(c.get("broker_account_id") or "") == account_id:
                return c
    for c in children:
        if c["id"] not in used_ids and not c.get("broker_account_id") and c.get("name") == name:
            return c
    return None


def _as_dict(value: Any) -> dict:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return {}
    return value if isinstance(value, dict) else {}


def _sync_summary(account_reports: List[dict]) -> dict:
    """Короткий итог синхронизации для карточки подключения (без списков операций)."""
    return {
        "synced_at": datetime.utcnow().replace(microsecond=0).isoformat(),
        "inserted_count": sum(r["inserted_count"] for r in account_reports),
        "failed_count": sum(r["failed_count"] for r in account_reports),
        "skipped_count": sum(r["skipped_count"] for r in account_reports),
        "suppressed_count": sum(r.get("suppressed_count", 0) for r in account_reports),
        "matched_manual_count": sum(r.get("matched_manual_count", 0) for r in account_reports),
        "kept_manual_count": sum(r.get("kept_manual_count", 0) for r in account_reports),
        "transfer_count": sum(r.get("transfer_count", 0) for r in account_reports),
        "accounts": [
            {
                k: r.get(k)
                for k in (
                    "account", "portfolio_id", "inserted_count", "failed_count", "skipped_count",
                    "suppressed_count", "matched_manual_count", "kept_manual_count", "transfer_count",
                )
            } | {"mismatch_count": (r.get("reconciliation") or {}).get("mismatch_count", 0)}
            for r in account_reports
        ],
        "mismatch_count": sum((r.get("reconciliation") or {}).get("mismatch_count", 0) for r in account_reports),
    }


async def _import_broker_portfolio_locked(
    user_id,
    parent_portfolio_id: int,
    broker_data: dict,
    broker_id: int,
    api_key: Optional[str],
    progress_callback=None,
):
    # ======================================================================
    # Сначала очистка брокерских записей: clear_broker_portfolio_data удаляет и
    # неиспользуемые кастомные активы (database/clear_broker_portfolio_data.sql).
    # Справочники isin/figi/ticker → asset_id нужно строить ПОСЛЕ очистки, иначе
    # в памяти остаются id удалённых строк assets → FK при batch_create_portfolio_assets.
    # Ручные записи пользователя остаются и возвращаются списком — для дедупликации.
    # ======================================================================
    cleared = _as_dict(await rpc_async(
        "clear_broker_portfolio_data", {"p_portfolio_id": parent_portfolio_id},
    ))
    kept_manual: Dict[str, List[dict]] = cleared.get("kept_manual") or {}
    logger.info(
        "Очистка брокерских записей портфеля %s выполнена (в транзакции импорта), "
        "ручных записей осталось: %s",
        parent_portfolio_id, cleared.get("kept_manual_count", 0),
    )

    children = await table_select_async(
        "portfolios",
        select="id, name, broker_account_id",
        filters={"parent_portfolio_id": parent_portfolio_id},
    ) or []
    used_child_ids: set = set()

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
    quote_code_by_id = _quote_code_by_asset_id(ticker_to_quote)
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
    amortization_op_type_id = op_type_map.get("amortization")

    imported_portfolio_ids = []
    account_reports = []

    for account_index, (portfolio_name, pdata) in enumerate(broker_data.items()):
        logger.info(f"Импортируем портфель '{portfolio_name}'")
        await _report_progress(progress_callback, account_index, len(broker_data), portfolio_name)

        # ==================================================================
        # Дочерний портфель счёта: прежний (с ручными записями и настройками) или новый
        # ==================================================================
        account_id = str(pdata.get("account_id") or "").strip() or None
        existing_child = _match_child_portfolio(children, used_child_ids, account_id, portfolio_name)
        if existing_child:
            portfolio_id = existing_child["id"]
            if account_id and not existing_child.get("broker_account_id"):
                await table_update_async(
                    "portfolios", {"broker_account_id": account_id}, filters={"id": portfolio_id},
                )
            suppressed_rows = await table_select_async(
                "broker_operation_suppressions",
                select="external_id",
                filters={"portfolio_id": portfolio_id},
            ) or []
            suppressed_ids = {r["external_id"] for r in suppressed_rows if r.get("external_id")}
        else:
            child_row = {
                "user_id": user_id,
                "parent_portfolio_id": parent_portfolio_id,
                "name": portfolio_name,
            }
            if account_id:
                child_row["broker_account_id"] = account_id
            child = await table_insert_async("portfolios", child_row)
            if not child:
                raise RuntimeError(
                    f"Не удалось создать дочерний портфель «{portfolio_name}» — импорт отменён"
                )
            portfolio_id = child[0]["id"]
            suppressed_ids = set()
        used_child_ids.add(portfolio_id)
        manual_rows = _ManualRows(kept_manual.get(str(portfolio_id)))
        kept_manual_count = len(kept_manual.get(str(portfolio_id)) or [])
        suppressed_count = 0
        matched_manual_count = 0

        # ==================================================================
        # Собираем нужные asset_id из брокерских данных
        # ==================================================================
        needed_asset_ids = set()
        broker_positions_map = {}
        unresolved_positions = []
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
                        "ticker": pos.get("ticker"),
                        "name": pos.get("name"),
                    }
                elif pos.get("isin") and abs(float(pos.get("quantity") or 0)) > 1e-9:
                    # У валют ISIN нет — в сверку попадают только бумаги
                    unresolved_positions.append(pos)

        sorted_transactions = sorted(
            pdata["transactions"],
            key=lambda x: (x.get("date", ""), x.get("type", "")),
        )
        external_ids = _broker_external_ids(sorted_transactions)

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
        # В портфеле после очистки только ручные записи: удалённое/изменённое
        # пользователем пропускаем, уже добавленное вручную — не дублируем
        # ==================================================================
        new_tx = []
        new_ops = []
        skipped_ops = []
        transfers = []

        for tx, external_id in zip(sorted_transactions, external_ids):
            if external_id in suppressed_ids:
                suppressed_count += 1
                continue
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

            # Частичная амортизация — выплата части номинала, бумаги остаются:
            # пишем денежной операцией, а не Redemption (тот списал бы всю позицию).
            if tx_type == "Amortization" and _is_partial_amortization(tx) and amortization_op_type_id:
                if abs(payment) < 1e-8:
                    continue
                if not normalize_date_to_string(tx_date, include_time=True):
                    skipped_ops.append({"type": tx_type, "date": tx_date, "reason": "bad_date"})
                    continue
                currency_id_for_op = 1
                if asset_id and asset_id in currency_assets_map:
                    currency_id_for_op = currency_assets_map[asset_id]
                    _, payment = _convert_price_payment_to_rub_if_needed(
                        asset_id, currency_assets_map, currency_rates, tx_date, 0.0, payment,
                        payment_currency=tx.get("currency"), quote_code_by_id=quote_code_by_id,
                    )
                if manual_rows.take_cash(amortization_op_type_id, tx_date, asset_id, payment):
                    matched_manual_count += 1
                    continue
                new_ops.append({
                    "user_id": user_id,
                    "portfolio_id": portfolio_id,
                    "type": amortization_op_type_id,
                    "amount": abs(payment),
                    "currency": currency_id_for_op,
                    "date": tx_date,
                    "asset_id": asset_id,
                    "portfolio_asset_id": pa_map.get(asset_id) if asset_id else None,
                    "transaction_id": None,
                    "external_id": external_id,
                })
                continue

            if tx_type in ("Buy", "Sell", "Amortization"):
                if not asset_id:
                    if tx_type == "Buy":
                        logger.warning(
                            "Импорт: пропуск покупки — нет ISIN/FIGI/тикера в справочнике "
                            f"(isin={isin!r}, figi={tx.get('figi')!r}, ticker={tx.get('ticker')!r}, "
                            f"date={tx_date}). Старые тикеры задайте в data/broker_ticker_aliases.json."
                        )
                    skipped_ops.append({
                        "type": tx_type, "date": tx_date, "isin": isin,
                        "ticker": tx.get("ticker"), "reason": "asset_not_found",
                    })
                    continue

                pa_id = pa_map.get(asset_id)
                if not pa_id:
                    if tx_type == "Buy":
                        logger.warning(
                            "Импорт: пропуск покупки — нет portfolio_asset "
                            f"(asset_id={asset_id}, date={tx_date})."
                        )
                    skipped_ops.append({
                        "type": tx_type, "date": tx_date, "asset_id": asset_id,
                        "reason": "portfolio_asset_not_created",
                    })
                    continue

                tx_date_normalized = normalize_date_to_string(tx_date, include_time=True)
                if not tx_date_normalized:
                    tx_date_normalized = normalize_date_to_day_string(tx_date)
                    if not tx_date_normalized:
                        skipped_ops.append({"type": tx_type, "date": tx_date, "reason": "bad_date"})
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
                            skipped_ops.append({
                                "type": tx_type, "date": tx_date, "asset_id": asset_id,
                                "reason": "redemption_quantity_unknown",
                            })
                            continue
                        op_quantity = calculated_qty

                    price = round(payment / op_quantity, 6) if op_quantity > 0 else 0.0
                    price_currency = tx.get("currency")
                    qty = round(op_quantity, 6)
                else:
                    price = round(float(tx.get("price") or 0), 6)
                    price_currency = tx.get("price_currency") or tx.get("currency")
                    qty = round(float(tx.get("quantity") or 0), 6)

                # Цена и payment от брокера обычно в RUB; для FX-активов переводим в quote,
                # currency_id = quote (как до 5b129d0). SQL считает amount_rub = payment × курс.
                currency_id_for_tx = 1
                comm_val, comm_rub = _commission_quote_and_rub(
                    asset_id, currency_assets_map, currency_rates, tx_date,
                    float(tx.get("commission") or 0), tx.get("currency"), quote_code_by_id,
                )
                if asset_id in currency_assets_map:
                    currency_id_for_tx = currency_assets_map[asset_id]
                    price, payment = _convert_price_payment_to_rub_if_needed(
                        asset_id, currency_assets_map, currency_rates, tx_date, price, payment,
                        price_currency=price_currency,
                        payment_currency=tx.get("currency"),
                        quote_code_by_id=quote_code_by_id,
                    )

                # Перевод бумаг от/к другому брокеру: себестоимость — средняя цена позиции у
                # брокера (нет — рыночная на дату), при выводе — цена списываемых FIFO-лотов.
                # Пользователь может её исправить: правка сохранится (broker_operation_suppressions).
                transfer = _transfer_direction(tx, price, payment)
                price_source = None
                if transfer:
                    price, price_source = 0.0, "unknown"
                    if transfer == "out":
                        events = manual_rows.lots(asset_id) + [
                            (_ts(t["transaction_date"]), t["transaction_type"], t["quantity"], t["price"])
                            for t in new_tx if t["portfolio_asset_id"] == pa_id
                        ]
                        fifo = _fifo_cost_price(events, _ts(tx_date_normalized), qty)
                        if fifo:
                            price, price_source = fifo, "fifo"
                    pos = broker_positions_map.get(asset_id) or {}
                    if price_source == "unknown" and float(pos.get("average_price") or 0) > 0:
                        price = _convert_price_payment_to_rub_if_needed(
                            asset_id, currency_assets_map, currency_rates, tx_date,
                            float(pos["average_price"]), 0.0,
                            price_currency=pos.get("average_price_currency"),
                            quote_code_by_id=quote_code_by_id,
                        )[0]
                        price_source = "broker_average"
                    if price_source == "unknown" and transfer == "in":
                        market = await _market_price_on(asset_id, tx_date_normalized)
                        if market:
                            price, price_source = round(market, 6), "market"

                tx_type_id = {"Buy": 1, "Sell": 2, "Amortization": 3}[tx_type]
                if manual_rows.take_tx(
                    asset_id, tx_type_id, tx_date_normalized, qty, None if transfer else price,
                ):
                    matched_manual_count += 1
                    continue

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
                    "external_id": external_id,
                }
                if abs(comm_val) >= 1e-12:
                    tx_row["commission"] = comm_val
                if comm_rub is not None:
                    tx_row["commission_rub"] = comm_rub
                new_tx.append(tx_row)
                if transfer:
                    transfers.append({
                        "direction": transfer,
                        "date": tx_date_normalized,
                        "ticker": tx.get("ticker") or (assets_by_id.get(asset_id) or {}).get("ticker"),
                        "name": tx.get("name") or (assets_by_id.get(asset_id) or {}).get("name"),
                        "quantity": qty,
                        "price": price,
                        "price_source": price_source,
                    })
            else:
                # Cash operations: Dividend, Coupon, Commission, Tax, Deposit, Withdraw
                if abs(payment) < 1e-8:
                    continue

                op_type_id = op_type_map.get(tx_type.lower())
                if not op_type_id:
                    if tx_type != "Other":
                        skipped_ops.append({"type": tx_type, "date": tx_date, "reason": "unknown_operation_type"})
                    continue

                op_date_normalized = normalize_date_to_string(tx_date, include_time=True)
                if not op_date_normalized:
                    op_date_normalized = normalize_date_to_day_string(tx_date)
                    if not op_date_normalized:
                        skipped_ops.append({"type": tx_type, "date": tx_date, "reason": "bad_date"})
                        continue

                currency_id_for_op = 1
                comm_cash = float(tx.get("commission") or 0)
                comm_cash_rub = round(comm_cash, 6) if abs(comm_cash) >= 1e-12 else None
                if op_type_id not in (5, 6) and asset_id and asset_id in currency_assets_map:
                    currency_id_for_op = currency_assets_map[asset_id]
                    comm_cash, comm_cash_rub = _commission_quote_and_rub(
                        asset_id, currency_assets_map, currency_rates, tx_date,
                        comm_cash, tx.get("currency"), quote_code_by_id,
                    )
                    _, payment = _convert_price_payment_to_rub_if_needed(
                        asset_id, currency_assets_map, currency_rates, tx_date, 0.0, payment,
                        payment_currency=tx.get("currency"), quote_code_by_id=quote_code_by_id,
                    )

                pa_id_for_op = pa_map.get(asset_id) if asset_id else None
                if manual_rows.take_cash(op_type_id, op_date_normalized, asset_id, payment):
                    matched_manual_count += 1
                    continue

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
                    "external_id": external_id,
                }
                if abs(comm_cash) >= 1e-12:
                    op_row["commission"] = comm_cash
                if comm_cash_rub is not None:
                    op_row["commission_rub"] = comm_cash_rub
                new_ops.append(op_row)

        # ==================================================================
        # Отправляем в БД одним батчем
        # ==================================================================
        inserted = 0
        failed = 0
        failed_operations: List[dict] = []
        if new_tx or new_ops:
            operations_batch = _build_operations_batch(new_tx, new_ops, op_type_map)
            operations_batch.sort(key=lambda x: parse_date(
                x.get("operation_date") or x.get("date") or ""
            ) or datetime.min)

            try:
                result = await _operation_repository.apply_operations_batch(operations_batch)
            except Exception as e:
                # Не глотаем: иначе портфель остаётся очищенным, а задача — «успешной».
                logger.error(f"Ошибка при apply_operations_batch: {e}", exc_info=True)
                raise RuntimeError(
                    f"Счёт «{portfolio_name}»: не удалось записать операции ({e}) — "
                    "импорт отменён, данные портфеля не изменены"
                ) from e
            inserted = int((result or {}).get("inserted_count", 0) or 0)
            failed = int((result or {}).get("failed_count", 0) or 0)
            failed_operations = list((result or {}).get("failed_operations") or [])
            logger.info(
                f"Портфель '{portfolio_name}': batch insert — "
                f"inserted={inserted}, failed={failed}, skipped={len(skipped_ops)}, "
                f"suppressed={suppressed_count}, matched_manual={matched_manual_count}"
            )
            for f_op in failed_operations:
                logger.warning(f"  failed: {f_op.get('error', '?')}")
        else:
            logger.info(f"Портфель '{portfolio_name}': операций нет")

        if skipped_ops:
            logger.warning(
                "Портфель '%s': пропущено %s операций брокера: %s",
                portfolio_name, len(skipped_ops), skipped_ops[:_FAILED_OPERATIONS_REPORT_LIMIT],
            )

        reconciliation = None
        if "positions" in pdata:
            pa_rows = await table_select_async(
                "portfolio_assets", select="asset_id, quantity", filters={"portfolio_id": portfolio_id},
            ) or []
            reconciliation = _reconcile_positions(
                broker_positions_map, unresolved_positions, pa_rows, assets_by_id,
            )
            if reconciliation["mismatch_count"]:
                logger.warning(
                    "Портфель '%s': расхождение с брокером по %s позициям: %s",
                    portfolio_name, reconciliation["mismatch_count"], reconciliation["mismatches"][:10],
                )

        account_reports.append({
            "account": portfolio_name,
            "portfolio_id": portfolio_id,
            "inserted_count": inserted,
            "failed_count": failed,
            "skipped_count": len(skipped_ops),
            "suppressed_count": suppressed_count,
            "matched_manual_count": matched_manual_count,
            "kept_manual_count": kept_manual_count,
            "transfer_count": len(transfers),
            "transfers": transfers[:_FAILED_OPERATIONS_REPORT_LIMIT],
            "failed_operations": failed_operations[:_FAILED_OPERATIONS_REPORT_LIMIT],
            "skipped_operations": skipped_ops[:_FAILED_OPERATIONS_REPORT_LIMIT],
            "reconciliation": reconciliation,
        })
        imported_portfolio_ids.append(portfolio_id)

    # ======================================================================
    # Счета, которых брокер больше не возвращает: пустые удаляем (как раньше),
    # с ручными записями пользователя — оставляем
    # ======================================================================
    for c in children:
        if c["id"] in used_child_ids:
            continue
        if kept_manual.get(str(c["id"])):
            logger.info(
                "Счёт «%s» (портфель %s) не пришёл от брокера, но в нём есть ручные записи — оставляем",
                c.get("name"), c["id"],
            )
            continue
        await rpc_async("clear_portfolio_full", {"p_portfolio_id": c["id"], "p_delete_self": True})

    # ======================================================================
    # Broker connection — только на родительский портфель
    # ======================================================================
    if imported_portfolio_ids:
        from app.domain.services.broker_connections_service import upsert_broker_connection

        await upsert_broker_connection(
            user_id, broker_id, parent_portfolio_id, api_key,
            sync_summary=_sync_summary(account_reports),
        )

    return {
        "success": True,
        "imported_portfolio_ids": imported_portfolio_ids,
        "inserted_count": sum(r["inserted_count"] for r in account_reports),
        "failed_count": sum(r["failed_count"] for r in account_reports),
        "skipped_count": sum(r["skipped_count"] for r in account_reports),
        "suppressed_count": sum(r["suppressed_count"] for r in account_reports),
        "matched_manual_count": sum(r["matched_manual_count"] for r in account_reports),
        "kept_manual_count": int(cleared.get("kept_manual_count") or 0),
        "mismatch_count": sum((r.get("reconciliation") or {}).get("mismatch_count", 0) for r in account_reports),
        "accounts": account_reports,
    }


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
            "source": "broker",
        }
        if tx.get("external_id"):
            tx_payload["external_id"] = tx["external_id"]
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
            "source": "broker",
        }
        if op.get("external_id"):
            op_payload["external_id"] = op["external_id"]
        if op.get("commission") is not None and abs(float(op.get("commission") or 0)) >= 1e-12:
            op_payload["commission"] = float(op["commission"])
        if op.get("commission_rub") is not None:
            op_payload["commission_rub"] = float(op["commission_rub"])
        batch.append(op_payload)

    return batch
