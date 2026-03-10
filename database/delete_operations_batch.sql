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
    IF array_length(p_operation_ids, 1) IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Массив ID операций пуст',
            'deleted_count', 0
        );
    END IF;
    
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
    
    SELECT 
        array_agg(DISTINCT portfolio_id) FILTER (WHERE portfolio_id IS NOT NULL),
        array_agg(DISTINCT transaction_id) FILTER (WHERE transaction_id IS NOT NULL),
        MIN(operation_date)
    INTO v_portfolio_ids, v_transaction_ids, v_min_date
    FROM temp_deleted_ops_info;
    
    IF v_portfolio_ids IS NULL THEN
        v_portfolio_ids := ARRAY[]::bigint[];
    END IF;
    IF v_transaction_ids IS NULL THEN
        v_transaction_ids := ARRAY[]::bigint[];
    END IF;
    
    IF array_length(v_transaction_ids, 1) > 0 THEN
        DECLARE
            v_tx_min_date date;
        BEGIN
            SELECT MIN(t.transaction_date::date)
            INTO v_tx_min_date
            FROM transactions t
            WHERE t.id = ANY(v_transaction_ids);
            
            IF v_tx_min_date IS NOT NULL THEN
                v_min_date := LEAST(
                    COALESCE(v_min_date, v_tx_min_date),
                    v_tx_min_date
                );
            END IF;
            
            SELECT array_agg(DISTINCT pa.portfolio_id) FILTER (WHERE pa.portfolio_id IS NOT NULL)
            INTO v_tx_portfolio_ids
            FROM transactions t
            JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
            WHERE t.id = ANY(v_transaction_ids);
            
            IF v_tx_portfolio_ids IS NOT NULL AND array_length(v_tx_portfolio_ids, 1) > 0 THEN
                v_portfolio_ids := array_cat(
                    COALESCE(v_portfolio_ids, ARRAY[]::bigint[]),
                    v_tx_portfolio_ids
                );
                SELECT array_agg(DISTINCT unnest)
                INTO v_portfolio_ids
                FROM unnest(v_portfolio_ids) AS unnest;
            END IF;
        END;
    END IF;
    
    IF v_min_date IS NULL THEN
        SELECT MIN(operation_date)
        INTO v_min_date
        FROM temp_deleted_ops_info
        WHERE operation_date IS NOT NULL;
        
        IF v_min_date IS NULL THEN
            v_min_date := CURRENT_DATE - 1;
        END IF;
    END IF;
    
    IF v_portfolio_ids IS NULL OR array_length(v_portfolio_ids, 1) = 0 THEN
        SELECT array_agg(DISTINCT portfolio_id) FILTER (WHERE portfolio_id IS NOT NULL)
        INTO v_portfolio_ids
        FROM temp_deleted_ops_info;
    END IF;
    
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
    
    DELETE FROM cash_operations 
    WHERE id = ANY(p_operation_ids)
      AND transaction_id IS NULL;
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    
    IF array_length(v_portfolio_asset_ids, 1) > 0 THEN
        FOREACH v_portfolio_asset_id IN ARRAY v_portfolio_asset_ids
        LOOP
            PERFORM rebuild_fifo_for_portfolio_asset(v_portfolio_asset_id);
            PERFORM update_portfolio_asset(v_portfolio_asset_id);
        END LOOP;
    END IF;
    
    IF array_length(v_portfolio_ids, 1) > 0 THEN
        DECLARE
            v_first_buy_date date;
        BEGIN
            FOREACH v_portfolio_id IN ARRAY v_portfolio_ids
            LOOP
                FOR v_portfolio_asset_id, v_asset_id IN
                    SELECT DISTINCT pa.id, pa.asset_id
                    FROM portfolio_assets pa
                    WHERE pa.portfolio_id = v_portfolio_id
                LOOP
                    SELECT min(t.transaction_date::date)
                    INTO v_first_buy_date
                    FROM transactions t
                    WHERE t.portfolio_asset_id = v_portfolio_asset_id
                      AND t.transaction_type = 1;
                    
                    IF v_first_buy_date IS NOT NULL THEN
                        DELETE FROM cash_operations
                        WHERE portfolio_id = v_portfolio_id
                          AND asset_id = v_asset_id
                          AND transaction_id IS NULL
                          AND type IN (3, 4, 7, 8)
                          AND date::date < v_first_buy_date;
                    ELSE
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
    
    IF v_min_date IS NOT NULL THEN
        FOR v_portfolio_id, v_asset_id IN 
            SELECT DISTINCT tdoi.portfolio_id, tdoi.asset_id
            FROM temp_deleted_ops_info tdoi
            WHERE tdoi.portfolio_id IS NOT NULL
              AND tdoi.asset_id IS NOT NULL
              AND tdoi.operation_type IN (3, 4, 7, 8)
        LOOP
        BEGIN
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
    
    -- Проверяем неполученные выплаты для всех затронутых активов
    -- Делаем это после обновления позиций, чтобы portfolio_daily_positions был актуален
    
    -- 1. Проверяем активы, связанные с транзакциями (уже есть в v_portfolio_asset_ids)
    IF array_length(v_portfolio_asset_ids, 1) > 0 THEN
        BEGIN
            FOR v_portfolio_asset_id IN 
                SELECT DISTINCT unnest(v_portfolio_asset_ids)
            LOOP
                BEGIN
                    PERFORM check_missed_payouts(v_portfolio_asset_id);
                EXCEPTION
                    WHEN OTHERS THEN
                        -- Игнорируем ошибки проверки выплат, чтобы не прерывать удаление операций
                        RAISE WARNING 'Ошибка при проверке неполученных выплат для актива %: %', v_portfolio_asset_id, SQLERRM;
                END;
            END LOOP;
        EXCEPTION
            WHEN OTHERS THEN
                -- Игнорируем ошибки проверки выплат, чтобы не прерывать удаление операций
                RAISE WARNING 'Ошибка при проверке неполученных выплат: %', SQLERRM;
        END;
    END IF;
    
    -- 2. Проверяем активы для операций дивидендов/купонов, не связанных с транзакциями
    -- Эти операции могут быть удалены отдельно, и нужно обновить missed_payouts для соответствующих активов
    FOR v_portfolio_id, v_asset_id IN 
        SELECT DISTINCT tdoi.portfolio_id, tdoi.asset_id
        FROM temp_deleted_ops_info tdoi
        WHERE tdoi.portfolio_id IS NOT NULL
          AND tdoi.asset_id IS NOT NULL
          AND tdoi.operation_type IN (3, 4)  -- Dividend, Coupon
          AND tdoi.transaction_id IS NULL    -- Только операции без транзакций
    LOOP
        BEGIN
            -- Проверяем все активы в портфеле с этим asset_id
            FOR v_portfolio_asset_id IN 
                SELECT pa.id
                FROM portfolio_assets pa
                WHERE pa.portfolio_id = v_portfolio_id
                  AND pa.asset_id = v_asset_id
            LOOP
                BEGIN
                    PERFORM check_missed_payouts(v_portfolio_asset_id);
                EXCEPTION
                    WHEN OTHERS THEN
                        -- Игнорируем ошибки проверки выплат, чтобы не прерывать удаление операций
                        RAISE WARNING 'Ошибка при проверке неполученных выплат для актива % (операции): %', v_portfolio_asset_id, SQLERRM;
                END;
            END LOOP;
        EXCEPTION
            WHEN OTHERS THEN
                -- Игнорируем ошибки проверки выплат, чтобы не прерывать удаление операций
                RAISE WARNING 'Ошибка при проверке неполученных выплат для портфеля % и актива % (операции): %', v_portfolio_id, v_asset_id, SQLERRM;
        END;
    END LOOP;
    
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
        DROP TABLE IF EXISTS temp_deleted_ops_info;
        RETURN jsonb_build_object(
            'success', false,
            'error', SQLERRM,
            'deleted_count', v_deleted_count
        );
END;
$$;
