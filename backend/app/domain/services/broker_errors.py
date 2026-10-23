"""
Ошибки обращения к брокеру: понятное пользователю сообщение и решение, повторять ли импорт.

Неверный или отозванный токен повтором не исправить — задача сразу завершается,
подключение помечается token_invalid, автосинхронизация по нему не запускается,
пока пользователь не обновит токен. Сбои связи и лимиты брокера — повторяем с паузой.
"""
from dataclasses import dataclass
from typing import Iterator, Optional

from app.core.broker_secrets import BrokerTokenUnavailable

CODE_TOKEN_INVALID = "token_invalid"
CODE_BROKER_UNAVAILABLE = "broker_unavailable"
CODE_IMPORT_ABORTED = "import_aborted"
CODE_UNKNOWN = "unknown"

_GRPC_AUTH_CODES = {"UNAUTHENTICATED", "PERMISSION_DENIED"}
_GRPC_TRANSIENT_CODES = {"UNAVAILABLE", "DEADLINE_EXCEEDED", "RESOURCE_EXHAUSTED", "ABORTED", "INTERNAL"}

TOKEN_INVALID_MESSAGE = (
    "Брокер отклонил токен: он недействителен, отозван или истёк. "
    "Создайте новый токен и обновите его в разделе «Подключения брокеров». "
    "Данные портфеля не изменены."
)
BROKER_UNAVAILABLE_MESSAGE = (
    "Брокер временно недоступен или ограничил число запросов. "
    "Повторим автоматически, данные портфеля не изменены."
)


class ImportAborted(Exception):
    """Импорт невозможен, и повтор не поможет (нет подключения, портфель удалён и т.п.)."""


@dataclass(frozen=True)
class BrokerErrorInfo:
    code: str
    message: str  # для пользователя
    retryable: bool

    @property
    def token_invalid(self) -> bool:
        return self.code == CODE_TOKEN_INVALID


def _chain(exc: Optional[BaseException]) -> Iterator[BaseException]:
    seen = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        yield exc
        exc = exc.__cause__ or exc.__context__


def _http_status(exc: BaseException) -> Optional[int]:
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    return status if isinstance(status, int) else None


def _is_transport_error(exc: BaseException) -> bool:
    try:
        import httpx
    except ImportError:  # pragma: no cover
        return False
    return isinstance(exc, (httpx.TransportError, httpx.TimeoutException))


def classify_broker_error(exc: BaseException) -> BrokerErrorInfo:
    for e in _chain(exc):
        if isinstance(e, BrokerTokenUnavailable):
            return BrokerErrorInfo(CODE_TOKEN_INVALID, str(e), retryable=False)
        if isinstance(e, ImportAborted):
            return BrokerErrorInfo(CODE_IMPORT_ABORTED, str(e), retryable=False)

        # t_tech.invest RequestError: code — grpc.StatusCode
        grpc_code = getattr(getattr(e, "code", None), "name", None)
        if grpc_code in _GRPC_AUTH_CODES:
            return BrokerErrorInfo(CODE_TOKEN_INVALID, TOKEN_INVALID_MESSAGE, retryable=False)
        if grpc_code in _GRPC_TRANSIENT_CODES:
            return BrokerErrorInfo(CODE_BROKER_UNAVAILABLE, BROKER_UNAVAILABLE_MESSAGE, retryable=True)

        # БКС (httpx): OAuth отвечает 400 invalid_grant / 401 на неверный refresh-токен
        status = _http_status(e)
        if status in (400, 401, 403):
            url = str(getattr(getattr(e, "request", None), "url", "") or "")
            if status != 400 or "openid-connect/token" in url:
                return BrokerErrorInfo(CODE_TOKEN_INVALID, TOKEN_INVALID_MESSAGE, retryable=False)
        if status == 429 or (status is not None and status >= 500):
            return BrokerErrorInfo(CODE_BROKER_UNAVAILABLE, BROKER_UNAVAILABLE_MESSAGE, retryable=True)
        if _is_transport_error(e):
            return BrokerErrorInfo(CODE_BROKER_UNAVAILABLE, BROKER_UNAVAILABLE_MESSAGE, retryable=True)

    text = str(exc) or exc.__class__.__name__
    if "данные портфеля не изменены" not in text:
        text = f"{text}. Данные портфеля не изменены."
    return BrokerErrorInfo(CODE_UNKNOWN, f"Не удалось импортировать портфель: {text}", retryable=True)
