"""
Pydantic модели для аутентификации.
"""
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Модель запроса регистрации."""
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., min_length=4, description="Пароль (минимум 4 символа)")


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
    new_password: str = Field(..., min_length=4, description="Новый пароль (минимум 4 символа)")
