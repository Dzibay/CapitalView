-- ============================================================================
-- Функция безопасного batch удаления операций с пересчетом аналитики
-- ============================================================================
-- При удалении операций:
-- 1. Удаляет связанные транзакции (если операция связана с транзакцией)
-- 2. Удаляет операции из cash_operations
-- 3. Пересчитывает FIFO для затронутых portfolio_assets
-- 4. Обновляет историю портфелей с минимальной даты удаленных операций
-- 5. Аналитика пересчитывается автоматически при следующем запросе
-- ============================================================================

CREATE OR REPLACE FUNCTION delete_operations_batch(p_operation_ids bigint[])
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    v_op_record record;
    v_portfolio_ids bigint[];
    v_portfolio_asset_ids bigint[];
    v_min_date date;
    v_portfolio_id bigint;
    v_portfolio_asset_id bigint;
    v_transaction_ids bigint[];
    v_deleted_count int := 0;
    v_deleted_transactions_count int := 0;
BEGIN
    -- Проверяем, что массив не пустой
    IF array_length(p_operation_ids, 1) IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Массив ID операций пуст',
            'deleted_count', 0
        );
    END IF;
    
    -- 1. Получаем информацию о всех операциях и собираем уникальные portfolio_id и transaction_ids
    SELECT 
        array_agg(DISTINCT co.portfolio_id) FILTER (WHERE co.portfolio_id IS NOT NULL),
        array_agg(DISTINCT co.transaction_id) FILTER (WHERE co.transaction_id IS NOT NULL),
        MIN(co.date::date)
    INTO v_portfolio_ids, v_transaction_ids, v_min_date
    FROM cash_operations co
    WHERE co.id = ANY(p_operation_ids);
    
    -- Инициализируем массивы если они NULL
    IF v_portfolio_ids IS NULL THEN
        v_portfolio_ids := ARRAY[]::bigint[];
    END IF;
    IF v_transaction_ids IS NULL THEN
        v_transaction_ids := ARRAY[]::bigint[];
    END IF;
    
    -- 2. Если есть связанные транзакции, получаем portfolio_asset_ids для пересчета FIFO
    IF array_length(v_transaction_ids, 1) > 0 THEN
        SELECT 
            array_agg(DISTINCT t.portfolio_asset_id) FILTER (WHERE t.portfolio_asset_id IS NOT NULL)
        INTO v_portfolio_asset_ids
        FROM transactions t
        WHERE t.id = ANY(v_transaction_ids);
        
        IF v_portfolio_asset_ids IS NULL THEN
            v_portfolio_asset_ids := ARRAY[]::bigint[];
        END IF;
    ELSE
        v_portfolio_asset_ids := ARRAY[]::bigint[];
    END IF;
    
    -- 3. Удаляем операции, связанные с транзакциями (если есть)
    -- Сначала удаляем эти операции, чтобы избежать проблем с внешними ключами
    IF array_length(v_transaction_ids, 1) > 0 THEN
        DELETE FROM cash_operations WHERE transaction_id = ANY(v_transaction_ids);
    END IF;
    
    -- 4. Удаляем транзакции напрямую (если есть)
    IF array_length(v_transaction_ids, 1) > 0 THEN
        DELETE FROM transactions WHERE id = ANY(v_transaction_ids);
        GET DIAGNOSTICS v_deleted_transactions_count = ROW_COUNT;
    END IF;
    
    -- 5. Удаляем операции, которые НЕ связаны с транзакциями
    DELETE FROM cash_operations 
    WHERE id = ANY(p_operation_ids)
      AND transaction_id IS NULL;
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    
    -- 6. Пересчитываем FIFO для всех затронутых portfolio_assets (если были удалены транзакции)
    IF array_length(v_portfolio_asset_ids, 1) > 0 THEN
        FOREACH v_portfolio_asset_id IN ARRAY v_portfolio_asset_ids
        LOOP
            PERFORM rebuild_fifo_for_portfolio_asset(v_portfolio_asset_id);
            PERFORM update_portfolio_asset(v_portfolio_asset_id);
        END LOOP;
    END IF;
    
    -- 7. Обновляем историю портфелей с минимальной даты
    IF v_min_date IS NOT NULL AND array_length(v_portfolio_ids, 1) > 0 THEN
        FOREACH v_portfolio_id IN ARRAY v_portfolio_ids
        LOOP
            PERFORM update_portfolio_values_from_date(
                v_portfolio_id,
                v_min_date
            );
        END LOOP;
    END IF;
    
    RETURN jsonb_build_object(
        'success', true,
        'deleted_count', v_deleted_count,
        'deleted_transactions_count', v_deleted_transactions_count,
        'portfolio_ids', v_portfolio_ids,
        'portfolio_asset_ids', v_portfolio_asset_ids
    );
EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', SQLERRM,
            'deleted_count', v_deleted_count
        );
END;
$$;

-- Комментарий к функции
COMMENT ON FUNCTION delete_operations_batch(bigint[]) IS 
'Безопасно удаляет несколько операций с пересчетом истории портфелей. Удаляет связанные транзакции (если есть), операции из cash_operations, пересчитывает FIFO и обновляет историю портфелей с минимальной даты удаленных операций.';
