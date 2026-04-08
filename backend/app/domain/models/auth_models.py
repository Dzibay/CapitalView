"""
Pydantic модели для аутентификации.
"""
import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


def _validate_password_strength(v: str) -> str:
    """Пароль: минимум 8 символов, хотя бы одна буква и одна цифра."""
    if len(v) < 8:
        raise ValueError("Пароль должен быть не менее 8 символов")
    if not re.search(r"[a-zA-Z]", v):
        raise ValueError("Пароль должен содержать хотя бы одну букву")
    if not re.search(r"\d", v):
        raise ValueError("Пароль должен содержать хотя бы одну цифру")
    return v


class RegisterRequest(BaseModel):
    """Модель запроса регистрации."""
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., min_length=8, description="Пароль (мин. 8 символов, буквы и цифры)")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class LoginRequest(BaseModel):
    """Модель запроса входа."""
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., description="Пароль")


class AuthResponse(BaseModel):
    """Модель ответа аутентификации."""
    access_token: str = Field(..., description="JWT токен доступа")
    user: dict = Field(default=None, description="Данные пользователя")


class UpdateProfileRequest(BaseModel):
    """Модель запроса обновления профиля (email меняется только через поддержку)."""
    name: str = Field(..., min_length=1, max_length=200, description="Имя пользователя")

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("Имя не может быть пустым")
        return s


class ChangePasswordRequest(BaseModel):
    """Смена пароля; текущий не нужен, если у аккаунта ещё нет пароля (вход через Google)."""
    current_password: Optional[str] = Field(
        default=None,
        description="Текущий пароль (обязателен, если пароль уже задан)",
    )
    new_password: str = Field(..., min_length=8, description="Новый пароль (мин. 8 символов, буквы и цифры)")

    @field_validator("current_password", mode="before")
    @classmethod
    def empty_current_to_none(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v.strip() if isinstance(v, str) else v

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class ResendVerificationRequest(BaseModel):
    """Повторная отправка письма с подтверждением."""
    email: EmailStr
