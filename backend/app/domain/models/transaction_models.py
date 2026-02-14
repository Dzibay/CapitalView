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
    transaction_type: int = Field(..., description="Тип транзакции (1 = buy, 2 = sell)")
    quantity: float = Field(..., gt=0, description="Количество")
    price: float = Field(..., gt=0, description="Цена за единицу")
    transaction_date: Union[datetime, str] = Field(..., description="Дата транзакции")
    
    @field_validator('transaction_type', mode='before')
    @classmethod
    def parse_transaction_type(cls, v):
        """Преобразует тип транзакции в число: buy/1 -> 1, sell/2 -> 2."""
        if isinstance(v, int):
            if v in [1, 2]:
                return v
            raise ValueError("transaction_type должен быть 1 (buy) или 2 (sell)")
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower in ['buy', 'покупка', '1']:
                return 1
            elif v_lower in ['sell', 'продажа', '2']:
                return 2
            else:
                raise ValueError(f"Некорректный тип транзакции: {v}. Ожидается 'buy'/'sell' или 1/2")
        raise ValueError(f"transaction_type должен быть строкой или числом, получен: {type(v)}")
    
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
