CREATE OR REPLACE FUNCTION apply_transactions_batch(
    p_transactions jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    v_tx jsonb;
    v_tx_id bigint;
    v_remaining numeric;
    v_realized numeric := 0;
    v_portfolio_id bigint;
    v_inserted_count integer := 0;
    v_failed_count integer := 0;
    v_failed_tx jsonb := '[]'::jsonb;
    v_tx_ids bigint[] := ARRAY[]::bigint[];
    lot RECORD;
    v_error_text text;
    v_tx_item jsonb;
    v_tx_date timestamp without time zone;
    v_buy_op_type_id bigint;
    v_sell_op_type_id bigint;
    v_redemption_op_type_id bigint;
    v_tx_record RECORD;
    v_portfolio_asset_id bigint;
BEGIN
    IF p_transactions IS NULL OR jsonb_array_length(p_transactions) = 0 THEN
        RETURN jsonb_build_object(
            'inserted_count', 0,
            'failed_count', 0,
            'failed_transactions', '[]'::jsonb,
            'transaction_ids', '[]'::jsonb
        );
    END IF;

    CREATE TEMP TABLE temp_sorted_tx AS
    SELECT 
        (tx->>'user_id')::uuid as user_id,
        (tx->>'portfolio_asset_id')::bigint as portfolio_asset_id,
        (tx->>'transaction_type')::int as transaction_type,
        (tx->>'quantity')::numeric as quantity,
        (tx->>'price')::numeric as price,
        CASE 
            WHEN (tx->>'transaction_date')::text ~ 'T' OR (tx->>'transaction_date')::text ~ ' ' THEN
                (tx->>'transaction_date')::timestamp without time zone
            ELSE
                (tx->>'transaction_date')::date::timestamp without time zone
        END as transaction_date,
        tx as original_json
    FROM jsonb_array_elements(p_transactions) tx
    ORDER BY 
        transaction_date,
        (tx->>'portfolio_asset_id')::bigint,
        (tx->>'transaction_type')::int;
    
    CREATE TEMP TABLE temp_tx_payment_map (
        transaction_id bigint PRIMARY KEY,
        payment numeric,
        user_id uuid,
        portfolio_asset_id bigint,
        transaction_type int,
        transaction_date timestamp without time zone,
        price numeric,
        quantity numeric
    );

    IF EXISTS (SELECT 1 FROM temp_sorted_tx WHERE transaction_type = 1) THEN
        CREATE TEMP TABLE temp_inserted_buy_tx (
            tx_id bigint,
            portfolio_asset_id bigint,
            quantity numeric,
            price numeric,
            transaction_date timestamp without time zone
        );
        
        WITH inserted_transactions AS (
            INSERT INTO transactions (
                user_id,
                portfolio_asset_id,
                transaction_type,
                quantity,
                price,
                transaction_date,
                realized_pnl
            )
            SELECT 
                t.user_id,
                t.portfolio_asset_id,
                t.transaction_type,
                t.quantity,
                t.price,
                t.transaction_date,
                0
            FROM temp_sorted_tx t
            WHERE t.transaction_type = 1
              AND NOT EXISTS (
                  SELECT 1
                  FROM transactions existing
                  WHERE existing.portfolio_asset_id = t.portfolio_asset_id
                    AND existing.transaction_date::timestamp without time zone = t.transaction_date
                    AND existing.transaction_type = t.transaction_type
                    AND ABS(existing.price - t.price) < 0.000001
                    AND ABS(existing.quantity - t.quantity) < 0.000001
              )
            RETURNING 
                id,
                user_id,
                portfolio_asset_id,
                transaction_type,
                quantity,
                price,
                transaction_date
        )
        INSERT INTO temp_inserted_buy_tx (
            tx_id,
            portfolio_asset_id,
            quantity,
            price,
            transaction_date
        )
        SELECT 
            id,
            portfolio_asset_id,
            quantity,
            price,
            transaction_date
        FROM inserted_transactions;
        
        INSERT INTO temp_tx_payment_map (transaction_id, payment, user_id, portfolio_asset_id, transaction_type, transaction_date, price, quantity)
        SELECT 
            tibt.tx_id,
            COALESCE((tst.original_json->>'payment')::numeric, 0),
            t.user_id,
            tibt.portfolio_asset_id,
            1,  -- transaction_type = 1 для Buy транзакций
            tibt.transaction_date,
            tibt.price,
            tibt.quantity
        FROM temp_inserted_buy_tx tibt
        JOIN transactions t ON t.id = tibt.tx_id
        LEFT JOIN temp_sorted_tx tst ON 
            tst.portfolio_asset_id = tibt.portfolio_asset_id
            AND tst.transaction_type = 1  -- Buy транзакции
            AND (
                tst.transaction_date = tibt.transaction_date
                OR ABS(EXTRACT(EPOCH FROM (tst.transaction_date - tibt.transaction_date))) < 1  -- Разница менее 1 секунды
            )
            AND ABS(COALESCE(tst.price, 0) - COALESCE(tibt.price, 0)) < 0.0001
            AND ABS(COALESCE(tst.quantity, 0) - COALESCE(tibt.quantity, 0)) < 0.0001;
        
        INSERT INTO temp_tx_payment_map (transaction_id, payment, user_id, portfolio_asset_id, transaction_type, transaction_date, price, quantity)
        SELECT DISTINCT ON (tibt.tx_id)
            tibt.tx_id,
            COALESCE((tst.original_json->>'payment')::numeric, 0),
            t.user_id,
            tibt.portfolio_asset_id,
            1,
            tibt.transaction_date,
            tibt.price,
            tibt.quantity
        FROM temp_inserted_buy_tx tibt
        JOIN transactions t ON t.id = tibt.tx_id
        LEFT JOIN temp_sorted_tx tst ON 
            tst.portfolio_asset_id = tibt.portfolio_asset_id
            AND tst.transaction_type = 1
            AND tst.transaction_date::date = tibt.transaction_date::date
            AND ABS(COALESCE(tst.price, 0) - COALESCE(tibt.price, 0)) < 0.0001
            AND ABS(COALESCE(tst.quantity, 0) - COALESCE(tibt.quantity, 0)) < 0.0001
        WHERE NOT EXISTS (
            SELECT 1 FROM temp_tx_payment_map tpm WHERE tpm.transaction_id = tibt.tx_id
        )
        AND (tst.original_json->>'payment') IS NOT NULL
        AND (tst.original_json->>'payment')::numeric != 0
        ORDER BY tibt.tx_id, ABS(EXTRACT(EPOCH FROM (tst.transaction_date - tibt.transaction_date)));
        
        SELECT COUNT(*) INTO v_inserted_count FROM temp_inserted_buy_tx;
        
        SELECT COALESCE(array_agg(tx_id), ARRAY[]::bigint[]) INTO v_tx_ids FROM temp_inserted_buy_tx;
        
        INSERT INTO fifo_lots (
            portfolio_asset_id,
            remaining_qty,
            price,
            created_at
        )
        SELECT 
            t.portfolio_asset_id,
            t.quantity,
            t.price,
            t.transaction_date
        FROM temp_inserted_buy_tx t
        ORDER BY t.transaction_date, t.tx_id;
        
        DROP TABLE temp_inserted_buy_tx;
    END IF;

    IF EXISTS (SELECT 1 FROM temp_sorted_tx WHERE transaction_type IN (2, 3)) THEN
        FOR v_tx_item IN 
            SELECT original_json 
            FROM temp_sorted_tx 
            WHERE transaction_type IN (2, 3)
            ORDER BY transaction_date
        LOOP
            BEGIN
                SELECT portfolio_id
                INTO v_portfolio_id
                FROM portfolio_assets
                WHERE id = (v_tx_item->>'portfolio_asset_id')::bigint;

                IF v_portfolio_id IS NULL THEN
                    RAISE EXCEPTION 'Portfolio not found for portfolio_asset_id=%', 
                        (v_tx_item->>'portfolio_asset_id')::bigint;
                END IF;

                IF (v_tx_item->>'transaction_date')::text ~ 'T' OR (v_tx_item->>'transaction_date')::text ~ ' ' THEN
                    v_tx_date := (v_tx_item->>'transaction_date')::timestamp without time zone;
                ELSE
                    v_tx_date := (v_tx_item->>'transaction_date')::date::timestamp without time zone;
                END IF;
                
                IF EXISTS (
                    SELECT 1
                    FROM transactions existing
                    WHERE existing.portfolio_asset_id = (v_tx_item->>'portfolio_asset_id')::bigint
                      AND existing.transaction_date::timestamp without time zone = v_tx_date
                      AND existing.transaction_type = (v_tx_item->>'transaction_type')::int
                      AND ABS(existing.price - (v_tx_item->>'price')::numeric) < 0.000001
                      AND ABS(existing.quantity - (v_tx_item->>'quantity')::numeric) < 0.000001
                ) THEN
                    v_failed_count := v_failed_count + 1;
                    v_failed_tx := v_failed_tx || jsonb_build_object(
                        'transaction', v_tx_item,
                        'error', 'Transaction already exists (duplicate)'
                    );
                    CONTINUE;  -- Пропускаем эту транзакцию
                END IF;

                INSERT INTO transactions (
                    user_id,
                    portfolio_asset_id,
                    transaction_type,
                    quantity,
                    price,
                    transaction_date,
                    realized_pnl
                )
                VALUES (
                    (v_tx_item->>'user_id')::uuid,
                    (v_tx_item->>'portfolio_asset_id')::bigint,
                    (v_tx_item->>'transaction_type')::int,
                    (v_tx_item->>'quantity')::numeric,
                    (v_tx_item->>'price')::numeric,
                    v_tx_date,
                    0
                )
                RETURNING id INTO v_tx_id;

                IF v_tx_id IS NULL THEN
                    RAISE EXCEPTION 'Failed to insert transaction: transaction_id is NULL';
                END IF;
                
                INSERT INTO temp_tx_payment_map (transaction_id, payment, user_id, portfolio_asset_id, transaction_type, transaction_date, price, quantity)
                SELECT 
                    v_tx_id,
                    COALESCE((tst.original_json->>'payment')::numeric, 0),
                    (v_tx_item->>'user_id')::uuid,
                    (v_tx_item->>'portfolio_asset_id')::bigint,
                    (v_tx_item->>'transaction_type')::int,
                    v_tx_date,
                    (v_tx_item->>'price')::numeric,
                    (v_tx_item->>'quantity')::numeric
                FROM temp_sorted_tx tst
                WHERE tst.user_id = (v_tx_item->>'user_id')::uuid
                  AND tst.portfolio_asset_id = (v_tx_item->>'portfolio_asset_id')::bigint
                  AND tst.transaction_type = (v_tx_item->>'transaction_type')::int
                  AND tst.transaction_date = v_tx_date
                  AND ABS(COALESCE(tst.price, 0) - COALESCE((v_tx_item->>'price')::numeric, 0)) < 0.0001
                  AND ABS(COALESCE(tst.quantity, 0) - COALESCE((v_tx_item->>'quantity')::numeric, 0)) < 0.0001
                LIMIT 1;

                -- Обрабатываем FIFO для продажи или погашения
                v_remaining := (v_tx_item->>'quantity')::numeric;
                v_realized := 0;

                FOR lot IN
                    SELECT *
                    FROM fifo_lots
                    WHERE portfolio_asset_id = (v_tx_item->>'portfolio_asset_id')::bigint
                      AND remaining_qty > 0
                    ORDER BY created_at, id
                    FOR UPDATE
                LOOP
                    EXIT WHEN v_remaining <= 0;

                    -- Для SELL и REDEMPTION рассчитываем realized_pnl
                    IF (v_tx_item->>'transaction_type')::int IN (2, 3) THEN
                    IF lot.remaining_qty <= v_remaining THEN
                        v_realized := v_realized + lot.remaining_qty * (
                            (v_tx_item->>'price')::numeric - lot.price
                        );
                        ELSE
                            v_realized := v_realized + v_remaining * (
                                (v_tx_item->>'price')::numeric - lot.price
                            );
                        END IF;
                    END IF;

                    IF lot.remaining_qty <= v_remaining THEN
                        v_remaining := v_remaining - lot.remaining_qty;
                        UPDATE fifo_lots
                        SET remaining_qty = 0
                        WHERE id = lot.id;
                    ELSE
                        UPDATE fifo_lots
                        SET remaining_qty = lot.remaining_qty - v_remaining
                        WHERE id = lot.id;
                        v_remaining := 0;
                    END IF;
                END LOOP;

                IF v_remaining > 0 THEN
                    RAISE EXCEPTION 'Not enough quantity to % (portfolio_asset_id=%, remaining=%)',
                        CASE WHEN (v_tx_item->>'transaction_type')::int = 2 THEN 'sell' ELSE 'redeem' END,
                        (v_tx_item->>'portfolio_asset_id')::bigint,
                        v_remaining;
                END IF;

                IF (v_tx_item->>'transaction_type')::int IN (2, 3) AND v_realized != 0 THEN
                UPDATE transactions
                SET realized_pnl = v_realized
                WHERE id = v_tx_id;
                END IF;

                v_tx_ids := array_append(v_tx_ids, v_tx_id);
                v_inserted_count := v_inserted_count + 1;

            EXCEPTION
                WHEN OTHERS THEN
                    -- Ошибка при обработке продажи
                    v_failed_count := v_failed_count + 1;
                    v_error_text := SQLERRM;
                    v_failed_tx := v_failed_tx || jsonb_build_object(
                        'transaction', v_tx_item,
                        'error', v_error_text
                    );
            END;
        END LOOP;
    END IF;

    -- ========================================================================
    -- 3. БАТЧ-СОЗДАНИЕ CASH_OPERATIONS (оптимизация для массового импорта)
    -- ========================================================================
    -- Отключаем триггер для батч-вставки, чтобы избежать дублирования
    -- Затем включаем триггер обратно
    
    IF array_length(v_tx_ids, 1) > 0 THEN
        SELECT id INTO v_buy_op_type_id FROM operations_type WHERE name = 'Buy' LIMIT 1;
        SELECT id INTO v_sell_op_type_id FROM operations_type WHERE name = 'Sell' LIMIT 1;
        
        SELECT id INTO v_redemption_op_type_id FROM operations_type WHERE name = 'Redemption' LIMIT 1;
        IF v_redemption_op_type_id IS NULL THEN
            SELECT id INTO v_redemption_op_type_id FROM operations_type WHERE name = 'ammortization' LIMIT 1;
        END IF;
        
        INSERT INTO cash_operations (user_id, portfolio_id, type, amount, currency, date, transaction_id, asset_id)
        SELECT
            t.user_id,
            pa.portfolio_id,
            CASE 
                WHEN t.transaction_type = 1 THEN v_buy_op_type_id
                WHEN t.transaction_type = 2 THEN v_sell_op_type_id
                WHEN t.transaction_type = 3 THEN v_redemption_op_type_id
            END,
            CASE 
                WHEN t.transaction_type = 1 THEN -ABS(COALESCE(tpm.payment, 0))  -- Buy: отрицательное
                WHEN t.transaction_type = 2 THEN ABS(COALESCE(tpm.payment, 0))    -- Sell: положительное
                WHEN t.transaction_type = 3 THEN ABS(COALESCE(tpm.payment, 0))    -- Redemption: положительное
                ELSE COALESCE(tpm.payment, 0)
            END,
            1, -- RUB
            t.transaction_date,
            t.id,
            pa.asset_id
        FROM transactions t
        JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
        LEFT JOIN temp_tx_payment_map tpm ON tpm.transaction_id = t.id
        WHERE t.id = ANY(v_tx_ids)
          AND t.transaction_type IN (1, 2, 3)  -- Buy, Sell и Redemption
          AND NOT EXISTS (
              SELECT 1 
              FROM cash_operations co 
              WHERE co.transaction_id = t.id
          );
        
    END IF;

    IF array_length(v_tx_ids, 1) > 0 THEN
        DECLARE
            v_pa_id bigint;
            v_min_tx_date date;
            v_pa_ids bigint[];
        BEGIN
            SELECT 
                MIN(t.transaction_date::date),
                array_agg(DISTINCT t.portfolio_asset_id) FILTER (WHERE t.portfolio_asset_id IS NOT NULL)
            INTO v_min_tx_date, v_pa_ids
            FROM transactions t
            WHERE t.id = ANY(v_tx_ids);
            
            IF v_min_tx_date IS NOT NULL AND array_length(v_pa_ids, 1) > 0 THEN
                FOREACH v_pa_id IN ARRAY v_pa_ids
                LOOP
                    BEGIN
                        PERFORM update_portfolio_asset_positions_from_date(
                            v_pa_id,
                            v_min_tx_date - 1
                        );
                    EXCEPTION WHEN OTHERS THEN
                        RAISE WARNING 'Ошибка при обновлении позиций актива %: %', v_pa_id, SQLERRM;
                    END;
                END LOOP;
            END IF;
        END;
    END IF;

    IF array_length(v_tx_ids, 1) > 0 THEN
        DECLARE
            v_p_id bigint;
            v_min_tx_date date;
            v_p_ids bigint[];
        BEGIN
            SELECT 
                MIN(t.transaction_date::date),
                array_agg(DISTINCT pa.portfolio_id) FILTER (WHERE pa.portfolio_id IS NOT NULL)
            INTO v_min_tx_date, v_p_ids
            FROM transactions t
            JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
            WHERE t.id = ANY(v_tx_ids);
            
            IF v_min_tx_date IS NOT NULL AND array_length(v_p_ids, 1) > 0 THEN
                FOREACH v_p_id IN ARRAY v_p_ids
                LOOP
                    BEGIN
                        PERFORM update_portfolio_values_from_date(
                            v_p_id,
                            v_min_tx_date - 1
                        );
                    EXCEPTION WHEN OTHERS THEN
                        RAISE WARNING 'Ошибка при обновлении истории портфеля %: %', v_p_id, SQLERRM;
                    END;
                END LOOP;
            END IF;
        END;
    END IF;

    -- Примечание: проверка неполученных выплат НЕ выполняется здесь автоматически
    -- Это сделано для предотвращения ложных срабатываний при батч-импорте от брокера,
    -- когда операции могут быть еще не вставлены на момент проверки.
    -- Проверку следует вызывать отдельно после завершения всех батч-операций.

    DROP TABLE IF EXISTS temp_sorted_tx;
    DROP TABLE IF EXISTS temp_tx_payment_map;

    RETURN jsonb_build_object(
        'inserted_count', v_inserted_count,
        'failed_count', v_failed_count,
        'failed_transactions', v_failed_tx,
        'transaction_ids', to_jsonb(v_tx_ids)
    );

EXCEPTION
    WHEN OTHERS THEN
        DROP TABLE IF EXISTS temp_sorted_tx;
        DROP TABLE IF EXISTS temp_tx_payment_map;
        RAISE;
END;
$$;
