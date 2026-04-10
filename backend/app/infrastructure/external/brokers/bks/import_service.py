"""
Сервис импорта портфеля из БКС (Trade API).

Документация: https://trade-api.bcs.ru/http/
Реальный API: https://be.broker.ru

Эндпоинты:
- GET  /trade-api-bff-portfolio/api/v1/portfolio — позиции и деньги
- POST /trade-api-bff-trade-details/api/v1/trades/search — сделки
  Query: page, size (1-100), sort. Body: side (1/2), tradeNums, tickers, classCodes, startDateTime, endDateTime

Авторизация: refresh_token -> access_token через OAuth
(токен получается в веб-версии БКС Мир инвестиций)

Возвращает данные в формате, совместимом с portfolio_import_service:
{ account_name: { account_id, positions, transactions } }
"""
from datetime import datetime, timedelta
import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

# Маппинг типов операций БКС -> CapitalView
OPERATION_CLASSIFICATION = {
    "BUY": "Buy",
    "SELL": "Sell",
    "PURCHASE": "Buy",
    "SALE": "Sell",
    "DIVIDEND": "Dividend",
    "COUPON": "Coupon",
    "DEPOSIT": "Deposit",
    "WITHDRAW": "Withdraw",
    "COMMISSION": "Commission",
    "FEE": "Commission",
    "TAX": "Tax",
    "REDEMPTION": "Amortization",
    "BOND_REPAYMENT": "Amortization",
}

# БКС Trade API (импорт портфеля)
# Реальный API: https://be.broker.ru (документация: https://trade-api.bcs.ru/http/)
BKS_API_BASE_URL = "https://be.broker.ru"
BKS_OAUTH_URL = "https://be.broker.ru/trade-api-keycloak/realms/tradeapi/protocol/openid-connect/token"
# trade-api-read — чтение; trade-api-write — торговля
BKS_OAUTH_CLIENT_ID = "trade-api-read"


