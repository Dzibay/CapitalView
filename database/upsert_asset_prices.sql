CREATE OR REPLACE FUNCTION upsert_asset_prices(p_prices jsonb)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
    v_asset_id bigint;
BEGIN
    CREATE TEMP TABLE IF NOT EXISTS temp_asset_prices (
        asset_id bigint,
        price numeric(20,6),
        trade_date date
    ) ON COMMIT DROP;
    
    TRUNCATE TABLE temp_asset_prices;
    
    -- Вставляем данные в temp_asset_prices, фильтруя NULL значения
    INSERT INTO temp_asset_prices (asset_id, price, trade_date)
    SELECT 
        (x->>'asset_id')::bigint,
        (x->>'price')::numeric(20,6),
        (x->>'trade_date')::date
    FROM jsonb_array_elements(p_prices) t(x)
    WHERE (x->>'asset_id') IS NOT NULL
      AND (x->>'price') IS NOT NULL
      AND (x->>'trade_date') IS NOT NULL;
    
    -- Удаляем дубликаты в temp_asset_prices, оставляя одну запись для каждого (asset_id, trade_date)
    -- Используем DISTINCT ON для выбора записи с максимальной ценой (последняя по времени)
    CREATE TEMP TABLE IF NOT EXISTS temp_asset_prices_unique (
        asset_id bigint,
        price numeric(20,6),
        trade_date date
    ) ON COMMIT DROP;
    
    TRUNCATE TABLE temp_asset_prices_unique;
    
    INSERT INTO temp_asset_prices_unique (asset_id, price, trade_date)
    SELECT DISTINCT ON (asset_id, trade_date)
        asset_id, price, trade_date
    FROM temp_asset_prices
    ORDER BY asset_id, trade_date, price DESC;
    
    -- Проверяем существование активов перед вставкой
    INSERT INTO asset_prices (asset_id, price, trade_date)
    SELECT t.asset_id, t.price, t.trade_date
    FROM temp_asset_prices_unique t
    WHERE EXISTS (SELECT 1 FROM assets a WHERE a.id = t.asset_id)
    ON CONFLICT (asset_id, trade_date) DO UPDATE
    SET price = EXCLUDED.price;
    
    -- Оптимизировано: один batch-вызов вместо цикла
    BEGIN
        PERFORM update_asset_latest_prices_batch(
            ARRAY(SELECT DISTINCT asset_id FROM temp_asset_prices_unique)
        );
    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'Ошибка при обновлении последних цен активов: %', SQLERRM;
    END;
    
    RETURN true; 
END;
$$;

COMMENT ON FUNCTION upsert_asset_prices(jsonb) IS 'Массовое добавление/обновление цен активов';