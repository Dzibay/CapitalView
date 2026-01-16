"""
Pydantic модели для транзакций.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Union
from datetime import datetime


class CreateTransactionRequest(BaseModel):
    """Модель запроса создания транзакции."""
    portfolio_asset_id: int = Field(..., ge=1, description="ID портфельного актива")
    asset_id: int = Field(..., ge=1, description="ID актива")
    transaction_type: str = Field(..., description="Тип транзакции (buy/sell)")
    quantity: float = Field(..., gt=0, description="Количество")
    price: float = Field(..., gt=0, description="Цена за единицу")
    transaction_date: Union[datetime, str] = Field(..., description="Дата транзакции")
    commission: Optional[float] = Field(0.0, ge=0, description="Комиссия")
    currency: Optional[str] = Field("RUB", description="Валюта транзакции")
    notes: Optional[str] = Field(None, description="Примечания")
    
    @field_validator('transaction_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        """Парсит дату из строки или datetime."""
        if isinstance(v, str):
            try:
                # Пробуем разные форматы
                if 'T' in v:
                    return datetime.fromisoformat(v.replace('Z', '+00:00'))
                else:
                    return datetime.fromisoformat(v)
            except:
                return v
        return v


class GetTransactionsQuery(BaseModel):
    """Модель запроса получения транзакций (query parameters)."""
    asset_name: Optional[str] = Field(None, description="Фильтр по названию актива")
    portfolio_id: Optional[int] = Field(None, ge=1, description="Фильтр по ID портфеля")
    start_date: Optional[Union[datetime, str]] = Field(None, description="Начальная дата периода")
    end_date: Optional[Union[datetime, str]] = Field(None, description="Конечная дата периода")
    limit: Optional[int] = Field(None, ge=1, le=1000, description="Лимит записей")

