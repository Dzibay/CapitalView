"""
Pydantic модели для аутентификации.
"""
import re
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
    """Модель запроса обновления профиля."""
    name: str = Field(None, description="Имя пользователя")
    email: EmailStr = Field(None, description="Email пользователя")


class ChangePasswordRequest(BaseModel):
    """Модель запроса смены пароля."""
    current_password: str = Field(..., description="Текущий пароль")
    new_password: str = Field(..., min_length=8, description="Новый пароль (мин. 8 символов, буквы и цифры)")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return _validate_password_strength(v)
