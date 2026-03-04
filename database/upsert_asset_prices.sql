-- ============================================================================
-- Функция для массового добавления/обновления цен активов
-- Перезаписывает существующие цены для той же даты и актива
-- ============================================================================

CREATE OR REPLACE FUNCTION upsert_asset_prices(p_prices jsonb)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
    v_asset_id bigint;
BEGIN
    -- Используем временную таблицу для эффективного upsert
    CREATE TEMP TABLE IF NOT EXISTS temp_asset_prices (
        asset_id bigint,
        price real,
        trade_date timestamp
    ) ON COMMIT DROP;
    
    -- Очищаем временную таблицу
    TRUNCATE TABLE temp_asset_prices;
    
    -- Вставляем данные во временную таблицу
    INSERT INTO temp_asset_prices (asset_id, price, trade_date)
    SELECT 
        (x->>'asset_id')::bigint,
        (x->>'price')::real,
        (x->>'trade_date')::timestamp
    FROM jsonb_array_elements(p_prices) t(x);
    
    -- Обновляем существующие записи (по дате без учета времени)
    UPDATE asset_prices ap
    SET 
        price = t.price,
        trade_date = t.trade_date
    FROM temp_asset_prices t
    WHERE ap.asset_id = t.asset_id
      AND DATE(ap.trade_date) = DATE(t.trade_date);
    
    -- Вставляем новые записи (которые не были обновлены)
    INSERT INTO asset_prices (asset_id, price, trade_date)
    SELECT t.asset_id, t.price, t.trade_date
    FROM temp_asset_prices t
    WHERE NOT EXISTS (
        SELECT 1 
        FROM asset_prices ap
        WHERE ap.asset_id = t.asset_id
          AND DATE(ap.trade_date) = DATE(t.trade_date)
    );
    
    -- Обновляем asset_latest_prices_full для всех затронутых активов
    -- Используем DISTINCT, чтобы обновить каждый актив только один раз
    FOR v_asset_id IN 
        SELECT DISTINCT asset_id FROM temp_asset_prices
    LOOP
        BEGIN
            PERFORM update_asset_latest_price(v_asset_id);
        EXCEPTION WHEN OTHERS THEN
            -- Логируем ошибку, но продолжаем обработку других активов
            RAISE WARNING 'Ошибка при обновлении последней цены актива %: %', v_asset_id, SQLERRM;
        END;
    END LOOP;
    
    RETURN true; 
END;
$$;

COMMENT ON FUNCTION upsert_asset_prices(jsonb) IS 
'Массовое добавление/обновление цен активов. Перезаписывает существующие цены для той же даты и актива.';