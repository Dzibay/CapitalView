# Тесты

## Структура

- `unit/` - Unit тесты для отдельных компонентов
- `integration/` - Integration тесты для проверки взаимодействия компонентов
- `fixtures/` - Фикстуры для тестов
- `conftest.py` - Конфигурация pytest и общие фикстуры

## Запуск тестов

```bash
# Все тесты
pytest

# Только unit тесты
pytest tests/unit/

# Только integration тесты
pytest tests/integration/

# С покрытием
pytest --cov=app tests/
```

## Примеры тестов

### Unit тесты

Тестируют отдельные функции и классы в изоляции.

Пример: `tests/unit/test_date_utils.py` - тесты для утилит работы с датами.

### Integration тесты

Тестируют взаимодействие между компонентами (например, репозитории и сервисы).

## Фикстуры

Общие фикстуры определены в `conftest.py`:
- `supabase_client` - клиент Supabase
- `portfolio_repository` - репозиторий портфелей
- `user_repository` - репозиторий пользователей
- `asset_repository` - репозиторий активов
