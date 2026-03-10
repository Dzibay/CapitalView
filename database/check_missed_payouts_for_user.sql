-- Функция для проверки неполученных выплат для всех активов пользователя
-- Вызывается после завершения импорта от брокера или вручную
CREATE OR REPLACE FUNCTION check_missed_payouts_for_user(
    p_user_id uuid
)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    v_portfolio_asset_id bigint;
    v_total_checked integer := 0;
    v_total_missed integer := 0;
    v_errors jsonb := '[]'::jsonb;
    v_error_text text;
BEGIN
    -- Проверяем все активы во всех портфелях пользователя
    FOR v_portfolio_asset_id IN 
        SELECT pa.id
        FROM portfolio_assets pa
        JOIN portfolios p ON p.id = pa.portfolio_id
        WHERE p.user_id = p_user_id
    LOOP
        BEGIN
            PERFORM check_missed_payouts(v_portfolio_asset_id);
            v_total_checked := v_total_checked + 1;
        EXCEPTION
            WHEN OTHERS THEN
                v_error_text := SQLERRM;
                v_errors := v_errors || jsonb_build_object(
                    'portfolio_asset_id', v_portfolio_asset_id,
                    'error', v_error_text
                );
                -- Продолжаем проверку других активов даже при ошибке
        END;
    END LOOP;
    
    RETURN jsonb_build_object(
        'success', true,
        'user_id', p_user_id,
        'total_checked', v_total_checked,
        'errors', v_errors,
        'errors_count', jsonb_array_length(v_errors)
    );
END;
$$;
