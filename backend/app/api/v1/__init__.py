"""
API версии 1.
Импорт всех роутеров для удобной регистрации.
"""
from app.api.v1 import (
    auth,
    portfolios,
    assets,
    transactions,
    operations,
    analytics,
    dashboard,
    tasks
)

__all__ = [
    "auth",
    "portfolios",
    "assets",
    "transactions",
    "operations",
    "analytics",
    "dashboard",
    "tasks"
]
