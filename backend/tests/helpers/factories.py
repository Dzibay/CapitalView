"""
Фабрики для создания тестовых данных.
"""
import uuid
from datetime import datetime, date
from typing import Optional, Dict, Any


def create_test_user(
    email: Optional[str] = None,
    name: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Создает тестового пользователя.
    
    Args:
        email: Email пользователя
        name: Имя пользователя
        user_id: ID пользователя
        
    Returns:
        Словарь с данными пользователя
    """
    return {
        "id": user_id or str(uuid.uuid4()),
        "email": email or f"test_{uuid.uuid4().hex[:8]}@example.com",
        "name": name or "Test User",
        "password_hash": "hashed_password_123"
    }


def create_test_portfolio(
    user_id: Optional[str] = None,
    name: Optional[str] = None,
    portfolio_id: Optional[int] = None,
    parent_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Создает тестовый портфель.
    
    Args:
        user_id: ID пользователя
        name: Название портфеля
        portfolio_id: ID портфеля
        parent_id: ID родительского портфеля
        
    Returns:
        Словарь с данными портфеля
    """
    return {
        "id": portfolio_id or 1,
        "user_id": user_id or str(uuid.uuid4()),
        "name": name or "Test Portfolio",
        "parent_id": parent_id,
        "description": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


def create_test_asset(
    ticker: Optional[str] = None,
    name: Optional[str] = None,
    asset_id: Optional[int] = None,
    asset_type_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Создает тестовый актив.
    
    Args:
        ticker: Тикер актива
        name: Название актива
        asset_id: ID актива
        asset_type_id: ID типа актива
        
    Returns:
        Словарь с данными актива
    """
    return {
        "id": asset_id or 1,
        "ticker": ticker or "TEST",
        "name": name or "Test Asset",
        "asset_type_id": asset_type_id or 1,
        "quote_asset_id": 1,  # RUB
        "properties": {},
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


def create_test_transaction(
    portfolio_id: Optional[int] = None,
    asset_id: Optional[int] = None,
    transaction_id: Optional[int] = None,
    transaction_date: Optional[date] = None,
    quantity: Optional[float] = None,
    price: Optional[float] = None
) -> Dict[str, Any]:
    """
    Создает тестовую транзакцию.
    
    Args:
        portfolio_id: ID портфеля
        asset_id: ID актива
        transaction_id: ID транзакции
        transaction_date: Дата транзакции
        quantity: Количество
        price: Цена
        
    Returns:
        Словарь с данными транзакции
    """
    return {
        "id": transaction_id or 1,
        "portfolio_id": portfolio_id or 1,
        "asset_id": asset_id or 1,
        "date": transaction_date or date.today(),
        "quantity": quantity or 10.0,
        "price": price or 100.0,
        "fee": 0.0,
        "currency_id": 1,  # RUB
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


def create_test_operation(
    portfolio_id: Optional[int] = None,
    operation_type: Optional[int] = None,
    amount: Optional[float] = None,
    operation_id: Optional[int] = None,
    operation_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Создает тестовую операцию.
    
    Args:
        portfolio_id: ID портфеля
        operation_type: Тип операции
        amount: Сумма
        operation_id: ID операции
        operation_date: Дата операции
        
    Returns:
        Словарь с данными операции
    """
    return {
        "id": operation_id or 1,
        "user_id": str(uuid.uuid4()),
        "portfolio_id": portfolio_id or 1,
        "type": operation_type or 1,  # Deposit
        "amount": amount or 1000.0,
        "amount_rub": amount or 1000.0,
        "currency_id": 1,  # RUB
        "date": operation_date or date.today(),
        "asset_id": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


def create_test_portfolio_asset(
    portfolio_id: Optional[int] = None,
    asset_id: Optional[int] = None,
    portfolio_asset_id: Optional[int] = None,
    quantity: Optional[float] = None
) -> Dict[str, Any]:
    """
    Создает тестовый портфельный актив.
    
    Args:
        portfolio_id: ID портфеля
        asset_id: ID актива
        portfolio_asset_id: ID портфельного актива
        quantity: Количество
        
    Returns:
        Словарь с данными портфельного актива
    """
    return {
        "id": portfolio_asset_id or 1,
        "portfolio_id": portfolio_id or 1,
        "asset_id": asset_id or 1,
        "quantity": quantity or 10.0,
        "average_price": 100.0,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
