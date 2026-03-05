CREATE OR REPLACE FUNCTION get_portfolio_last_operation_date(
    p_portfolio_id bigint
)
RETURNS timestamp without time zone
LANGUAGE plpgsql
AS $$
DECLARE
    v_last_tx_date timestamp without time zone;
    v_last_op_date timestamp without time zone;
    v_result timestamp without time zone;
BEGIN
    -- Получаем дату последней транзакции
    SELECT MAX(t.transaction_date)
    INTO v_last_tx_date
    FROM transactions t
    JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
    WHERE pa.portfolio_id = p_portfolio_id;
    
    -- Получаем дату последней денежной операции
    SELECT MAX(co.date)
    INTO v_last_op_date
    FROM cash_operations co
    WHERE co.portfolio_id = p_portfolio_id;
    
    -- Возвращаем максимальную дату из двух (или NULL, если обе NULL)
    SELECT GREATEST(
        COALESCE(v_last_tx_date, '1970-01-01'::timestamp),
        COALESCE(v_last_op_date, '1970-01-01'::timestamp)
    )
    INTO v_result;
    
    -- Если обе даты NULL, возвращаем NULL
    IF v_last_tx_date IS NULL AND v_last_op_date IS NULL THEN
        RETURN NULL;
    END IF;
    
    RETURN v_result;
END;
$$;

COMMENT ON FUNCTION get_portfolio_last_operation_date IS 'Возвращает дату последней операции в портфеле';
