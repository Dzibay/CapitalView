-- ============================================================================
-- ОПТИМИЗАЦИЯ ТАБЛИЦ portfolio_daily_positions И portfolio_daily_values
-- ============================================================================
-- Этот файл содержит критически важные индексы для ускорения запросов

-- ============================================================================
-- ИНДЕКСЫ ДЛЯ portfolio_daily_positions
-- ============================================================================

-- Для быстрого поиска позиций по портфелю (используется в refresh_daily_data_for_user)
CREATE INDEX IF NOT EXISTS idx_portfolio_daily_positions_portfolio_id 
    ON portfolio_daily_positions(portfolio_id);

-- Композитный индекс для поиска позиций по портфелю и дате
CREATE INDEX IF NOT EXISTS idx_portfolio_daily_positions_portfolio_date 
    ON portfolio_daily_positions(portfolio_id, tx_date);

-- Для JOIN с portfolio_assets (уже есть в PRIMARY KEY, но добавлено для оптимизации запросов)
-- PRIMARY KEY уже создает индекс на (portfolio_asset_id, tx_date)

-- ============================================================================
-- ИНДЕКСЫ ДЛЯ portfolio_daily_values
-- ============================================================================

-- PRIMARY KEY уже создает индекс на (portfolio_id, report_date)
-- Добавим дополнительный индекс для сортировки по дате (если нужно искать по всем портфелям)
CREATE INDEX IF NOT EXISTS idx_portfolio_daily_values_date 
    ON portfolio_daily_values(report_date);

-- Индекс для обратного поиска (поиск последних записей портфеля)
-- Используется для получения актуальных данных
CREATE INDEX IF NOT EXISTS idx_portfolio_daily_values_portfolio_date_desc 
    ON portfolio_daily_values(portfolio_id, report_date DESC);

-- ============================================================================
-- ЧАСТИЧНЫЕ ИНДЕКСЫ ДЛЯ ОПТИМИЗАЦИИ
-- ============================================================================

-- Индекс только для недавних данных (последний год) - ускорит частые запросы
CREATE INDEX IF NOT EXISTS idx_portfolio_daily_values_recent 
    ON portfolio_daily_values(portfolio_id, report_date DESC) 
    WHERE report_date >= CURRENT_DATE - INTERVAL '1 year';

-- Аналогично для positions (если нужны только последние данные)
-- CREATE INDEX IF NOT EXISTS idx_portfolio_daily_positions_recent 
--     ON portfolio_daily_positions(portfolio_id, tx_date DESC) 
--     WHERE tx_date >= CURRENT_DATE - INTERVAL '1 year';

-- ============================================================================
-- ОБНОВЛЕНИЕ СТАТИСТИКИ
-- ============================================================================

ANALYZE portfolio_daily_positions;
ANALYZE portfolio_daily_values;

-- ============================================================================
-- ПРОВЕРКА СОЗДАННЫХ ИНДЕКСОВ
-- ============================================================================

-- Выполните этот запрос для проверки:
-- SELECT 
--     tablename,
--     indexname,
--     indexdef
-- FROM pg_indexes
-- WHERE schemaname = 'public'
--   AND tablename IN ('portfolio_daily_positions', 'portfolio_daily_values')
-- ORDER BY tablename, indexname;



