"""
API endpoints для аутентификации.
Версия 1.
"""
from fastapi import APIRouter, HTTPException, Depends
from app.domain.services.user_service import create_user, get_user_by_email, update_user
from app.extensions import bcrypt
from app.domain.models.auth_models import RegisterRequest, LoginRequest, UpdateProfileRequest
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
from app.utils.response import success_response
from app.utils.jwt import create_access_token
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=HTTPStatus.CREATED)
async def register(data: RegisterRequest):
    """Регистрация нового пользователя."""
    # Проверка существования пользователя
    if get_user_by_email(data.email):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=ErrorMessages.USER_ALREADY_EXISTS
        )
    
    # Создание пользователя
    create_user(data.email, data.password)
    
    return success_response(
        message=SuccessMessages.USER_CREATED,
        status_code=HTTPStatus.CREATED
    )


@router.post("/login")
async def login(data: LoginRequest):
    """Вход пользователя в систему."""
    # Проверка пользователя
    user = get_user_by_email(data.email)
    if not user or not bcrypt.check_password_hash(user["password_hash"], data.password):
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail=ErrorMessages.INVALID_CREDENTIALS
        )
    
    # Создание токена
    access_token = create_access_token(identity=data.email)
    
    return success_response(
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "email": user["email"]
            }
        },
        message=SuccessMessages.LOGIN_SUCCESS
    )


@router.get("/check-token")
async def check_token(user: dict = Depends(get_current_user)):
    """Проверка валидности JWT токена."""
    return success_response(
        data={
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user.get("name")
            }
        },
        message="Token valid"
    )


@router.put("/profile")
async def update_profile(
    data: UpdateProfileRequest,
    user: dict = Depends(get_current_user)
):
    """Обновление профиля пользователя."""
    try:
        updated_user = update_user(
            user_id=user["id"],
            name=data.name,
            email=data.email
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        return success_response(
            data={
                "user": {
                    "id": updated_user["id"],
                    "email": updated_user["email"],
                    "name": updated_user.get("name")
                }
            },
            message="Профиль успешно обновлен"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(e)
        )
