"""
Подключения брокеров: проверка токена, список подключений, синхронизация, замена токена.

Токен брокера в ответы не попадает — только маска (••••abcd).
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_subscriber as get_current_user
from app.utils.response import success_response
from app.constants import HTTPStatus
from app.core.logging import get_logger
from app.domain.models.portfolio_models import (
    BrokerTokenCheckRequest,
    BrokerTokenUpdateRequest,
    BrokerConnectionUpdateRequest,
)
from app.domain.services.broker_connections_service import (
    SYNC_STATUS_TOKEN_INVALID,
    check_broker_token_exists,
    delete_connection,
    enqueue_connection_syncs,
    get_user_connection,
    list_user_broker_connections,
    replace_connection_token,
    set_connection_auto_sync,
    validate_broker_token,
)
from app.domain.services.broker_errors import classify_broker_error, CODE_BROKER_UNAVAILABLE

logger = get_logger(__name__)

router = APIRouter(prefix="/broker-connections", tags=["broker-connections"])

TOKEN_REJECTED_MESSAGE = (
    "Брокер не принял токен. Проверьте, что он скопирован целиком, не отозван и не истёк."
)
NO_ACCOUNTS_MESSAGE = (
    "По этому токену брокер не показал ни одного счёта. При создании токена "
    "выберите доступ ко всем счетам или к нужному счёту."
)
BROKER_DOWN_MESSAGE = "Брокер сейчас не отвечает. Попробуйте через минуту."


def _error(status_code: int, message: str, error_code: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"success": False, "error": message, "error_code": error_code},
    )


async def _check_token_or_raise(broker_id: int, token: str) -> list:
    """Спрашивает у брокера список счетов; ошибку переводит в понятный ответ API."""
    try:
        accounts = await validate_broker_token(broker_id, token)
    except ValueError as e:
        raise _error(HTTPStatus.BAD_REQUEST, str(e), "BROKER_NOT_SUPPORTED")
    except Exception as e:
        info = classify_broker_error(e)
        logger.info("Проверка токена брокера %s не прошла: %s (%s)", broker_id, info.code, e)
        if info.token_invalid:
            raise _error(HTTPStatus.BAD_REQUEST, TOKEN_REJECTED_MESSAGE, "TOKEN_INVALID")
        if info.code == CODE_BROKER_UNAVAILABLE:
            raise _error(HTTPStatus.SERVICE_UNAVAILABLE, BROKER_DOWN_MESSAGE, "BROKER_UNAVAILABLE")
        raise _error(
            HTTPStatus.BAD_GATEWAY,
            "Не удалось проверить токен у брокера. Попробуйте ещё раз чуть позже.",
            "BROKER_ERROR",
        )
    if not accounts:
        raise _error(HTTPStatus.BAD_REQUEST, NO_ACCOUNTS_MESSAGE, "NO_ACCOUNTS")
    return accounts


async def _owned_connection_or_404(user_id, connection_id: int) -> dict:
    conn = await get_user_connection(user_id, connection_id)
    if not conn:
        raise _error(HTTPStatus.NOT_FOUND, "Подключение не найдено", "CONNECTION_NOT_FOUND")
    return conn


def _sync_message(results: list) -> str:
    started = [r for r in results if r.get("task_id")]
    need_token = [r for r in results if r.get("skipped") == SYNC_STATUS_TOKEN_INVALID]
    parts = []
    if started:
        parts.append(f"Обновляем портфелей: {len(started)}")
    if need_token:
        names = ", ".join(f"«{r.get('portfolio_name') or r['portfolio_id']}»" for r in need_token)
        parts.append(f"нужен новый токен: {names}")
    if not parts:
        return "Нет подключённых брокеров для обновления"
    return "; ".join(parts)


@router.get("/")
async def list_connections_route(user: dict = Depends(get_current_user)):
    """Подключения брокеров пользователя со статусом последней синхронизации."""
    connections = await list_user_broker_connections(user["id"])
    return success_response(data={"connections": connections})


@router.post("/check-token")
async def check_token_route(data: BrokerTokenCheckRequest, user: dict = Depends(get_current_user)):
    """Проверяет токен у брокера до импорта и показывает, какие счета будут загружены."""
    accounts = await _check_token_or_raise(data.broker_id, data.token)
    existing = await check_broker_token_exists(user["id"], data.broker_id, data.token)
    return success_response(
        data={
            "accounts": accounts,
            "already_connected": (
                {"portfolio_id": existing.get("portfolio_id"), "portfolio_name": existing.get("portfolio_name")}
                if existing.get("exists") else None
            ),
        },
        message="Токен принят брокером",
    )


@router.post("/sync", status_code=HTTPStatus.ACCEPTED)
async def sync_all_route(user: dict = Depends(get_current_user)):
    """«Обновить портфели»: синхронизация всех подключений по сохранённым токенам."""
    results = await enqueue_connection_syncs(user["id"])
    return success_response(
        data={"results": results, "tasks": [r for r in results if r.get("task_id")]},
        message=_sync_message(results),
        status_code=HTTPStatus.ACCEPTED,
    )


@router.post("/{connection_id}/sync", status_code=HTTPStatus.ACCEPTED)
async def sync_connection_route(connection_id: int, user: dict = Depends(get_current_user)):
    conn = await _owned_connection_or_404(user["id"], connection_id)
    results = await enqueue_connection_syncs(user["id"], portfolio_ids=[conn["portfolio_id"]])
    result = results[0] if results else {"skipped": "no_token"}
    if result.get("skipped") == SYNC_STATUS_TOKEN_INVALID:
        raise _error(
            HTTPStatus.CONFLICT,
            "Брокер отклонил сохранённый токен. Укажите новый токен — синхронизация запустится сразу.",
            "TOKEN_INVALID",
        )
    if not result.get("task_id"):
        raise _error(HTTPStatus.BAD_REQUEST, "Для подключения не сохранён токен", "NO_TOKEN")
    return success_response(data=result, message="Синхронизация запущена", status_code=HTTPStatus.ACCEPTED)


@router.put("/{connection_id}/token")
async def replace_token_route(
    connection_id: int,
    data: BrokerTokenUpdateRequest,
    user: dict = Depends(get_current_user),
):
    """Заменить токен (истёк или отозван). Новый токен сначала проверяется у брокера."""
    conn = await _owned_connection_or_404(user["id"], connection_id)
    await _check_token_or_raise(int(conn["broker_id"]), data.token)
    existing = await check_broker_token_exists(user["id"], int(conn["broker_id"]), data.token)
    if existing.get("exists") and existing.get("portfolio_id") != conn["portfolio_id"]:
        raise _error(
            HTTPStatus.BAD_REQUEST,
            f"Этот токен уже подключён к портфелю «{existing.get('portfolio_name')}»",
            "TOKEN_IN_USE",
        )
    await replace_connection_token(user["id"], connection_id, data.token)
    task = None
    if data.sync_now:
        results = await enqueue_connection_syncs(user["id"], portfolio_ids=[conn["portfolio_id"]])
        task = next((r for r in results if r.get("task_id")), None)
    return success_response(
        data={"task": task},
        message="Токен обновлён" + (", синхронизация запущена" if task else ""),
    )


@router.patch("/{connection_id}")
async def update_connection_route(
    connection_id: int,
    data: BrokerConnectionUpdateRequest,
    user: dict = Depends(get_current_user),
):
    await _owned_connection_or_404(user["id"], connection_id)
    if data.auto_sync is not None:
        await set_connection_auto_sync(user["id"], connection_id, data.auto_sync)
    return success_response(message="Настройки подключения сохранены")


@router.delete("/{connection_id}")
async def delete_connection_route(connection_id: int, user: dict = Depends(get_current_user)):
    """Отключить брокера: токен удаляется, импортированные данные остаются в портфеле."""
    await _owned_connection_or_404(user["id"], connection_id)
    await delete_connection(user["id"], connection_id)
    return success_response(message="Брокер отключён. Данные портфеля сохранены.")
