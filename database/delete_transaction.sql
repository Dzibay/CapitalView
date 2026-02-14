-- ============================================================================
-- Функция безопасного удаления транзакции с пересчетом FIFO
-- ============================================================================
-- При удалении транзакции:
-- 1. Удаляет транзакцию (триггер удалит связанную cash_operation)
-- 2. Пересчитывает FIFO для всех оставшихся транзакций этого portfolio_asset
--    используя rebuild_fifo_for_portfolio_asset
-- 3. Обновляет portfolio_asset и историю портфеля
-- ============================================================================

CREATE OR REPLACE FUNCTION delete_transaction(p_transaction_id bigint)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
    v_tx_record record;
    v_portfolio_asset_id bigint;
    v_portfolio_id bigint;
    v_transaction_date date;
BEGIN
    -- 1. Получаем информацию о транзакции
    SELECT 
        t.id,
        t.portfolio_asset_id,
        t.transaction_type,
        t.quantity,
        t.price,
        t.transaction_date::date,
        t.user_id,
        pa.portfolio_id
    INTO v_tx_record
    FROM transactions t
    JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
    WHERE t.id = p_transaction_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Транзакция % не найдена', p_transaction_id;
    END IF;
    
    v_portfolio_asset_id := v_tx_record.portfolio_asset_id;
    v_portfolio_id := v_tx_record.portfolio_id;
    v_transaction_date := v_tx_record.transaction_date;
    
    -- 2. Удаляем транзакцию (триггер delete_cash_operation_on_tx_delete удалит связанную cash_operation)
    DELETE FROM transactions WHERE id = p_transaction_id;
    
    -- 3. Пересчитываем FIFO для всех оставшихся транзакций этого portfolio_asset
    -- Используем rebuild_fifo_for_portfolio_asset для упрощения логики
    PERFORM rebuild_fifo_for_portfolio_asset(v_portfolio_asset_id);
    
    -- 4. Обновляем portfolio_asset
    -- Функция update_portfolio_asset принимает один параметр pa_id
    PERFORM update_portfolio_asset(v_portfolio_asset_id);
    
    -- 5. Обновляем историю портфеля с даты удаленной транзакции
    PERFORM update_portfolio_asset_positions_from_date(
        v_portfolio_asset_id,
        v_transaction_date
    );
    
    PERFORM update_portfolio_values_from_date(
        v_portfolio_id,
        v_transaction_date
    );
    
    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        -- В случае ошибки откатываем транзакцию
        RAISE;
END;
$$;

-- Комментарий к функции
COMMENT ON FUNCTION delete_transaction(bigint) IS 
'Безопасно удаляет транзакцию с пересчетом FIFO. Удаляет транзакцию и пересчитывает FIFO для всех оставшихся транзакций этого portfolio_asset.';
