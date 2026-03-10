-- ============================================================================
-- СОЗДАНИЕ ИНДЕКСОВ ДЛЯ ОПТИМИЗАЦИИ ЗАПРОСОВ
-- ============================================================================
-- Этот файл содержит все необходимые индексы для оптимизации работы БД
-- Индексы создаются только если они еще не существуют (IF NOT EXISTS)
-- 
-- ВАЖНО: Перед применением проверьте, что индексы не созданы ранее
-- ============================================================================

-- ============================================================================
-- ТАБЛИЦА: portfolios
-- ============================================================================

-- Индекс для поиска портфелей пользователя (используется в get_user_portfolios)
CREATE INDEX IF NOT EXISTS idx_portfolios_user_id 
ON portfolios(user_id);

-- Индекс для поиска дочерних портфелей по родителю и имени
-- Используется в portfolio_service для поиска существующих портфелей
CREATE INDEX IF NOT EXISTS idx_portfolios_parent_name 
ON portfolios(parent_portfolio_id, name) 
WHERE parent_portfolio_id IS NOT NULL;

-- Индекс для поиска портфелей пользователя с родительским портфелем
CREATE INDEX IF NOT EXISTS idx_portfolios_user_parent 
ON portfolios(user_id, parent_portfolio_id) 
WHERE parent_portfolio_id IS NOT NULL;

-- ============================================================================
-- ТАБЛИЦА: portfolio_assets
-- ============================================================================

-- Индекс для поиска активов портфеля (используется в get_portfolio_assets)
CREATE INDEX IF NOT EXISTS idx_portfolio_assets_portfolio_id 
ON portfolio_assets(portfolio_id);

-- Индекс для поиска портфелей, содержащих актив
-- Используется в access_control_service и portfolio_service
CREATE INDEX IF NOT EXISTS idx_portfolio_assets_asset_id 
ON portfolio_assets(asset_id);

-- Составной индекс для поиска конкретного актива в портфеле
-- Используется для проверки существования и уникальности
CREATE INDEX IF NOT EXISTS idx_portfolio_assets_portfolio_asset 
ON portfolio_assets(portfolio_id, asset_id);

-- ============================================================================
-- ТАБЛИЦА: transactions
-- ============================================================================

-- Индекс для поиска транзакций портфельного актива
-- Используется в get_portfolio_transactions, get_user_transactions
CREATE INDEX IF NOT EXISTS idx_transactions_portfolio_asset_id 
ON transactions(portfolio_asset_id);

-- Индекс для сортировки транзакций по дате (DESC)
-- Используется в репозиториях для ORDER BY transaction_date DESC
CREATE INDEX IF NOT EXISTS idx_transactions_date_desc 
ON transactions(transaction_date DESC);

-- Составной индекс для поиска транзакций портфельного актива с сортировкой по дате
-- Оптимизирует запросы вида: WHERE portfolio_asset_id = X ORDER BY transaction_date DESC
CREATE INDEX IF NOT EXISTS idx_transactions_portfolio_asset_date 
ON transactions(portfolio_asset_id, transaction_date DESC);

-- Индекс для поиска транзакций пользователя
-- Используется в get_user_transactions
CREATE INDEX IF NOT EXISTS idx_transactions_user_id 
ON transactions(user_id);

-- Индекс для поиска транзакций по типу (для фильтрации продаж и погашений)
CREATE INDEX IF NOT EXISTS idx_transactions_type 
ON transactions(transaction_type) 
WHERE transaction_type IN (2, 3);

-- Индекс для поиска транзакций по дате (для фильтрации по диапазону дат)
CREATE INDEX IF NOT EXISTS idx_transactions_date 
ON transactions(transaction_date);

-- ============================================================================
-- ТАБЛИЦА: cash_operations
-- ============================================================================

-- Индекс для поиска операций пользователя
-- Используется в get_cash_operations
CREATE INDEX IF NOT EXISTS idx_cash_operations_user_id 
ON cash_operations(user_id);

