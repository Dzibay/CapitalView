-- ============================================================================
-- СОЗДАНИЕ ИНДЕКСОВ ДЛЯ ОПТИМИЗАЦИИ ЗАПРОСОВ
-- ============================================================================
-- Оптимизировано: удалены дублирующие и бесполезные индексы,
-- добавлены составные и covering индексы для тяжёлых аналитических запросов
-- ============================================================================

-- ============================================================================
-- ТАБЛИЦА: portfolios
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_portfolios_user_id 
ON portfolios(user_id);

CREATE INDEX IF NOT EXISTS idx_portfolios_parent_name 
ON portfolios(parent_portfolio_id, name) 
WHERE parent_portfolio_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_portfolios_user_parent 
ON portfolios(user_id, parent_portfolio_id) 
WHERE parent_portfolio_id IS NOT NULL;

-- ============================================================================
-- ТАБЛИЦА: portfolio_assets
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_portfolio_assets_portfolio_id 
ON portfolio_assets(portfolio_id);

CREATE INDEX IF NOT EXISTS idx_portfolio_assets_asset_id 
ON portfolio_assets(asset_id);

CREATE INDEX IF NOT EXISTS idx_portfolio_assets_portfolio_asset 
ON portfolio_assets(portfolio_id, asset_id);

-- ============================================================================
-- ТАБЛИЦА: transactions
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_transactions_portfolio_asset_id 
ON transactions(portfolio_asset_id);

-- Единый индекс на дату (DESC покрывает ASC-сканирование в обратном направлении)
CREATE INDEX IF NOT EXISTS idx_transactions_date_desc 
ON transactions(transaction_date DESC);

CREATE INDEX IF NOT EXISTS idx_transactions_portfolio_asset_date 
ON transactions(portfolio_asset_id, transaction_date DESC);

CREATE INDEX IF NOT EXISTS idx_transactions_user_id 
ON transactions(user_id);

CREATE INDEX IF NOT EXISTS idx_transactions_type 
ON transactions(transaction_type) 
WHERE transaction_type IN (2, 3);

-- ============================================================================
-- ТАБЛИЦА: cash_operations
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_cash_operations_user_id 
ON cash_operations(user_id);

CREATE INDEX IF NOT EXISTS idx_cash_operations_portfolio_id 
ON cash_operations(portfolio_id);

-- Единый индекс на дату (DESC покрывает ASC-сканирование)
CREATE INDEX IF NOT EXISTS idx_cash_operations_date_desc 
ON cash_operations(date DESC);

CREATE INDEX IF NOT EXISTS idx_cash_operations_portfolio_date 
ON cash_operations(portfolio_id, date DESC);

CREATE INDEX IF NOT EXISTS idx_cash_operations_portfolio_asset_type 
ON cash_operations(portfolio_id, asset_id, type) 
WHERE asset_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_cash_operations_transaction_id 
ON cash_operations(transaction_id) 
WHERE transaction_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_cash_operations_type 
ON cash_operations(type);

-- НОВЫЕ: составные индексы для аналитических запросов (get_user_portfolios_analytics)
CREATE INDEX IF NOT EXISTS idx_cash_operations_portfolio_type_covering
ON cash_operations(portfolio_id, type)
INCLUDE (amount, amount_rub, date, asset_id);

CREATE INDEX IF NOT EXISTS idx_cash_operations_portfolio_asset_type_date
ON cash_operations(portfolio_id, asset_id, type, date)
WHERE asset_id IS NOT NULL AND type IN (3, 4);

-- ============================================================================
-- ТАБЛИЦА: assets
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_assets_user_id 
ON assets(user_id) 
WHERE user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_assets_ticker 
ON assets(ticker) 
WHERE ticker IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_assets_ticker_user 
ON assets(ticker, user_id);

CREATE INDEX IF NOT EXISTS idx_assets_asset_type_id 
ON assets(asset_type_id);

CREATE INDEX IF NOT EXISTS idx_assets_quote_asset_id 
ON assets(quote_asset_id) 
WHERE quote_asset_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_assets_system 
ON assets(user_id) 
WHERE user_id IS NULL;

-- ============================================================================
-- ТАБЛИЦА: asset_prices
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_asset_prices_asset_date_desc 
ON asset_prices(asset_id, trade_date DESC);

