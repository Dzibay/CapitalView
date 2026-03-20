DROP FUNCTION IF EXISTS delete_portfolio_asset(bigint);
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
BEGIN
    SELECT 
        pa.asset_id,
        pa.portfolio_id,
        COALESCE(at.is_custom, false)
    INTO 
        v_asset_id,
        v_portfolio_id,
        v_is_custom
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
    
    -- Операции по паре портфель+актив (в т.ч. с transaction_id; FK не ведёт на portfolio_assets)
    DELETE FROM cash_operations
    WHERE portfolio_id = v_portfolio_id
      AND asset_id = v_asset_id;

    -- Каскад: transactions (+ cash по transaction_id), fifo_lots, portfolio_asset_daily_values, missed_payouts
    DELETE FROM portfolio_assets
    WHERE id = p_portfolio_asset_id;
    
    IF v_is_custom THEN
        IF NOT EXISTS (
            SELECT 1 FROM portfolio_assets 
            WHERE asset_id = v_asset_id
        ) THEN
            DELETE FROM cash_operations
            WHERE asset_id = v_asset_id;
            
            DELETE FROM asset_prices 
            WHERE asset_id = v_asset_id;
            
            DELETE FROM asset_latest_prices 
            WHERE asset_id = v_asset_id;
            
            DELETE FROM assets 
            WHERE id = v_asset_id;
        END IF;
    END IF;
    
    BEGIN
        PERFORM update_portfolio_values_from_date(v_portfolio_id, '0001-01-01'::date);
    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'Ошибка при обновлении истории портфеля: %', SQLERRM;
    END;
    
    RETURN json_build_object(
        'success', true,
        'message', 'Актив и связанные записи успешно удалены',
        'portfolio_id', v_portfolio_id,
        'asset_id', v_asset_id,
        'is_custom', v_is_custom
    )::text;
    
EXCEPTION WHEN OTHERS THEN
    RETURN json_build_object(
        'success', false,
        'error', format('Ошибка при удалении актива: %s', SQLERRM)
    )::text;
END;
$$;
