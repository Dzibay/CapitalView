"""
Константы приложения.
Централизованное хранение всех констант для удобства поддержки.
"""

# Коды брокеров
class BrokerID:
    """Идентификаторы брокеров."""
    TINKOFF = 1
    BYBIT = 2
    # Добавьте других брокеров по мере необходимости


# HTTP статус коды (для удобства)
class HTTPStatus:
    """HTTP статус коды."""
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_SERVER_ERROR = 500


# Сообщения об ошибках
class ErrorMessages:
    """Стандартные сообщения об ошибках."""
    USER_NOT_FOUND = "Пользователь не найден"
    USER_ALREADY_EXISTS = "Пользователь уже существует"
    INVALID_CREDENTIALS = "Неверные учетные данные"
    PORTFOLIO_NOT_FOUND = "Портфель не найден"
    ASSET_NOT_FOUND = "Актив не найден"
    UNAUTHORIZED = "Требуется аутентификация"
    FORBIDDEN = "Доступ запрещен"
    VALIDATION_ERROR = "Ошибка валидации данных"
    INTERNAL_ERROR = "Внутренняя ошибка сервера"
    PARENT_PORTFOLIO_CANNOT_BE_DELETED = "Невозможно удалить портфель, который является родительским для других портфелей"


# Сообщения об успехе
class SuccessMessages:
    """Стандартные сообщения об успехе."""
    USER_CREATED = "Пользователь успешно создан"
    LOGIN_SUCCESS = "Успешный вход в систему"
    PORTFOLIO_CREATED = "Портфель успешно создан"
    PORTFOLIO_DELETED = "Портфель успешно удален"
    PORTFOLIO_UPDATED = "Портфель успешно обновлен"
    TRANSACTION_CREATED = "Транзакция успешно создана"
    BROKER_IMPORT_SUCCESS = "Импорт брокера завершен успешно"

