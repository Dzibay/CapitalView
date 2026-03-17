"""
API endpoints для аутентификации.
Версия 1.
"""
from urllib.parse import urlencode
from fastapi import APIRouter, HTTPException, Depends
from app.config import Config
from fastapi.responses import RedirectResponse
import httpx
from app.domain.services.user_service import create_user, get_user_by_email, update_user, update_user_password, create_or_get_user_oauth
from app.extensions import bcrypt
from app.domain.models.auth_models import RegisterRequest, LoginRequest, UpdateProfileRequest, ChangePasswordRequest
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
from app.utils.response import success_response
from app.utils.jwt import create_access_token
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


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
    user = get_user_by_email(data.email)
    if not user or not user.get("password_hash"):
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail=ErrorMessages.INVALID_CREDENTIALS
        )
    if not bcrypt.check_password_hash(user["password_hash"], data.password):
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


@router.get("/google")
async def google_login(state: str = None):
    """Редирект на страницу авторизации Google."""
    if not Config.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth не настроен")
    
    redirect_uri = f"{Config.BACKEND_URL}/api/v1/auth/google/callback"
    
    params = {
        "client_id": Config.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    if state:
        params["state"] = state
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
async def google_callback(code: str = None, error: str = None, state: str = None):
    """Обработка callback от Google OAuth."""
    if error:
        return RedirectResponse(
            url=f"{Config.FRONTEND_URL}/login?error={error}"
        )
    if not code:
        return RedirectResponse(
            url=f"{Config.FRONTEND_URL}/login?error=no_code"
        )
    if not Config.GOOGLE_CLIENT_ID or not Config.GOOGLE_CLIENT_SECRET:
        return RedirectResponse(
            url=f"{Config.FRONTEND_URL}/login?error=oauth_not_configured"
        )
    
    redirect_uri = f"{Config.BACKEND_URL}/api/v1/auth/google/callback"
    
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": Config.GOOGLE_CLIENT_ID,
                "client_secret": Config.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_resp.status_code != 200:
            return RedirectResponse(
                url=f"{Config.FRONTEND_URL}/login?error=token_exchange_failed"
            )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return RedirectResponse(
                url=f"{Config.FRONTEND_URL}/login?error=no_access_token"
            )
        
        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_resp.status_code != 200:
            return RedirectResponse(
                url=f"{Config.FRONTEND_URL}/login?error=userinfo_failed"
            )
        userinfo = userinfo_resp.json()
    
    email = userinfo.get("email")
    if not email:
        return RedirectResponse(
            url=f"{Config.FRONTEND_URL}/login?error=no_email"
        )
    
    name = userinfo.get("name") or userinfo.get("given_name", "")
    user = create_or_get_user_oauth(email=email, name=name)
    jwt_token = create_access_token(identity=email)
    
    callback_params = {"token": jwt_token}
    if state:
        callback_params["redirect"] = state
    callback_url = f"{Config.FRONTEND_URL}/auth/callback?{urlencode(callback_params)}"
    return RedirectResponse(url=callback_url)


@router.put("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    user: dict = Depends(get_current_user)
):
    """Смена пароля пользователя."""
    try:
        update_user_password(
            user_id=user["id"],
            current_password=data.current_password,
            new_password=data.new_password
        )
        return success_response(message="Пароль успешно изменён")
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(e)
        )
