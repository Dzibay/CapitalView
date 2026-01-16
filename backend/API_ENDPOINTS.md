# API Endpoints - Полный список

## Аутентификация (Auth)

### POST `/api/auth/register`
Регистрация нового пользователя

### POST `/api/auth/login`
Вход в систему и получение JWT токена

### GET `/api/auth/check-token`
Проверка валидности токена

---

## Портфели (Portfolio)

### GET `/api/portfolio/list`
Получение списка всех портфелей пользователя

### POST `/api/portfolio/add`
Создание нового портфеля

### GET `/api/portfolio/{portfolio_id}`
**НОВЫЙ** - Получение детальной информации о портфеле
- Включает активы, транзакции и историю стоимости

### GET `/api/portfolio/{portfolio_id}/summary`
**НОВЫЙ** - Получение краткой сводки по портфелю
- Активы и общая стоимость без детальной истории

### GET `/api/portfolio/{portfolio_id}/assets`
Получение активов портфеля

### GET `/api/portfolio/{portfolio_id}/history`
Получение истории стоимости портфеля

### GET `/api/portfolio/{portfolio_id}/transactions`
**НОВЫЙ** - Получение всех транзакций портфеля

### POST `/api/portfolio/{portfolio_id}/description`
Обновление описания портфеля

### POST `/api/portfolio/{portfolio_id}/clear`
Очистка портфеля (удаление всех активов)

### DELETE `/api/portfolio/{portfolio_id}/delete`
Удаление портфеля

### POST `/api/portfolio/import_broker`
Импорт портфеля из брокера

---

## Активы (Assets)

### POST `/api/assets/add`
Создание нового актива

### GET `/api/assets/{asset_id}`
**НОВЫЙ** - Получение информации об активе
- Детальная информация об активе, включая последнюю цену

### GET `/api/assets/{asset_id}/prices`
**НОВЫЙ** - Получение истории цен актива
- Параметры: `start_date`, `end_date`, `limit`

### GET `/api/assets/portfolio/{portfolio_asset_id}`
**НОВЫЙ** - Получение информации о портфельном активе
- Детальная информация о портфельном активе, включая все транзакции

### POST `/api/assets/add_price`
Добавление цены актива

### DELETE `/api/assets/{asset_id}`
Удаление актива

---

## Транзакции (Transactions)

### GET `/api/transactions/`
Получение транзакций с фильтрацией
- Параметры: `asset_name`, `portfolio_id`, `start_date`, `end_date`, `limit`

### POST `/api/transactions/`
Создание новой транзакции

---

## Дашборд (Dashboard)

### GET `/api/dashboard/`
Получение данных дашборда

---

## Аналитика (Analytics)

### GET `/api/analitics/portfolios`
Получение аналитики по всем портфелям пользователя

---

## Новые endpoints (добавлены)

### Информация об активах
- `GET /api/assets/{asset_id}` - детальная информация об активе
- `GET /api/assets/{asset_id}/prices` - история цен актива
- `GET /api/assets/portfolio/{portfolio_asset_id}` - информация о портфельном активе

### Информация о портфелях
- `GET /api/portfolio/{portfolio_id}` - детальная информация о портфеле
- `GET /api/portfolio/{portfolio_id}/summary` - краткая сводка портфеля
- `GET /api/portfolio/{portfolio_id}/transactions` - транзакции портфеля

---

## Примеры использования

### Получение информации об активе
```bash
GET /api/assets/1
Authorization: Bearer <token>
```

### Получение истории цен актива
```bash
GET /api/assets/1/prices?start_date=2024-01-01&end_date=2024-12-31&limit=100
Authorization: Bearer <token>
```

### Получение детальной информации о портфеле
```bash
GET /api/portfolio/1
Authorization: Bearer <token>
```

### Получение краткой сводки портфеля
```bash
GET /api/portfolio/1/summary
Authorization: Bearer <token>
```

---

## Swagger документация

Все endpoints документированы в Swagger UI:
```
http://localhost:5000/api/docs
```

