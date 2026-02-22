"""
Pydantic модели для активов.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Union
from datetime import datetime


class CreateAssetRequest(BaseModel):
    """Модель запроса создания актива."""
    name: str = Field(..., min_length=1, description="Название актива")
    asset_type: str = Field(..., description="Тип актива")
    currency: Optional[str] = Field("RUB", description="Валюта актива")
    ticker: Optional[str] = Field(None, description="Тикер актива")
    isin: Optional[str] = Field(None, description="ISIN актива")
    description: Optional[dict] = Field(default_factory=dict, description="Дополнительное описание")


class AddAssetPriceRequest(BaseModel):
    """Модель запроса добавления цены актива."""
    asset_id: int = Field(..., ge=1, description="ID актива")
    price: float = Field(..., gt=0, description="Цена актива")
    date: Union[datetime, str] = Field(..., description="Дата цены")
    source: Optional[str] = Field(None, description="Источник цены")
    
    @field_validator('date', mode='before')
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


class MoveAssetRequest(BaseModel):
    """Модель запроса перемещения актива между портфелями."""
    target_portfolio_id: int = Field(..., ge=1, description="ID целевого портфеля")


class BatchAddPriceRequest(BaseModel):
    """Модель запроса массового добавления цен актива."""
    asset_id: int = Field(..., ge=1, description="ID актива")
    prices: list = Field(..., min_length=1, description="Список цен с датами")
    
    @field_validator('prices')
    @classmethod
    def validate_prices(cls, v):
        """Валидирует список цен."""
        if not isinstance(v, list):
            raise ValueError("prices должен быть списком")
        for price_item in v:
            if not isinstance(price_item, dict):
                raise ValueError("Каждый элемент prices должен быть словарем")
            if 'price' not in price_item or 'date' not in price_item:
                raise ValueError("Каждый элемент prices должен содержать 'price' и 'date'")
            if price_item['price'] <= 0:
                raise ValueError("Цена должна быть больше 0")
        return v