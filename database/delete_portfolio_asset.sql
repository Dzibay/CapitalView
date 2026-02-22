drop function delete_portfolio_asset;
CREATE OR REPLACE FUNCTION delete_portfolio_asset(
    p_portfolio_asset_id bigint
)
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
    v_asset_id bigint;
    v_portfolio_id bigint;
    v_is_custom boolean;
    v_user_id uuid;
    v_result text;
BEGIN
    -- Начинаем транзакцию (автоматически в PostgreSQL)
    
    -- 1. Получаем информацию об активе и проверяем существование
    SELECT 
        pa.asset_id,
        pa.portfolio_id,
        COALESCE(at.is_custom, false),
        p.user_id
    INTO 
        v_asset_id,
        v_portfolio_id,
        v_is_custom,
        v_user_id
    FROM portfolio_assets pa
    JOIN portfolios p ON p.id = pa.portfolio_id
    JOIN assets a ON a.id = pa.asset_id
    LEFT JOIN asset_types at ON at.id = a.asset_type_id
    WHERE pa.id = p_portfolio_asset_id;
    
    IF v_asset_id IS NULL THEN
        RETURN json_build_object(
            'success', false,
            'error', format('Портфельный актив с ID %s не найден', p_portfolio_asset_id)
        )::text;
    END IF;
    
    -- 2. Удаляем транзакции (CASCADE должен удалить связанные записи)
    DELETE FROM transactions 
    WHERE portfolio_asset_id = p_portfolio_asset_id;
    
    -- 3. Удаляем FIFO лоты
    DELETE FROM fifo_lots 
    WHERE portfolio_asset_id = p_portfolio_asset_id;
    
    -- 4. Удаляем ежедневные позиции
    DELETE FROM portfolio_daily_positions 
    WHERE portfolio_asset_id = p_portfolio_asset_id;
    
    -- 5. Удаляем запись portfolio_assets
    DELETE FROM portfolio_assets 
    WHERE id = p_portfolio_asset_id;
    
    -- 6. Если актив кастомный - удаляем его полностью
    IF v_is_custom THEN
        -- Проверяем, используется ли актив в других портфелях
        IF NOT EXISTS (
            SELECT 1 FROM portfolio_assets 
            WHERE asset_id = v_asset_id
        ) THEN
            -- Удаляем историю цен актива
            DELETE FROM asset_prices 
            WHERE asset_id = v_asset_id;
            
            -- Удаляем запись из asset_latest_prices_full
            DELETE FROM asset_latest_prices_full 
            WHERE asset_id = v_asset_id;
            
            -- Удаляем сам актив
            DELETE FROM assets 
            WHERE id = v_asset_id;
        END IF;
    END IF;
    
    -- 7. Обновляем историю портфеля (не критично, если не удастся)
    BEGIN
        PERFORM update_portfolio_values_from_date(v_portfolio_id, '0001-01-01'::date);
    EXCEPTION WHEN OTHERS THEN
        -- Логируем ошибку, но не прерываем выполнение
        RAISE WARNING 'Ошибка при обновлении истории портфеля: %', SQLERRM;
    END;
    
    -- Возвращаем успешный результат
    RETURN json_build_object(
        'success', true,
        'message', 'Актив и связанные записи успешно удалены',
        'portfolio_id', v_portfolio_id,
        'asset_id', v_asset_id,
        'is_custom', v_is_custom
    )::text;
    
EXCEPTION WHEN OTHERS THEN
    -- В случае ошибки транзакция автоматически откатывается
    RETURN json_build_object(
        'success', false,
        'error', format('Ошибка при удалении актива: %s', SQLERRM)
    )::text;
END;
$$;
