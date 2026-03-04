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
    v_tx_portfolio_ids bigint[];
BEGIN
    -- Проверяем, что массив не пустой
    IF array_length(p_operation_ids, 1) IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Массив ID операций пуст',
            'deleted_count', 0
        );
    END IF;
    
    -- 1. Получаем информацию о всех операциях ДО удаления и собираем уникальные portfolio_id и transaction_ids
    -- ВАЖНО: Сохраняем информацию об операциях с asset_id для последующего обновления истории
    CREATE TEMP TABLE temp_deleted_ops_info AS
    SELECT 
        co.id,
        co.portfolio_id,
        co.asset_id,
        co.transaction_id,
        co.date::date as operation_date,
        co.type as operation_type
    FROM cash_operations co
    WHERE co.id = ANY(p_operation_ids);
    
    -- Получаем portfolio_ids и transaction_ids из временной таблицы
    SELECT 
        array_agg(DISTINCT portfolio_id) FILTER (WHERE portfolio_id IS NOT NULL),
        array_agg(DISTINCT transaction_id) FILTER (WHERE transaction_id IS NOT NULL),
        MIN(operation_date)
    INTO v_portfolio_ids, v_transaction_ids, v_min_date
    FROM temp_deleted_ops_info;
    
    -- Инициализируем массивы если они NULL
    IF v_portfolio_ids IS NULL THEN
        v_portfolio_ids := ARRAY[]::bigint[];
    END IF;
    IF v_transaction_ids IS NULL THEN
        v_transaction_ids := ARRAY[]::bigint[];
    END IF;
    
    -- 1.1. Если есть связанные транзакции, обновляем v_min_date и v_portfolio_ids с учетом транзакций
    -- Это важно, так как дата транзакции может отличаться от даты операции
    IF array_length(v_transaction_ids, 1) > 0 THEN
        DECLARE
            v_tx_min_date date;
        BEGIN
            -- Получаем минимальную дату транзакций
            SELECT MIN(t.transaction_date::date)
            INTO v_tx_min_date
            FROM transactions t
            WHERE t.id = ANY(v_transaction_ids);
            
            -- Обновляем v_min_date с учетом дат транзакций (берем минимум из операций и транзакций)
            IF v_tx_min_date IS NOT NULL THEN
                v_min_date := LEAST(
                    COALESCE(v_min_date, v_tx_min_date),
                    v_tx_min_date
                );
            END IF;
            
            -- Добавляем portfolio_ids из транзакций (через portfolio_assets)
            -- Это важно, так как транзакции могут быть в портфелях, не указанных в операциях
            SELECT array_agg(DISTINCT pa.portfolio_id) FILTER (WHERE pa.portfolio_id IS NOT NULL)
            INTO v_tx_portfolio_ids
            FROM transactions t
            JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
            WHERE t.id = ANY(v_transaction_ids);
            
            -- Добавляем найденные portfolio_ids к существующим
            IF v_tx_portfolio_ids IS NOT NULL AND array_length(v_tx_portfolio_ids, 1) > 0 THEN
                v_portfolio_ids := array_cat(
                    COALESCE(v_portfolio_ids, ARRAY[]::bigint[]),
                    v_tx_portfolio_ids
                );
                -- Удаляем дубликаты
                SELECT array_agg(DISTINCT unnest)
                INTO v_portfolio_ids
                FROM unnest(v_portfolio_ids) AS unnest;
            END IF;
        END;
    END IF;
    
    -- 1.2. Убеждаемся, что v_min_date не NULL (берем из операций, если транзакций не было)
    -- Также убеждаемся, что v_portfolio_ids содержит все затронутые портфели
    -- ВАЖНО: v_min_date должна быть определена для обновления истории
    IF v_min_date IS NULL THEN
        SELECT MIN(operation_date)
        INTO v_min_date
        FROM temp_deleted_ops_info
        WHERE operation_date IS NOT NULL;
        
        -- Если все еще NULL (все операции без дат или таблица пустая), используем текущую дату минус 1 день
        -- Это гарантирует, что история обновится хотя бы с вчерашнего дня
        IF v_min_date IS NULL THEN
            v_min_date := CURRENT_DATE - 1;
        END IF;
    END IF;
    
    -- 1.3. Убеждаемся, что v_portfolio_ids содержит все портфели из операций
    -- Это важно для операций без транзакций (Deposit, Withdraw и т.д.)
    IF v_portfolio_ids IS NULL OR array_length(v_portfolio_ids, 1) = 0 THEN
        SELECT array_agg(DISTINCT portfolio_id) FILTER (WHERE portfolio_id IS NOT NULL)
        INTO v_portfolio_ids
        FROM temp_deleted_ops_info;
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
    -- ВАЖНО: Используем локальную переменную, чтобы не перезаписать глобальную v_min_date
    IF array_length(v_portfolio_ids, 1) > 0 THEN
        DECLARE
            v_first_buy_date date;
        BEGIN
            FOREACH v_portfolio_id IN ARRAY v_portfolio_ids
            LOOP
                -- Для каждого актива в портфеле находим первую покупку и удаляем операции до неё
                FOR v_portfolio_asset_id, v_asset_id IN
                    SELECT DISTINCT pa.id, pa.asset_id
                    FROM portfolio_assets pa
                    WHERE pa.portfolio_id = v_portfolio_id
                LOOP
                    -- Получаем дату первой покупки актива (используем локальную переменную)
                    SELECT min(t.transaction_date::date)
                    INTO v_first_buy_date
                    FROM transactions t
                    WHERE t.portfolio_asset_id = v_portfolio_asset_id
                      AND t.transaction_type = 1;  -- Только покупки (Buy)
                    
                    -- Если есть первая покупка, удаляем операции до неё
                    IF v_first_buy_date IS NOT NULL THEN
                        DELETE FROM cash_operations
                        WHERE portfolio_id = v_portfolio_id
                          AND asset_id = v_asset_id
                          AND transaction_id IS NULL  -- Только операции без транзакций
                          AND type IN (3, 4, 7, 8)  -- Dividend, Coupon, Commission, Tax
                          AND date::date < v_first_buy_date;
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
        END;
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
    -- ВАЖНО: Используем temp_deleted_ops_info, так как операции уже удалены
    IF v_min_date IS NOT NULL THEN
        FOR v_portfolio_id, v_asset_id IN 
            SELECT DISTINCT tdoi.portfolio_id, tdoi.asset_id
            FROM temp_deleted_ops_info tdoi
            WHERE tdoi.portfolio_id IS NOT NULL
              AND tdoi.asset_id IS NOT NULL
              AND tdoi.operation_type IN (3, 4, 7, 8)  -- Dividend, Coupon, Commission, Tax
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
    
    -- Удаляем временную таблицу
    DROP TABLE IF EXISTS temp_deleted_ops_info;
    
    RETURN jsonb_build_object(
        'success', true,
        'deleted_count', v_deleted_count,
        'deleted_transactions_count', v_deleted_transactions_count,
        'portfolio_ids', v_portfolio_ids,
        'portfolio_asset_ids', v_portfolio_asset_ids
    );
EXCEPTION
    WHEN OTHERS THEN
        -- Удаляем временную таблицу в случае ошибки
        DROP TABLE IF EXISTS temp_deleted_ops_info;
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
