"""
Pydantic модели для аутентификации.
"""
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Модель запроса регистрации."""
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., min_length=6, description="Пароль (минимум 6 символов)")


class LoginRequest(BaseModel):
    """Модель запроса входа."""
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., description="Пароль")


class AuthResponse(BaseModel):
    """Модель ответа аутентификации."""
    access_token: str = Field(..., description="JWT токен доступа")
    user: dict = Field(default=None, description="Данные пользователя")

