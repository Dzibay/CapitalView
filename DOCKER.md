# Запуск CapitalView в Docker

## Первый запуск
1. Скопируйте `.env.example` в `.env`.
2. Заполните `JWT_SECRET_KEY`, `DB_PASSWORD` и нужные ключи внешних API.
3. Выполните:

```powershell
docker compose up -d --build
```

PostgreSQL, Redis, backend, фоновые workers, scheduler, frontend и Caddy запускаются автоматически.

## Прогресс первой инициализации

Пока выполняется схема БД и первичная загрузка MOEX/крипто-справочников, смотрите:

```powershell
docker compose logs -f db-init
```

В логах будут этапы `bootstrap_schema_start`, `reference_phase_start`, `reference_phase_done` и `reference_seed_done`.

Состояние сайта:

```powershell
docker compose ps
docker compose logs -f backend caddy
```

## Повторный запуск

Обычный `docker compose up -d --build` не удаляет volumes и не повторяет первичный seed. PostgreSQL хранится в `pgdata`, Redis — в `redis_data`, а успешная версия загрузки справочника фиксируется в таблице `service_state`.

Ежедневные обновления активов, дивидендов, купонов, сплитов и крипто-справочника выполняет контейнер `reference-scheduler`. Текущие цены обновляются отдельными price-workers.

## Данные и reset

Не используйте `docker compose down -v`, если нужно сохранить базу и кэш. Эта команда удалит volumes и заставит систему выполнить первичную инициализацию заново.
