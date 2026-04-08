"""
API endpoints для аутентификации.
Версия 1.
"""
import secrets
from urllib.parse import urlencode
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
import httpx

from app.config import Config
from app.domain.services.user_service import (
    create_user,
    get_user_by_email,
    update_user,
    update_user_password,
    create_or_get_user_oauth,
    record_user_last_login,
)
from app.extensions import bcrypt
from app.domain.models.auth_models import (
    RegisterRequest, LoginRequest, UpdateProfileRequest, ChangePasswordRequest,
    ResendVerificationRequest,
)
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
from app.utils.response import success_response
from app.utils.jwt import create_access_token
from app.core.dependencies import get_current_user
from app.core.platform_admin import auth_user_payload
from app.infrastructure.database.database_service import (
    table_insert_async, table_select_async, table_update_async,
)
from app.infrastructure.external.mail import send_verification_email
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

RESEND_COOLDOWN_SECONDS = 60


def _generate_token() -> str:
    """URL-safe токен для ссылки подтверждения (43 символа)."""
    return secrets.token_urlsafe(32)


def _build_verify_link(token: str) -> str:
    return f"{Config.BACKEND_URL}/api/v1/auth/verify-email?token={token}"


async def _create_and_send_token(user_id: str, email: str) -> bool:
    """Инвалидирует старые токены, создаёт новый и отправляет письмо со ссылкой."""
    await table_update_async(
        "email_verification_tokens",
        {"used": True},
        filters={"user_id": user_id},
    )

    token = _generate_token()
    await table_insert_async("email_verification_tokens", {
        "user_id": user_id,
        "token": token,
    })

    link = _build_verify_link(token)
    sent = await send_verification_email(email, link)
    if not sent:
        logger.warning(f"Failed to send verification email to {email}")
    return sent


@router.post("/register", status_code=HTTPStatus.CREATED)
async def register(data: RegisterRequest):
    """Регистрация нового пользователя."""
    if await get_user_by_email(data.email):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=ErrorMessages.USER_ALREADY_EXISTS,
        )

    user = await create_user(data.email, data.password)
    user_id = str(user["id"]) if isinstance(user, dict) else str(user[0]["id"])

    await _create_and_send_token(user_id, data.email)

    return success_response(
        data={"email_sent": True},
        message="Письмо с подтверждением отправлено на email",
        status_code=HTTPStatus.CREATED,
    )


@router.get("/verify-email")
async def verify_email(token: str = ""):
    """Подтверждение email по ссылке из письма."""
    if not token:
        return RedirectResponse(
            url=f"{Config.FRONTEND_URL}/login?error=invalid_verification_token"
        )

    rows = await table_select_async(
        "email_verification_tokens",
        filters={"token": token, "used": False},
        limit=1,
    )

    if not rows:
        return RedirectResponse(
            url=f"{Config.FRONTEND_URL}/login?error=invalid_verification_token"
        )

    row = rows[0]
    now = datetime.now(timezone.utc)
    expires_at = row["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now > expires_at:
        return RedirectResponse(
            url=f"{Config.FRONTEND_URL}/login?error=verification_token_expired"
        )

    await table_update_async("email_verification_tokens", {"used": True}, filters={"id": row["id"]})
    await table_update_async("users", {"email_verified": True}, filters={"id": str(row["user_id"])})

    users = await table_select_async("users", filters={"id": str(row["user_id"])}, limit=1)
    user = users[0] if users else None

    if not user:
        return RedirectResponse(
            url=f"{Config.FRONTEND_URL}/login?error=user_not_found"
        )

    await record_user_last_login(str(user["id"]))

    jwt_token = create_access_token(identity=user["email"])

    callback_url = f"{Config.FRONTEND_URL}/auth/callback?{urlencode({'token': jwt_token})}"
    return RedirectResponse(url=callback_url)


@router.post("/resend-verification")
async def resend_verification(data: ResendVerificationRequest):
    """Повторная отправка письма с подтверждением."""
    user = await get_user_by_email(data.email)
    if not user:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Пользователь не найден")

    if user.get("email_verified"):
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Email уже подтверждён")

    last_tokens = await table_select_async(
        "email_verification_tokens",
        filters={"user_id": str(user["id"])},
        order={"column": "created_at", "desc": True},
        limit=1,
    )
    if last_tokens:
        created = last_tokens[0]["created_at"]
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - created).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            remaining = int(RESEND_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Повторная отправка возможна через {remaining} сек.",
            )

    await _create_and_send_token(str(user["id"]), data.email)

    return success_response(
        data={"email_sent": True},
        message="Письмо с подтверждением отправлено повторно",
    )


@router.post("/login")
async def login(data: LoginRequest):
    """Вход пользователя в систему."""
    user = await get_user_by_email(data.email)
    if not user or not user.get("password_hash"):
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail=ErrorMessages.INVALID_CREDENTIALS,
        )
    if not bcrypt.check_password_hash(user["password_hash"], data.password):
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail=ErrorMessages.INVALID_CREDENTIALS,
        )

    if not user.get("email_verified"):
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="email_not_verified",
        )

    await record_user_last_login(str(user["id"]))

    access_token = create_access_token(identity=data.email)

    return success_response(
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user": auth_user_payload(user),
        },
        message=SuccessMessages.LOGIN_SUCCESS,
    )


@router.get("/check-token")
async def check_token(user: dict = Depends(get_current_user)):
    """Проверка валидности JWT токена."""
    return success_response(
        data={"user": auth_user_payload(user)},
        message="Token valid",
    )


@router.put("/profile")
async def update_profile(
    data: UpdateProfileRequest,
    user: dict = Depends(get_current_user),
):
    """Обновление профиля пользователя."""
    try:
        updated_user = await update_user(
            user_id=user["id"],
            name=data.name,
            email=data.email,
        )

        if not updated_user:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Пользователь не найден",
            )

        return success_response(
            data={"user": auth_user_payload(updated_user)},
            message="Профиль успешно обновлен",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(e),
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
    user = await create_or_get_user_oauth(email=email, name=name)

    if not user.get("email_verified"):
        await table_update_async("users", {"email_verified": True}, filters={"id": str(user["id"])})

    await record_user_last_login(str(user["id"]))

    jwt_token = create_access_token(identity=email)

    callback_params = {"token": jwt_token}
    if state:
        callback_params["redirect"] = state
    callback_url = f"{Config.FRONTEND_URL}/auth/callback?{urlencode(callback_params)}"
    return RedirectResponse(url=callback_url)


@router.put("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    user: dict = Depends(get_current_user),
):
    """Смена пароля пользователя."""
    try:
        await update_user_password(
            user_id=user["id"],
            current_password=data.current_password,
            new_password=data.new_password,
        )
        return success_response(message="Пароль успешно изменён")
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(e),
        )
