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
    currency: Optional[str] = Field(None, description="Валюта цены")
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