-- Индекс для поиска операций портфеля
-- Используется в get_cash_operations, get_portfolio_last_operation_date
CREATE INDEX IF NOT EXISTS idx_cash_operations_portfolio_id 
ON cash_operations(portfolio_id);

-- Индекс для сортировки операций по дате (DESC)
-- Используется в репозиториях для ORDER BY date DESC
CREATE INDEX IF NOT EXISTS idx_cash_operations_date_desc 
ON cash_operations(date DESC);

-- Составной индекс для поиска операций портфеля с сортировкой по дате
-- Оптимизирует запросы вида: WHERE portfolio_id = X ORDER BY date DESC
CREATE INDEX IF NOT EXISTS idx_cash_operations_portfolio_date 
ON cash_operations(portfolio_id, date DESC);

-- Индекс для поиска операций по дате (для фильтрации по диапазону дат)
CREATE INDEX IF NOT EXISTS idx_cash_operations_date 
ON cash_operations(date);

-- Составной индекс для поиска операций портфеля по активу и типу
-- Используется в update_portfolio_asset_positions_from_date для поиска выплат, комиссий, налогов
CREATE INDEX IF NOT EXISTS idx_cash_operations_portfolio_asset_type 
ON cash_operations(portfolio_id, asset_id, type) 
WHERE asset_id IS NOT NULL;

-- Индекс для поиска операций по транзакции
-- Используется в update_portfolio_asset_positions_from_date
CREATE INDEX IF NOT EXISTS idx_cash_operations_transaction_id 
ON cash_operations(transaction_id) 
WHERE transaction_id IS NOT NULL;

-- Индекс для поиска операций по типу (для фильтрации выплат, комиссий, налогов)
CREATE INDEX IF NOT EXISTS idx_cash_operations_type 
ON cash_operations(type);

-- ============================================================================
-- ТАБЛИЦА: assets
-- ============================================================================

-- Индекс для поиска активов пользователя (кастомные активы)
-- Используется в assets_service
CREATE INDEX IF NOT EXISTS idx_assets_user_id 
ON assets(user_id) 
WHERE user_id IS NOT NULL;

-- Индекс для поиска активов по тикеру
-- Используется для поиска активов по тикеру
CREATE INDEX IF NOT EXISTS idx_assets_ticker 
ON assets(ticker) 
WHERE ticker IS NOT NULL;

-- Составной индекс для поиска активов по тикеру и пользователю
-- Используется для проверки уникальности тикера у пользователя
CREATE INDEX IF NOT EXISTS idx_assets_ticker_user 
ON assets(ticker, user_id);

-- Индекс для поиска активов по типу
-- Используется в get_portfolio_assets для JOIN с asset_types
CREATE INDEX IF NOT EXISTS idx_assets_asset_type_id 
ON assets(asset_type_id);

-- Индекс для поиска активов по валюте котировки
-- Используется в get_portfolio_assets для JOIN с quote_asset
CREATE INDEX IF NOT EXISTS idx_assets_quote_asset_id 
ON assets(quote_asset_id) 
WHERE quote_asset_id IS NOT NULL;

-- Индекс для поиска системных активов (user_id IS NULL)
-- Используется для фильтрации системных активов
CREATE INDEX IF NOT EXISTS idx_assets_system 
ON assets(user_id) 
WHERE user_id IS NULL;

-- ============================================================================
-- ТАБЛИЦА: asset_prices
-- ============================================================================

-- PRIMARY KEY уже создан на (asset_id, trade_date)
-- Индекс для поиска последней цены актива (используется в get_portfolio_assets)
-- Оптимизирует запросы вида: WHERE asset_id = X ORDER BY trade_date DESC LIMIT 1
CREATE INDEX IF NOT EXISTS idx_asset_prices_asset_date_desc 
ON asset_prices(asset_id, trade_date DESC);

