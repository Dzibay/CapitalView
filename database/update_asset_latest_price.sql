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

