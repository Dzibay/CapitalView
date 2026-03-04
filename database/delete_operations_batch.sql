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
    v_asset_id bigint;
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
    
    -- 6.1. Удаляем операции до первой покупки для всех затронутых активов
    -- Это необходимо, так как операции (комиссии, дивиденды) не должны существовать до первой покупки
    IF array_length(v_portfolio_ids, 1) > 0 THEN
        FOREACH v_portfolio_id IN ARRAY v_portfolio_ids
        LOOP
            -- Для каждого актива в портфеле находим первую покупку и удаляем операции до неё
            FOR v_portfolio_asset_id, v_asset_id IN
                SELECT DISTINCT pa.id, pa.asset_id
                FROM portfolio_assets pa
                WHERE pa.portfolio_id = v_portfolio_id
            LOOP
                -- Получаем дату первой покупки актива
                SELECT min(t.transaction_date::date)
                INTO v_min_date
                FROM transactions t
                WHERE t.portfolio_asset_id = v_portfolio_asset_id
                  AND t.transaction_type = 1;  -- Только покупки (Buy)
                
                -- Если есть первая покупка, удаляем операции до неё
                IF v_min_date IS NOT NULL THEN
                    DELETE FROM cash_operations
                    WHERE portfolio_id = v_portfolio_id
                      AND asset_id = v_asset_id
                      AND transaction_id IS NULL  -- Только операции без транзакций
                      AND type IN (3, 4, 7, 8)  -- Dividend, Coupon, Commission, Tax
                      AND date::date < v_min_date;
                ELSE
                    -- Если нет покупок, удаляем все операции по активу
                    DELETE FROM cash_operations
                    WHERE portfolio_id = v_portfolio_id
                      AND asset_id = v_asset_id
                      AND transaction_id IS NULL  -- Только операции без транзакций
                      AND type IN (3, 4, 7, 8);  -- Dividend, Coupon, Commission, Tax
                END IF;
            END LOOP;
        END LOOP;
    END IF;
    
    -- 7. ШАГ 1: Обновляем позиции активов для ВСЕХ затронутых portfolio_assets
    -- Это нужно сделать ПЕРВЫМ, так как portfolio_daily_values агрегирует данные из portfolio_daily_positions
    -- 7.1. Обновляем позиции для транзакций (если были удалены транзакции)
    IF v_min_date IS NOT NULL AND array_length(v_portfolio_asset_ids, 1) > 0 THEN
        FOREACH v_portfolio_asset_id IN ARRAY v_portfolio_asset_ids
        LOOP
            BEGIN
                PERFORM update_portfolio_asset_positions_from_date(
                    v_portfolio_asset_id,
                    v_min_date - 1
                );
            EXCEPTION WHEN OTHERS THEN
                RAISE WARNING 'Ошибка при обновлении позиций актива % (транзакции): %', v_portfolio_asset_id, SQLERRM;
            END;
        END LOOP;
    END IF;
    
    -- 7.2. Обновляем позиции для операций с asset_id (Commission/Tax/Dividend/Coupon)
    -- Типы операций: 3=Dividend, 4=Coupon, 7=Commission, 8=Tax
    IF v_min_date IS NOT NULL THEN
        FOR v_portfolio_id, v_asset_id IN 
            SELECT DISTINCT co.portfolio_id, co.asset_id
            FROM cash_operations co
            WHERE co.id = ANY(p_operation_ids)
              AND co.portfolio_id IS NOT NULL
              AND co.asset_id IS NOT NULL
              AND co.type IN (3, 4, 7, 8)  -- Dividend, Coupon, Commission, Tax
        LOOP
            BEGIN
                -- Обновляем позиции для всех portfolio_asset_id с этим asset_id в портфеле
                FOR v_portfolio_asset_id IN 
                    SELECT pa.id
                    FROM portfolio_assets pa
                    WHERE pa.portfolio_id = v_portfolio_id
                      AND pa.asset_id = v_asset_id
                LOOP
                    BEGIN
                        PERFORM update_portfolio_asset_positions_from_date(
                            v_portfolio_asset_id,
                            v_min_date - 1
                        );
                    EXCEPTION WHEN OTHERS THEN
                        RAISE WARNING 'Ошибка при обновлении позиций актива % (операции): %', v_portfolio_asset_id, SQLERRM;
                    END;
                END LOOP;
            EXCEPTION WHEN OTHERS THEN
                RAISE WARNING 'Ошибка при обновлении позиций для портфеля % и актива %: %', v_portfolio_id, v_asset_id, SQLERRM;
            END;
        END LOOP;
    END IF;
    
    -- 8. ШАГ 2: Обновляем историю портфелей с минимальной даты
    -- Это агрегирует данные из portfolio_daily_positions в portfolio_daily_values
    -- Важно: делаем это ПОСЛЕ обновления позиций активов
    IF v_min_date IS NOT NULL AND array_length(v_portfolio_ids, 1) > 0 THEN
        FOREACH v_portfolio_id IN ARRAY v_portfolio_ids
        LOOP
            BEGIN
                PERFORM update_portfolio_values_from_date(
                    v_portfolio_id,
                    v_min_date - 1
                );
            EXCEPTION WHEN OTHERS THEN
                RAISE WARNING 'Ошибка при обновлении истории портфеля %: %', v_portfolio_id, SQLERRM;
            END;
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
