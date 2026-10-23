"""
Pydantic модели для портфелей.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Union
from datetime import datetime


class CreatePortfolioRequest(BaseModel):
    """Модель запроса создания портфеля."""
    name: str = Field(..., min_length=1, description="Название портфеля")
    parent_portfolio_id: Optional[int] = Field(None, description="ID родительского портфеля")
    description: Optional[dict] = Field(default_factory=dict, description="Описание портфеля")
    
    @field_validator('description', mode='before')
    @classmethod
    def normalize_description(cls, v):
        """Преобразует пустую строку или None в пустой словарь."""
        if v is None:
            return {}
        if isinstance(v, str):
            if v.strip() == '':
                return {}
            # Если строка не пустая, пытаемся распарсить как JSON
            try:
                import json
                parsed = json.loads(v)
                return parsed if isinstance(parsed, dict) else {}
            except:
                return {}
        if isinstance(v, dict):
            return v
        return {}


class UpdatePortfolioDescriptionRequest(BaseModel):
    """Модель запроса обновления описания портфеля."""
    text: Optional[str] = Field(None, description="Текст описания")
    capital_target_name: Optional[str] = Field(None, description="Название цели по капиталу")
    capital_target_value: Optional[float] = Field(None, ge=0, description="Значение цели по капиталу")
    capital_target_deadline: Optional[Union[datetime, str]] = Field(None, description="Срок достижения цели")
    capital_target_currency: Optional[str] = Field("RUB", description="Валюта цели")
    monthly_contribution: Optional[float] = Field(None, ge=0, description="Ежемесячные пополнения")
    annual_return: Optional[float] = Field(None, ge=0, le=100, description="Годовая доходность в процентах")
    use_inflation: Optional[bool] = Field(None, description="Учитывать инфляцию")
    inflation_rate: Optional[float] = Field(None, ge=0, le=100, description="Уровень инфляции в процентах")
    
    @field_validator('capital_target_deadline', mode='before')
    @classmethod
    def parse_date(cls, v):
        """Парсит дату из строки или datetime."""
        if isinstance(v, str):
            try:
                if 'T' in v:
                    return datetime.fromisoformat(v.replace('Z', '+00:00'))
                else:
                    return datetime.fromisoformat(v)
            except:
                return v
        return v


class ImportBrokerRequest(BaseModel):
    """Модель запроса импорта брокера."""
    broker_id: int = Field(..., ge=1, description="ID брокера")
    token: str = Field(..., min_length=1, description="Токен или API-ключ брокера")
    portfolio_id: Optional[int] = Field(None, description="ID существующего портфеля")
    portfolio_name: Optional[str] = Field(None, description="Название нового портфеля")

    @field_validator("token")
    @classmethod
    def strip_token(cls, v: str) -> str:
        # Токен часто копируют с пробелом или переводом строки
        v = (v or "").strip()
        if not v:
            raise ValueError("Укажите токен брокера")
        return v


class BrokerTokenCheckRequest(BaseModel):
    """Проверка токена брокера до импорта."""
    broker_id: int = Field(..., ge=1, description="ID брокера")
    token: str = Field(..., min_length=1, description="Токен или API-ключ брокера")

    @field_validator("token")
    @classmethod
    def strip_token(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Укажите токен брокера")
        return v


class BrokerTokenUpdateRequest(BaseModel):
    """Новый токен для существующего подключения."""
    token: str = Field(..., min_length=1, description="Новый токен или API-ключ брокера")
    sync_now: bool = Field(True, description="Сразу запустить синхронизацию")

    @field_validator("token")
    @classmethod
    def strip_token(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Укажите токен брокера")
        return v


class BrokerConnectionUpdateRequest(BaseModel):
    """Настройки подключения брокера."""
    auto_sync: Optional[bool] = Field(None, description="Ежедневная автосинхронизация")