-- ============================================================================
-- ТАБЛИЦА: asset_payouts
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_asset_payouts_asset_id 
ON asset_payouts(asset_id);

CREATE INDEX IF NOT EXISTS idx_asset_payouts_payment_date_desc 
ON asset_payouts(asset_id, payment_date DESC);

-- НОВЫЙ: для фильтрации по нормализованному type
CREATE INDEX IF NOT EXISTS idx_asset_payouts_asset_type
ON asset_payouts(asset_id, type)
WHERE type IS NOT NULL;

-- ============================================================================
-- ТАБЛИЦА: portfolio_daily_positions
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_portfolio_daily_positions_portfolio_id 
ON portfolio_daily_positions(portfolio_id);

CREATE INDEX IF NOT EXISTS idx_portfolio_daily_positions_asset_date_desc 
ON portfolio_daily_positions(portfolio_asset_id, report_date DESC);

-- НОВЫЙ: covering index для аналитических CTE
CREATE INDEX IF NOT EXISTS idx_pdp_covering
ON portfolio_daily_positions(portfolio_asset_id, report_date DESC)
INCLUDE (payouts, commissions, realized_pnl, position_value, quantity, portfolio_id);

-- ============================================================================
-- ТАБЛИЦА: portfolio_daily_values
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_portfolio_daily_values_portfolio_date_desc 
ON portfolio_daily_values(portfolio_id, report_date DESC);

-- ============================================================================
-- ТАБЛИЦА: fifo_lots
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_fifo_lots_portfolio_asset_id 
ON fifo_lots(portfolio_asset_id);

CREATE INDEX IF NOT EXISTS idx_fifo_lots_created_at 
ON fifo_lots(portfolio_asset_id, created_at);

-- ============================================================================
-- ТАБЛИЦА: import_tasks
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_import_tasks_user_id 
ON import_tasks(user_id);

CREATE INDEX IF NOT EXISTS idx_import_tasks_status 
ON import_tasks(status) 
WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_import_tasks_user_status 
ON import_tasks(user_id, status) 
WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_import_tasks_created_at_desc 
ON import_tasks(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_import_tasks_user_broker_token 
ON import_tasks(user_id, broker_id, broker_token) 
WHERE broker_id IS NOT NULL AND broker_token IS NOT NULL;

-- ============================================================================
-- ТАБЛИЦА: user_broker_connections
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_user_broker_connections_user_id 
ON user_broker_connections(user_id);

CREATE INDEX IF NOT EXISTS idx_user_broker_connections_portfolio_id 
ON user_broker_connections(portfolio_id);

CREATE INDEX IF NOT EXISTS idx_user_broker_connections_user_portfolio_broker 
ON user_broker_connections(user_id, portfolio_id, broker_id);

CREATE INDEX IF NOT EXISTS idx_user_broker_connections_last_sync_desc 
ON user_broker_connections(user_id, last_sync_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_broker_connections_user_broker_token 
ON user_broker_connections(user_id, broker_id, api_key) 
WHERE api_key IS NOT NULL;

-- ============================================================================
-- ТАБЛИЦА: missed_payouts
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_missed_payouts_user_id ON missed_payouts(user_id);
CREATE INDEX IF NOT EXISTS idx_missed_payouts_portfolio_id ON missed_payouts(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_missed_payouts_portfolio_asset_id ON missed_payouts(portfolio_asset_id);
CREATE INDEX IF NOT EXISTS idx_missed_payouts_asset_id ON missed_payouts(asset_id);
CREATE INDEX IF NOT EXISTS idx_missed_payouts_payout_id ON missed_payouts(payout_id);
CREATE INDEX IF NOT EXISTS idx_missed_payouts_created_at ON missed_payouts(created_at DESC);

-- ============================================================================
-- УДАЛЕНИЕ ДУБЛИРУЮЩИХ И БЕСПОЛЕЗНЫХ ИНДЕКСОВ
-- (standalone date-индексы без portfolio/asset контекста)
-- ============================================================================

DROP INDEX IF EXISTS idx_transactions_date;
DROP INDEX IF EXISTS idx_cash_operations_date;
DROP INDEX IF EXISTS idx_portfolio_daily_positions_date;
DROP INDEX IF EXISTS idx_portfolio_daily_values_date;
DROP INDEX IF EXISTS idx_asset_prices_date;