-- Индекс для поиска цен по дате (для поиска курсов валют на конкретную дату)
-- Используется в update_portfolio_asset_positions_from_date
CREATE INDEX IF NOT EXISTS idx_asset_prices_date 
ON asset_prices(trade_date);

-- ============================================================================
-- ТАБЛИЦА: asset_latest_prices
-- ============================================================================

-- PRIMARY KEY уже создан на asset_id
-- Дополнительных индексов не требуется, так как все запросы идут по PRIMARY KEY

-- ============================================================================
-- ТАБЛИЦА: asset_payouts
-- ============================================================================

-- Индекс для поиска выплат актива
-- Используется в get_portfolio_assets для получения дивидендов/купонов
CREATE INDEX IF NOT EXISTS idx_asset_payouts_asset_id 
ON asset_payouts(asset_id);

-- Индекс для сортировки выплат по дате платежа (DESC)
-- Используется для ORDER BY payment_date DESC
CREATE INDEX IF NOT EXISTS idx_asset_payouts_payment_date_desc 
ON asset_payouts(asset_id, payment_date DESC);

-- ============================================================================
-- ТАБЛИЦА: portfolio_daily_positions
-- ============================================================================

-- PRIMARY KEY уже создан на (portfolio_asset_id, report_date)
-- Индекс для поиска позиций портфеля
-- Используется в update_portfolio_asset_positions_from_date
CREATE INDEX IF NOT EXISTS idx_portfolio_daily_positions_portfolio_id 
ON portfolio_daily_positions(portfolio_id);

-- Индекс для поиска последней позиции портфельного актива
-- Оптимизирует запросы вида: WHERE portfolio_asset_id = X ORDER BY report_date DESC LIMIT 1
CREATE INDEX IF NOT EXISTS idx_portfolio_daily_positions_asset_date_desc 
ON portfolio_daily_positions(portfolio_asset_id, report_date DESC);

-- Индекс для поиска позиций по дате (для фильтрации по диапазону дат)
CREATE INDEX IF NOT EXISTS idx_portfolio_daily_positions_date 
ON portfolio_daily_positions(report_date);

-- ============================================================================
-- ТАБЛИЦА: portfolio_daily_values
-- ============================================================================

-- PRIMARY KEY уже создан на (portfolio_id, report_date)
-- Индекс для поиска последнего значения портфеля
-- Оптимизирует запросы вида: WHERE portfolio_id = X ORDER BY report_date DESC LIMIT 1
CREATE INDEX IF NOT EXISTS idx_portfolio_daily_values_portfolio_date_desc 
ON portfolio_daily_values(portfolio_id, report_date DESC);

-- Индекс для поиска значений по дате (для фильтрации по диапазону дат)
CREATE INDEX IF NOT EXISTS idx_portfolio_daily_values_date 
ON portfolio_daily_values(report_date);

-- ============================================================================
-- ТАБЛИЦА: fifo_lots
-- ============================================================================

-- Индекс для поиска лотов портфельного актива
-- Используется в FIFO расчетах
CREATE INDEX IF NOT EXISTS idx_fifo_lots_portfolio_asset_id 
ON fifo_lots(portfolio_asset_id);

-- Индекс для сортировки лотов по дате создания
-- Используется для FIFO сортировки
CREATE INDEX IF NOT EXISTS idx_fifo_lots_created_at 
ON fifo_lots(portfolio_asset_id, created_at);

-- ============================================================================
-- ТАБЛИЦА: import_tasks
-- ============================================================================

-- Индекс для поиска задач пользователя
-- Используется в task_service
CREATE INDEX IF NOT EXISTS idx_import_tasks_user_id 
ON import_tasks(user_id);

-- Индекс для поиска pending задач (используется в get_next_pending_task)
CREATE INDEX IF NOT EXISTS idx_import_tasks_status 
ON import_tasks(status) 
WHERE status = 'pending';

-- Составной индекс для поиска pending задач пользователя
CREATE INDEX IF NOT EXISTS idx_import_tasks_user_status 
ON import_tasks(user_id, status) 
WHERE status = 'pending';