def _get_access_token(refresh_token: str) -> str:
    """
    Обменивает refresh_token на access_token через OAuth.
    POST /trade-api-keycloak/realms/tradeapi/protocol/openid-connect/token
    Body (form-urlencoded): client_id, refresh_token, grant_type
    - client_id: trade-api-read (чтение) | trade-api-write (торговля)
    - grant_type: refresh_token
    """
    payload = {
        "client_id": BKS_OAUTH_CLIENT_ID,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(BKS_OAUTH_URL, data=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["access_token"]


def _get_headers(access_token: str) -> dict:
    """Формирует заголовки для запросов к БКС API."""
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def _normalize_trade_to_transaction(trade: dict) -> dict | None:
    """Преобразует сделку БКС в формат CapitalView."""
    trade_type = str(trade.get("type") or trade.get("operationType") or "").upper()
    trade_type = trade_type.replace("-", "_").replace(" ", "_")
    classified = OPERATION_CLASSIFICATION.get(trade_type)
    
    if not classified:
        # Пробуем по полю direction (Buy/Sell)
        direction = str(trade.get("direction") or "").upper()
        if direction in ("BUY", "PURCHASE", "B"):
            classified = "Buy"
        elif direction in ("SELL", "SALE", "S"):
            classified = "Sell"
        else:
            return None
    
    isin = trade.get("isin") or trade.get("figi")
    ticker = trade.get("ticker") or trade.get("symbol")
    name = trade.get("name") or trade.get("instrumentName")
    date_str = trade.get("date") or trade.get("tradeDate") or trade.get("operationDate") or ""
    if hasattr(date_str, "isoformat"):
        date_str = date_str.isoformat()
    
    qty = float(trade.get("quantity", 0) or trade.get("qty", 0) or trade.get("amount", 0) or 0)
    price = float(trade.get("price", 0) or trade.get("pricePerUnit", 0) or 0)
    payment = float(trade.get("payment", 0) or trade.get("amount", 0) or trade.get("sum", 0) or (qty * price if qty and price else 0))
    
    tx = {
        "figi": trade.get("figi"),
        "ticker": ticker,
        "name": name,
        "isin": isin,
        "date": date_str,
        "type": classified,
        "currency": trade.get("currency", "RUB"),
    }
    
    if classified in ("Buy", "Sell", "Amortization"):
        if classified in ("Buy", "Sell") and qty <= 0:
            return None
        tx["price"] = price
        tx["quantity"] = qty
        tx["payment"] = payment
    else:
        tx["price"] = None
        tx["quantity"] = None
        tx["payment"] = payment
    
    return tx


def _parse_portfolio_positions(portfolio_rows: list) -> list:
    """
    Парсит ответ GET /trade-api-bff-portfolio/api/v1/portfolio.
    Формат (из BcsPy): массив строк, где term=="T1" и board!="" и quantity>0 — позиции.
    """
    positions = []
    for row in portfolio_rows or []:
        term = row.get("term", "")
        board = row.get("board", "")
        qty = float(row.get("quantity", 0) or row.get("balance", 0) or 0)
        if term != "T1" or not board or qty <= 0:
            continue
        avg_price = float(row.get("averagePrice", 0) or row.get("avgPrice", 0) or row.get("average_price", 0) or 0)
        curr_price = float(row.get("currentPrice", 0) or row.get("lastPrice", 0) or row.get("price", 0) or avg_price)
        positions.append({
            "figi": row.get("figi"),
            "ticker": row.get("ticker") or row.get("symbol"),
            "name": row.get("name") or row.get("instrumentName"),
            "isin": row.get("isin") or row.get("figi"),
            "quantity": qty,
            "average_price": avg_price,
            "current_price": curr_price,
        })
    return positions


def get_bks_portfolio(refresh_token: str) -> dict:
    """
    Получает данные портфеля от брокера БКС.
    
    token — refresh_token (получается в веб-версии БКС Мир инвестиций).
    Обменивается на access_token через OAuth.
    
    Эндпоинты:
    - GET  /trade-api-bff-portfolio/api/v1/portfolio — позиции
    - POST /trade-api-bff-trade-details/api/v1/trades/search — сделки
    """
    base = (BKS_API_BASE_URL or "https://be.broker.ru").rstrip("/")
    portfolio_url = f"{base}/trade-api-bff-portfolio/api/v1/portfolio"
    trades_url = f"{base}/trade-api-bff-trade-details/api/v1/trades/search"
    
    logger.info("BKS portfolio import start")
    
    access_token = _get_access_token(refresh_token)
    headers = _get_headers(access_token)
    result = {}
    
    with httpx.Client(timeout=60.0) as client:
        # 1. Портфель (позиции)
        positions = []
        try:
            portfolio_resp = client.get(portfolio_url, headers=headers)
            portfolio_resp.raise_for_status()
            portfolio_data = portfolio_resp.json()
            
            # Ответ может быть массивом или объектом с полями
            rows = portfolio_data if isinstance(portfolio_data, list) else (
                portfolio_data.get("positions")
                or portfolio_data.get("securities")
                or portfolio_data.get("data")
                or []
            )
            if isinstance(rows, dict):
                rows = list(rows.values()) if rows else []
            positions = _parse_portfolio_positions(rows)
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"БКС API portfolio: {e.response.status_code} - {e.response.text}"
            ) from e
        
        # 2. Сделки (POST /trade-api-bff-trade-details/api/v1/trades/search)
        # Query: page, size (1-100), sort. Body: side, tradeNums, tickers, classCodes, startDateTime, endDateTime
        transactions = []
        try:
            now = datetime.utcnow()
            start_dt = (now - timedelta(days=365 * 2)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            end_dt = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            trades_body = {
                "tradeNums": [],
                "tickers": [],
                "classCodes": [],
                "startDateTime": start_dt,
                "endDateTime": end_dt,
            }
            trades_list = []
            for side_val in ("1", "2"):
                trades_body["side"] = side_val
                page = 0
                size = 100
                while True:
                    params = {"page": page, "size": size, "sort": "tradeDateTime,asc"}
                    trades_resp = client.post(
                        trades_url, headers=headers, json=trades_body, params=params
                    )
                    trades_resp.raise_for_status()
                    trades_data = trades_resp.json()
                    chunk = trades_data if isinstance(trades_data, list) else (
                        trades_data.get("content")
                        or trades_data.get("trades")
                        or trades_data.get("data")
                        or trades_data.get("items")
                        or []
                    )
                    if isinstance(chunk, dict):
                        chunk = list(chunk.values()) if chunk else []
                    trades_list.extend(chunk)
                    if len(chunk) < size:
                        break
                    page += 1
            
            for trade in trades_list:
                tx = _normalize_trade_to_transaction(trade)
                if tx:
                    transactions.append(tx)
            
            transactions.sort(key=lambda x: (x.get("date") or "", x.get("type") or ""))
        except httpx.HTTPStatusError as e:
            # Сделки доступны с 26.01.2026, может быть 404 или другой код
            if e.response.status_code == 404:
                logger.warning("BKS trades/search 404, using positions only")
            else:
                logger.warning("BKS trades API status=%s body=%s", e.response.status_code, e.response.text)
        
        result["Портфель БКС"] = {
            "account_id": "default",
            "positions": positions,
            "transactions": transactions,
        }
    
    return result
