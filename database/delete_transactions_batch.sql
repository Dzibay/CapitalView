-- ============================================================================
-- Функция безопасного batch удаления транзакций с пересчетом FIFO
-- ============================================================================
-- При удалении транзакций:
-- 1. Получает ID связанных cash_operations (у транзакций всегда есть связанная операция)
-- 2. Вызывает delete_operations_batch для удаления операций и транзакций
-- 3. Все пересчеты выполняются в delete_operations_batch
-- ============================================================================

CREATE OR REPLACE FUNCTION delete_transactions_batch(p_transaction_ids bigint[])
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    v_operation_ids bigint[];
    v_result jsonb;
BEGIN
    -- Проверяем, что массив не пустой
    IF array_length(p_transaction_ids, 1) IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Массив ID транзакций пуст',
            'deleted_count', 0
        );
    END IF;
    
    -- 1. Получаем ID связанных cash_operations
    -- У транзакций всегда есть связанная операция
    SELECT array_agg(DISTINCT co.id) FILTER (WHERE co.id IS NOT NULL)
    INTO v_operation_ids
    FROM cash_operations co
    WHERE co.transaction_id = ANY(p_transaction_ids);
    
    -- Проверяем, что найдены связанные операции
    IF v_operation_ids IS NULL OR array_length(v_operation_ids, 1) IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Не найдено связанных операций для транзакций',
            'deleted_count', 0
        );
    END IF;
    
    -- 2. Вызываем delete_operations_batch для удаления операций и транзакций
    -- Эта функция удалит операции и связанные транзакции с пересчетом FIFO
    v_result := delete_operations_batch(v_operation_ids);
    
    -- Возвращаем результат с информацией о транзакциях
    RETURN jsonb_build_object(
        'success', v_result->>'success',
        'deleted_count', (v_result->>'deleted_transactions_count')::int,
        'deleted_operations_count', (v_result->>'deleted_count')::int,
        'portfolio_ids', v_result->'portfolio_ids',
        'portfolio_asset_ids', v_result->'portfolio_asset_ids',
        'error', v_result->>'error'
    );
EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', SQLERRM,
            'deleted_count', 0
        );
END;
$$;

-- Комментарий к функции
COMMENT ON FUNCTION delete_transactions_batch(bigint[]) IS 
'Безопасно удаляет несколько транзакций через удаление связанных операций. Получает ID связанных cash_operations (у транзакций всегда есть связанная операция) и вызывает delete_operations_batch для универсального удаления с пересчетом FIFO.';
