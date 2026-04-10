"""
Публичные URL ISS MOEX — одна точка для импорта, воркеров и тестовых скриптов.
"""

MOEX_ISS_ROOT = "https://iss.moex.com/iss"

# База путей engines/stock/markets (как прежнее имя MOEX_BASE_URL в client / price_service).
MOEX_BASE_URL = f"{MOEX_ISS_ROOT}/engines/stock/markets"

MOEX_SECURITIES_JSON = f"{MOEX_ISS_ROOT}/securities.json"
SHARES_SECURITIES_JSON = f"{MOEX_BASE_URL}/shares/securities.json"
BONDS_ACTIVE_SECURITIES_JSON = f"{MOEX_BASE_URL}/bonds/securities.json"
BONDS_HISTORY_TICKER_BASE = f"{MOEX_ISS_ROOT}/history/engines/stock/markets/bonds/securities"


def moex_bondization_url(ticker: str) -> str:
    return f"{MOEX_ISS_ROOT}/securities/{ticker}/bondization.json"


def moex_bonds_securities_page_url(start: int, limit: int) -> str:
    return f"{MOEX_SECURITIES_JSON}?engine=stock&market=bonds&start={start}&limit={limit}"


def moex_bond_history_url(ticker: str) -> str:
    return f"{BONDS_HISTORY_TICKER_BASE}/{ticker}.json"
