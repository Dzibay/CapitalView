-- Альтернативный вариант: таблица вместо materialized view
-- Преимущества:
-- 1. Можно обновлять частично (только измененные активы)
-- 2. Быстрее обновление отдельных записей
-- 3. Можно использовать триггеры для автоматического обновления
-- 
-- Недостатки:
-- 1. Требует больше места на диске
-- 2. Нужно управлять обновлениями вручную

-- Создание таблицы
CREATE TABLE IF NOT EXISTS asset_latest_prices_full_table (
    asset_id BIGINT PRIMARY KEY REFERENCES assets(id),
    today_price REAL,
    today_date DATE,
    yesterday_price REAL,
    yesterday_date DATE,
    curr_price REAL,
    curr_date DATE,
    prev_price REAL,
    prev_date DATE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индекс на updated_at для отслеживания устаревших записей
CREATE INDEX IF NOT EXISTS idx_asset_latest_prices_updated 
    ON asset_latest_prices_full_table(updated_at);

-- Функция для обновления одной записи (для частичных обновлений)
CREATE OR REPLACE FUNCTION update_asset_latest_price(p_asset_id BIGINT)
RETURNS VOID AS $$
BEGIN
    INSERT INTO asset_latest_prices_full_table (
        asset_id,
        today_price,
        today_date,
        yesterday_price,
        yesterday_date,
        curr_price,
        curr_date,
        prev_price,
        prev_date,
        updated_at
    )
    SELECT 
        a.id AS asset_id,
        (SELECT ap.price FROM asset_prices ap 
         WHERE ap.asset_id = a.id AND ap.trade_date::date = CURRENT_DATE 
         ORDER BY ap.trade_date DESC LIMIT 1) AS today_price,
        (SELECT ap.trade_date::date FROM asset_prices ap 
         WHERE ap.asset_id = a.id AND ap.trade_date::date = CURRENT_DATE 
         ORDER BY ap.trade_date DESC LIMIT 1) AS today_date,
        (SELECT ap.price FROM asset_prices ap 
         WHERE ap.asset_id = a.id AND ap.trade_date::date = CURRENT_DATE - 1 
         ORDER BY ap.trade_date DESC LIMIT 1) AS yesterday_price,
        (SELECT ap.trade_date::date FROM asset_prices ap 
         WHERE ap.asset_id = a.id AND ap.trade_date::date = CURRENT_DATE - 1 
         ORDER BY ap.trade_date DESC LIMIT 1) AS yesterday_date,
        COALESCE(
            (SELECT ap.price FROM asset_prices ap 
             WHERE ap.asset_id = a.id AND ap.trade_date::date IN (CURRENT_DATE, CURRENT_DATE - 1) 
             ORDER BY ap.trade_date DESC LIMIT 1),
            (SELECT ap.price FROM asset_prices ap 
             WHERE ap.asset_id = a.id ORDER BY ap.trade_date DESC LIMIT 1)
        ) AS curr_price,
        COALESCE(
            (SELECT ap.trade_date::date FROM asset_prices ap 
             WHERE ap.asset_id = a.id AND ap.trade_date::date IN (CURRENT_DATE, CURRENT_DATE - 1) 
             ORDER BY ap.trade_date DESC LIMIT 1),
            (SELECT ap.trade_date::date FROM asset_prices ap 
             WHERE ap.asset_id = a.id ORDER BY ap.trade_date DESC LIMIT 1)
        ) AS curr_date,
        (SELECT ap.price FROM asset_prices ap 
         WHERE ap.asset_id = a.id AND ap.trade_date < 
             (SELECT MAX(ap2.trade_date) FROM asset_prices ap2 WHERE ap2.asset_id = a.id)
         ORDER BY ap.trade_date DESC LIMIT 1) AS prev_price,
        (SELECT ap.trade_date::date FROM asset_prices ap 
         WHERE ap.asset_id = a.id AND ap.trade_date < 
             (SELECT MAX(ap2.trade_date) FROM asset_prices ap2 WHERE ap2.asset_id = a.id)
         ORDER BY ap.trade_date DESC LIMIT 1) AS prev_date,
        CURRENT_TIMESTAMP AS updated_at
    FROM assets a
    WHERE a.id = p_asset_id
    ON CONFLICT (asset_id) DO UPDATE SET
        today_price = EXCLUDED.today_price,
        today_date = EXCLUDED.today_date,
        yesterday_price = EXCLUDED.yesterday_price,
        yesterday_date = EXCLUDED.yesterday_date,
        curr_price = EXCLUDED.curr_price,
        curr_date = EXCLUDED.curr_date,
        prev_price = EXCLUDED.prev_price,
        prev_date = EXCLUDED.prev_date,
        updated_at = EXCLUDED.updated_at;
END;
$$ LANGUAGE plpgsql;

-- Функция для полного обновления таблицы (использует оптимизированный запрос)
CREATE OR REPLACE FUNCTION refresh_asset_latest_prices()
RETURNS VOID AS $$
BEGIN
    -- Используем оптимизированный запрос из asset_latest_prices_full_optimized.sql
    INSERT INTO asset_latest_prices_full (
        asset_id,
        today_price,
        today_date,
        yesterday_price,
        yesterday_date,
        curr_price,
        curr_date,
        prev_price,
        prev_date,
        updated_at
    )
    WITH ranked_prices AS (
        SELECT 
            asset_id,
            price,
            trade_date,
            trade_date::date AS price_date,
            ROW_NUMBER() OVER (PARTITION BY asset_id, trade_date::date ORDER BY trade_date DESC) AS date_rank,
            ROW_NUMBER() OVER (PARTITION BY asset_id ORDER BY trade_date DESC) AS all_rank,
            CASE WHEN trade_date::date IN (CURRENT_DATE, CURRENT_DATE - 1)
                 THEN ROW_NUMBER() OVER (PARTITION BY asset_id ORDER BY trade_date DESC)
                 ELSE NULL
            END AS recent_rank
        FROM asset_prices
    ),
    aggregated AS (
        SELECT 
            asset_id,
            MAX(CASE WHEN price_date = CURRENT_DATE AND date_rank = 1 THEN price END) AS today_price,
            MAX(CASE WHEN price_date = CURRENT_DATE AND date_rank = 1 THEN price_date END) AS today_date,
            MAX(CASE WHEN price_date = CURRENT_DATE - 1 AND date_rank = 1 THEN price END) AS yesterday_price,
            MAX(CASE WHEN price_date = CURRENT_DATE - 1 AND date_rank = 1 THEN price_date END) AS yesterday_date,
            MAX(CASE WHEN recent_rank = 1 THEN price END) AS recent_price,
            MAX(CASE WHEN recent_rank = 1 THEN price_date END) AS recent_date,
            MAX(CASE WHEN all_rank = 1 THEN price END) AS latest_price,
            MAX(CASE WHEN all_rank = 1 THEN price_date END) AS latest_date,
            MAX(CASE WHEN all_rank = 2 THEN price END) AS prev_price,
            MAX(CASE WHEN all_rank = 2 THEN price_date END) AS prev_date
        FROM ranked_prices
        GROUP BY asset_id
    )
    SELECT 
        a.id AS asset_id,
        ag.today_price,
        ag.today_date,
        ag.yesterday_price,
        ag.yesterday_date,
        COALESCE(ag.recent_price, ag.latest_price) AS curr_price,
        COALESCE(ag.recent_date, ag.latest_date) AS curr_date,
        ag.prev_price,
        ag.prev_date,
        CURRENT_TIMESTAMP AS updated_at
    FROM assets a
    LEFT JOIN aggregated ag ON ag.asset_id = a.id
    ON CONFLICT (asset_id) DO UPDATE SET
        today_price = EXCLUDED.today_price,
        today_date = EXCLUDED.today_date,
        yesterday_price = EXCLUDED.yesterday_price,
        yesterday_date = EXCLUDED.yesterday_date,
        curr_price = EXCLUDED.curr_price,
        curr_date = EXCLUDED.curr_date,
        prev_price = EXCLUDED.prev_price,
        prev_date = EXCLUDED.prev_date,
        updated_at = EXCLUDED.updated_at;
END;
$$ LANGUAGE plpgsql;

-- Функция для массового обновления нескольких активов (для использования после массовых операций)
CREATE OR REPLACE FUNCTION update_asset_latest_prices_batch(p_asset_ids BIGINT[])
RETURNS VOID AS $$
BEGIN
    -- Используем оптимизированный запрос для обновления только указанных активов
    INSERT INTO asset_latest_prices_full_table (
        asset_id,
        today_price,
        today_date,
        yesterday_price,
        yesterday_date,
        curr_price,
        curr_date,
        prev_price,
        prev_date,
        updated_at
    )
    WITH ranked_prices AS (
        SELECT 
            asset_id,
            price,
            trade_date,
            trade_date::date AS price_date,
            ROW_NUMBER() OVER (PARTITION BY asset_id, trade_date::date ORDER BY trade_date DESC) AS date_rank,
            ROW_NUMBER() OVER (PARTITION BY asset_id ORDER BY trade_date DESC) AS all_rank,
            CASE WHEN trade_date::date IN (CURRENT_DATE, CURRENT_DATE - 1)
                 THEN ROW_NUMBER() OVER (PARTITION BY asset_id ORDER BY trade_date DESC)
                 ELSE NULL
            END AS recent_rank
        FROM asset_prices
        WHERE asset_id = ANY(p_asset_ids)
    ),
    aggregated AS (
        SELECT 
            asset_id,
            MAX(CASE WHEN price_date = CURRENT_DATE AND date_rank = 1 THEN price END) AS today_price,
            MAX(CASE WHEN price_date = CURRENT_DATE AND date_rank = 1 THEN price_date END) AS today_date,
            MAX(CASE WHEN price_date = CURRENT_DATE - 1 AND date_rank = 1 THEN price END) AS yesterday_price,
            MAX(CASE WHEN price_date = CURRENT_DATE - 1 AND date_rank = 1 THEN price_date END) AS yesterday_date,
            MAX(CASE WHEN recent_rank = 1 THEN price END) AS recent_price,
            MAX(CASE WHEN recent_rank = 1 THEN price_date END) AS recent_date,
            MAX(CASE WHEN all_rank = 1 THEN price END) AS latest_price,
            MAX(CASE WHEN all_rank = 1 THEN price_date END) AS latest_date,
            MAX(CASE WHEN all_rank = 2 THEN price END) AS prev_price,
            MAX(CASE WHEN all_rank = 2 THEN price_date END) AS prev_date
        FROM ranked_prices
        GROUP BY asset_id
    )
    SELECT 
        a.id AS asset_id,
        ag.today_price,
        ag.today_date,
        ag.yesterday_price,
        ag.yesterday_date,
        COALESCE(ag.recent_price, ag.latest_price) AS curr_price,
        COALESCE(ag.recent_date, ag.latest_date) AS curr_date,
        ag.prev_price,
        ag.prev_date,
        CURRENT_TIMESTAMP AS updated_at
    FROM assets a
    LEFT JOIN aggregated ag ON ag.asset_id = a.id
    WHERE a.id = ANY(p_asset_ids)
    ON CONFLICT (asset_id) DO UPDATE SET
        today_price = EXCLUDED.today_price,
        today_date = EXCLUDED.today_date,
        yesterday_price = EXCLUDED.yesterday_price,
        yesterday_date = EXCLUDED.yesterday_date,
        curr_price = EXCLUDED.curr_price,
        curr_date = EXCLUDED.curr_date,
        prev_price = EXCLUDED.prev_price,
        prev_date = EXCLUDED.prev_date,
        updated_at = EXCLUDED.updated_at;
END;
$$ LANGUAGE plpgsql;

-- Триггер для автоматического обновления при добавлении/изменении цены
-- ⚠️ ВНИМАНИЕ: Триггер НЕ рекомендуется использовать при массовых операциях!
-- При массовом обновлении цен (например, обновление истории всех активов) триггер
-- будет срабатывать для каждой строки, что очень медленно.
-- 
-- Рекомендация: 
-- 1. НЕ создавайте триггер, если у вас есть массовые операции
-- 2. Обновляйте таблицу вручную после массовых операций через:
--    - update_asset_latest_prices_batch() для нескольких активов
--    - refresh_asset_latest_prices() для всех активов
-- 3. Используйте триггер ТОЛЬКО если у вас нет массовых операций

CREATE OR REPLACE FUNCTION trigger_update_asset_latest_price()
RETURNS TRIGGER AS $$
BEGIN
    -- Обновляем только один актив (для единичных операций)
    PERFORM update_asset_latest_price(NEW.asset_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Создание триггера (НЕ рекомендуется при наличии массовых операций!)
-- Раскомментируйте ТОЛЬКО если у вас нет массовых обновлений цен
-- 
-- CREATE TRIGGER asset_prices_update_latest_price
--     AFTER INSERT OR UPDATE ON asset_prices
--     FOR EACH ROW
--     EXECUTE FUNCTION trigger_update_asset_latest_price();