-- Индекс для сортировки задач по дате создания (DESC)
-- Используется в task_service для ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_import_tasks_created_at_desc 
ON import_tasks(created_at DESC);

-- Составной индекс для проверки существования токена брокера
-- Используется в broker_connections_service
CREATE INDEX IF NOT EXISTS idx_import_tasks_user_broker_token 
ON import_tasks(user_id, broker_id, broker_token) 
WHERE broker_id IS NOT NULL AND broker_token IS NOT NULL;

-- ============================================================================
-- ТАБЛИЦА: user_broker_connections
-- ============================================================================

-- Индекс для поиска соединений пользователя
-- Используется в broker_connections_service
CREATE INDEX IF NOT EXISTS idx_user_broker_connections_user_id 
ON user_broker_connections(user_id);

-- Индекс для поиска соединений портфеля
-- Используется в get_user_portfolios для JOIN
CREATE INDEX IF NOT EXISTS idx_user_broker_connections_portfolio_id 
ON user_broker_connections(portfolio_id);

-- Составной индекс для поиска соединения пользователя с портфелем и брокером
-- Используется в broker_connections_service для upsert_broker_connection
CREATE INDEX IF NOT EXISTS idx_user_broker_connections_user_portfolio_broker 
ON user_broker_connections(user_id, portfolio_id, broker_id);

-- Индекс для сортировки соединений по дате последней синхронизации (DESC)
-- Используется в broker_connections_service для ORDER BY last_sync_at DESC
CREATE INDEX IF NOT EXISTS idx_user_broker_connections_last_sync_desc 
ON user_broker_connections(user_id, last_sync_at DESC);

-- Составной индекс для проверки существования токена брокера
-- Используется в broker_connections_service для check_broker_token_exists
CREATE INDEX IF NOT EXISTS idx_user_broker_connections_user_broker_token 
ON user_broker_connections(user_id, broker_id, api_key) 
WHERE api_key IS NOT NULL;

-- ============================================================================
-- ТАБЛИЦА: users
-- ============================================================================

-- UNIQUE индекс уже создан на email
-- Дополнительных индексов не требуется

-- ============================================================================
-- СПРАВОЧНЫЕ ТАБЛИЦЫ
-- ============================================================================

-- Индексы для справочных таблиц обычно не требуются, так как они маленькие
-- Но можно добавить для консистентности:

-- asset_types - маленькая таблица, индексы не требуются
-- brokers - маленькая таблица, индексы не требуются
-- operations_type - маленькая таблица, индексы не требуются
-- transactions_type - маленькая таблица, индексы не требуются

-- ============================================================================
-- КОММЕНТАРИИ И РЕКОМЕНДАЦИИ
-- ============================================================================

-- 1. Индексы создаются с IF NOT EXISTS для безопасного повторного выполнения
-- 2. Частичные индексы (WHERE) используются для оптимизации запросов с условиями
-- 3. Составные индексы создаются в порядке использования в запросах
-- 4. Индексы для сортировки создаются с DESC для оптимизации ORDER BY DESC
-- 5. После создания индексов рекомендуется выполнить ANALYZE для обновления статистики:
--    ANALYZE portfolios;
--    ANALYZE portfolio_assets;
--    ANALYZE transactions;
--    ANALYZE cash_operations;
--    ANALYZE assets;
--    ANALYZE asset_prices;
--    ANALYZE portfolio_daily_positions;
--    ANALYZE portfolio_daily_values;
--    ANALYZE import_tasks;
--    ANALYZE user_broker_connections;

-- ============================================================================
-- ПРОВЕРКА СОЗДАННЫХ ИНДЕКСОВ
-- ============================================================================

-- Для проверки созданных индексов можно использовать:
-- SELECT schemaname, tablename, indexname, indexdef 
-- FROM pg_indexes 
-- WHERE schemaname = 'public' 
-- ORDER BY tablename, indexname;
