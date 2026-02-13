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