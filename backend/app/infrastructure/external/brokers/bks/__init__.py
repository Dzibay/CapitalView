"""
Интеграция с брокером БКС (Trade API).
Структура аналогична Tinkoff.
"""
from .import_service import get_bks_portfolio, list_bks_accounts

__all__ = ["get_bks_portfolio", "list_bks_accounts"]
