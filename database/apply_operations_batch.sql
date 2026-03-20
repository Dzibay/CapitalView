CREATE OR REPLACE FUNCTION apply_operations_batch(
    p_operations jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    v_op_id bigint;
    v_inserted_count integer := 0;
    v_failed_count integer := 0;
    v_failed_ops jsonb := '[]'::jsonb;
    v_op_ids bigint[] := ARRAY[]::bigint[];
    v_tx_ids bigint[] := ARRAY[]::bigint[];
    v_error_text text;
    v_rub_currency_id bigint;
    v_currency_rate numeric(20,6);
    v_amount_rub numeric(20,6);
    v_currency_quote_asset_id bigint;
    v_currency_to_quote_rate numeric(20,6);
    v_quote_to_rub_rate numeric(20,6);
    v_amount_in_quote numeric(20,6);
    v_portfolio_id bigint;
    v_operation_date timestamp without time zone;
    v_asset_id bigint;
    v_operation_type int;
    v_portfolio_asset_id bigint;
    v_created_operations jsonb := '[]'::jsonb;
    v_op_type_id bigint;
    v_portfolio_exists boolean;
    v_op_record RECORD;
    v_first_buy_date timestamp without time zone;
    v_min_date date;
    -- Для операций покупки/продажи/погашения (транзакции)
    v_buy_op_type_id bigint;
    v_sell_op_type_id bigint;
    v_redemption_op_type_id bigint;
    v_tx_id bigint;
    v_remaining numeric;
    v_realized numeric := 0;
    lot RECORD;
    v_tx_item RECORD;
    v_tx_date timestamp without time zone;
    v_currency_id bigint;  -- эффективная валюта: из данных или из актива (quote_asset_id)
    v_currency_ticker text;
    v_quote_ticker text;
BEGIN
    IF p_operations IS NULL OR jsonb_array_length(p_operations) = 0 THEN
        RETURN jsonb_build_object(
            'inserted_count', 0,
            'failed_count', 0,
            'failed_operations', '[]'::jsonb,
            'operation_ids', '[]'::jsonb,
            'transaction_ids', '[]'::jsonb,
            'created', '[]'::jsonb
        );
    END IF;

    SELECT id INTO v_rub_currency_id
    FROM assets
    WHERE ticker = 'RUB' AND user_id IS NULL
    LIMIT 1;
    
    IF v_rub_currency_id IS NULL THEN
        v_rub_currency_id := 1;
    END IF;

    -- ID типов операций Buy/Sell/Redemption одним запросом
    SELECT
        MAX(id) FILTER (WHERE name = 'Buy'),
        MAX(id) FILTER (WHERE name = 'Sell'),
        COALESCE(MAX(id) FILTER (WHERE name = 'Redemption'), MAX(id) FILTER (WHERE name = 'ammortization'))
    INTO v_buy_op_type_id, v_sell_op_type_id, v_redemption_op_type_id
    FROM operations_type
    WHERE name IN ('Buy', 'Sell', 'Redemption', 'ammortization');

    -- Сортируем операции по дате (включая поля для Buy/Sell/Redemption: quantity, price, payment)
    CREATE TEMP TABLE temp_sorted_ops AS
    SELECT 
        (op->>'user_id')::uuid as user_id,
        (op->>'portfolio_id')::bigint as portfolio_id,
        (op->>'operation_type')::int as operation_type,
        (op->>'amount')::numeric(20,6) as amount,
        (op->>'currency_id')::bigint as currency_id,
        CASE 
            WHEN (op->>'operation_date')::text ~ 'T' OR (op->>'operation_date')::text ~ ' ' THEN
                (op->>'operation_date')::timestamp without time zone
            ELSE
                (op->>'operation_date')::date::timestamp without time zone
        END as operation_date,
        (op->>'asset_id')::bigint as asset_id,
        (op->>'portfolio_asset_id')::bigint as portfolio_asset_id,
        (op->>'dividend_yield')::numeric as dividend_yield,
        (op->>'quantity')::numeric as quantity,
        (op->>'price')::numeric(20,2) as price,
        COALESCE((op->>'payment')::numeric(20,6), (op->>'amount')::numeric(20,6)) as payment,
        op as original_json
    FROM jsonb_array_elements(p_operations) op
    ORDER BY 
        operation_date,
        (op->>'portfolio_id')::bigint,
        (op->>'operation_type')::int;

    -- Таблица для маппинга транзакция -> payment и валюта (для последующей вставки cash_operations)
    CREATE TEMP TABLE temp_tx_payment_map (
        transaction_id bigint PRIMARY KEY,
        payment numeric,
        user_id uuid,
        portfolio_asset_id bigint,
        transaction_type int,
        transaction_date timestamp without time zone,
        price numeric,
        quantity numeric,
        currency_id bigint
    );

    -- ========== СНАЧАЛА: Buy/Sell/Redemption (чтобы покупки были в БД до проверки «первая покупка» для Dividend/Coupon) ==========
    IF v_buy_op_type_id IS NOT NULL AND v_sell_op_type_id IS NOT NULL AND v_redemption_op_type_id IS NOT NULL THEN
        IF EXISTS (
            SELECT 1 FROM temp_sorted_ops 
            WHERE operation_type IN (v_buy_op_type_id, v_sell_op_type_id, v_redemption_op_type_id)
        ) THEN
            -- Батч-вставка покупок (transaction_type = 1)
            IF EXISTS (SELECT 1 FROM temp_sorted_ops WHERE operation_type = v_buy_op_type_id) THEN
                CREATE TEMP TABLE temp_inserted_buy_tx (
                    tx_id bigint,
                    portfolio_asset_id bigint,
                    quantity numeric,
                    price numeric,
                    transaction_date timestamp without time zone
                );
                
                WITH inserted_transactions AS (
                    INSERT INTO transactions (
                        portfolio_asset_id,
                        transaction_type,
                        quantity,
                        price,
                        transaction_date,
                        realized_pnl
                    )
                    SELECT 
                        t.portfolio_asset_id,
                        1,
                        t.quantity,
                        t.price,
                        t.operation_date,
                        0
                    FROM temp_sorted_ops t
                    WHERE t.operation_type = v_buy_op_type_id
                      AND t.portfolio_asset_id IS NOT NULL
                      AND t.quantity IS NOT NULL
                      AND t.price IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1
                          FROM transactions existing
                          WHERE existing.portfolio_asset_id = t.portfolio_asset_id
                            AND existing.transaction_date::timestamp without time zone = t.operation_date
                            AND existing.transaction_type = 1
                            AND ABS(existing.price - t.price) < 0.000001
                            AND ABS(existing.quantity - t.quantity) < 0.000001
                      )
                    RETURNING 
                        id,
                        portfolio_asset_id,
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
                
                INSERT INTO temp_tx_payment_map (transaction_id, payment, user_id, portfolio_asset_id, transaction_type, transaction_date, price, quantity, currency_id)
                SELECT
                    tibt.tx_id,
                    COALESCE(tso.payment, 0),
                    p.user_id,
                    tibt.portfolio_asset_id,
                    1,
                    tibt.transaction_date,
                    tibt.price,
                    tibt.quantity,
                    COALESCE(tso.currency_id, (SELECT a.quote_asset_id FROM portfolio_assets pa JOIN assets a ON a.id = pa.asset_id WHERE pa.id = tibt.portfolio_asset_id LIMIT 1), 1)
                FROM temp_inserted_buy_tx tibt
                JOIN transactions t ON t.id = tibt.tx_id
                JOIN portfolio_assets pa ON pa.id = tibt.portfolio_asset_id
                JOIN portfolios p ON p.id = pa.portfolio_id
                LEFT JOIN temp_sorted_ops tso ON
                    tso.portfolio_asset_id = tibt.portfolio_asset_id
                    AND tso.operation_type = v_buy_op_type_id
                    AND (
                        tso.operation_date = tibt.transaction_date
                        OR ABS(EXTRACT(EPOCH FROM (tso.operation_date - tibt.transaction_date))) < 1
                    )
                    AND ABS(COALESCE(tso.price, 0) - COALESCE(tibt.price, 0)) < 0.0001
                    AND ABS(COALESCE(tso.quantity, 0) - COALESCE(tibt.quantity, 0)) < 0.0001;

                INSERT INTO temp_tx_payment_map (transaction_id, payment, user_id, portfolio_asset_id, transaction_type, transaction_date, price, quantity, currency_id)
                SELECT DISTINCT ON (tibt.tx_id)
                    tibt.tx_id,
                    COALESCE(tso.payment, 0),
                    p.user_id,
                    tibt.portfolio_asset_id,
                    1,
                    tibt.transaction_date,
                    tibt.price,
                    tibt.quantity,
                    COALESCE(tso.currency_id, (SELECT a.quote_asset_id FROM portfolio_assets pa JOIN assets a ON a.id = pa.asset_id WHERE pa.id = tibt.portfolio_asset_id LIMIT 1), 1)
                FROM temp_inserted_buy_tx tibt
                JOIN transactions t ON t.id = tibt.tx_id
                JOIN portfolio_assets pa ON pa.id = tibt.portfolio_asset_id
                JOIN portfolios p ON p.id = pa.portfolio_id
                LEFT JOIN temp_sorted_ops tso ON
                    tso.portfolio_asset_id = tibt.portfolio_asset_id
                    AND tso.operation_type = v_buy_op_type_id
                    AND tso.operation_date::date = tibt.transaction_date::date
                    AND ABS(COALESCE(tso.price, 0) - COALESCE(tibt.price, 0)) < 0.0001
                    AND ABS(COALESCE(tso.quantity, 0) - COALESCE(tibt.quantity, 0)) < 0.0001
                WHERE NOT EXISTS (
                    SELECT 1 FROM temp_tx_payment_map tpm WHERE tpm.transaction_id = tibt.tx_id
                )
                AND tso.payment IS NOT NULL
                AND tso.payment != 0
                ORDER BY tibt.tx_id, ABS(EXTRACT(EPOCH FROM (tso.operation_date - tibt.transaction_date)));
                
                SELECT COALESCE(array_agg(tx_id), ARRAY[]::bigint[]) INTO v_tx_ids FROM temp_inserted_buy_tx;
                v_inserted_count := v_inserted_count + (SELECT COUNT(*) FROM temp_inserted_buy_tx);
                
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

            -- Продажи и погашения по одной (FIFO)
            FOR v_tx_item IN 
                SELECT 
                    t.user_id,
                    t.portfolio_asset_id,
                    t.operation_date,
                    t.quantity,
                    t.price,
                    t.payment,
                    t.currency_id,
                    t.original_json,
                    CASE 
                        WHEN t.operation_type = v_sell_op_type_id THEN 2
                        WHEN t.operation_type = v_redemption_op_type_id THEN 3
                        ELSE 2
                    END AS transaction_type
                FROM temp_sorted_ops t
                WHERE t.operation_type IN (v_sell_op_type_id, v_redemption_op_type_id)
                  AND t.portfolio_asset_id IS NOT NULL
                  AND t.quantity IS NOT NULL
                  AND t.price IS NOT NULL
                ORDER BY t.operation_date
            LOOP
                BEGIN
                    SELECT portfolio_id INTO v_portfolio_id
                    FROM portfolio_assets
                    WHERE id = v_tx_item.portfolio_asset_id;

                    IF v_portfolio_id IS NULL THEN
                        RAISE EXCEPTION 'Portfolio not found for portfolio_asset_id=%', v_tx_item.portfolio_asset_id;
                    END IF;

                    v_tx_date := v_tx_item.operation_date;
                    
                    IF EXISTS (
                        SELECT 1
                        FROM transactions existing
                        WHERE existing.portfolio_asset_id = v_tx_item.portfolio_asset_id
                          AND existing.transaction_date::timestamp without time zone = v_tx_date
                          AND existing.transaction_type = v_tx_item.transaction_type
                          AND ABS(existing.price - v_tx_item.price) < 0.000001
                          AND ABS(existing.quantity - v_tx_item.quantity) < 0.000001
                    ) THEN
                        v_failed_count := v_failed_count + 1;
                        v_failed_ops := v_failed_ops || jsonb_build_object(
                            'operation', v_tx_item.original_json,
                            'error', 'Transaction already exists (duplicate)'
                        );
                        CONTINUE;
                    END IF;

                    INSERT INTO transactions (
                        portfolio_asset_id,
                        transaction_type,
                        quantity,
                        price,
                        transaction_date,
                        realized_pnl
                    )
                    VALUES (
                        v_tx_item.portfolio_asset_id,
                        v_tx_item.transaction_type,
                        v_tx_item.quantity,
                        v_tx_item.price,
                        v_tx_date,
                        0
                    )
                    RETURNING id INTO v_tx_id;

                    IF v_tx_id IS NULL THEN
                        RAISE EXCEPTION 'Failed to insert transaction: transaction_id is NULL';
                    END IF;

                    v_currency_id := COALESCE(
                        v_tx_item.currency_id,
                        (SELECT a.quote_asset_id FROM portfolio_assets pa JOIN assets a ON a.id = pa.asset_id WHERE pa.id = v_tx_item.portfolio_asset_id LIMIT 1),
                        1
                    );
                    
                    INSERT INTO temp_tx_payment_map (transaction_id, payment, user_id, portfolio_asset_id, transaction_type, transaction_date, price, quantity, currency_id)
                    VALUES (
                        v_tx_id,
                        COALESCE(v_tx_item.payment, 0),
                        v_tx_item.user_id,
                        v_tx_item.portfolio_asset_id,
                        v_tx_item.transaction_type,
                        v_tx_date,
                        v_tx_item.price,
                        v_tx_item.quantity,
                        v_currency_id
                    );

                    v_remaining := v_tx_item.quantity;
                    v_realized := 0;

                    FOR lot IN
                        SELECT *
                        FROM fifo_lots
                        WHERE portfolio_asset_id = v_tx_item.portfolio_asset_id
                          AND remaining_qty > 0
                        ORDER BY created_at, id
                        FOR UPDATE
                    LOOP
                        EXIT WHEN v_remaining <= 0;

                        IF v_tx_item.transaction_type IN (2, 3) THEN
                            IF lot.remaining_qty <= v_remaining THEN
                                v_realized := v_realized + lot.remaining_qty * (v_tx_item.price - lot.price);
                            ELSE
                                v_realized := v_realized + v_remaining * (v_tx_item.price - lot.price);
                            END IF;
                        END IF;

                        IF lot.remaining_qty <= v_remaining THEN
                            v_remaining := v_remaining - lot.remaining_qty;
                            UPDATE fifo_lots SET remaining_qty = 0 WHERE id = lot.id;
                        ELSE
                            UPDATE fifo_lots SET remaining_qty = lot.remaining_qty - v_remaining WHERE id = lot.id;
                            v_remaining := 0;
                        END IF;
                    END LOOP;

                    IF v_remaining > 0 THEN
                        RAISE EXCEPTION 'Not enough quantity to % (portfolio_asset_id=%, remaining=%)',
                            CASE WHEN v_tx_item.transaction_type = 2 THEN 'sell' ELSE 'redeem' END,
                            v_tx_item.portfolio_asset_id,
                            v_remaining;
                    END IF;

                    IF v_tx_item.transaction_type IN (2, 3) AND v_realized != 0 THEN
                        UPDATE transactions SET realized_pnl = v_realized WHERE id = v_tx_id;
                    END IF;

                    v_tx_ids := array_append(v_tx_ids, v_tx_id);
                    v_inserted_count := v_inserted_count + 1;

                EXCEPTION
                    WHEN OTHERS THEN
                        v_failed_count := v_failed_count + 1;
                        v_error_text := SQLERRM;
                        v_failed_ops := v_failed_ops || jsonb_build_object(
                            'operation', v_tx_item.original_json,
                            'error', v_error_text
                        );
                END;
            END LOOP;

            -- Батч-создание cash_operations для всех вставленных транзакций (Buy/Sell/Redemption)
            -- currency из переданных данных или из актива (quote_asset_id); amount_rub по курсу на дату операции
            IF array_length(v_tx_ids, 1) > 0 THEN
                INSERT INTO cash_operations (user_id, portfolio_id, type, amount, currency, date, transaction_id, asset_id, amount_rub)
                SELECT
                    p.user_id,
                    pa.portfolio_id,
                    CASE 
                        WHEN t.transaction_type = 1 THEN v_buy_op_type_id
                        WHEN t.transaction_type = 2 THEN v_sell_op_type_id
                        WHEN t.transaction_type = 3 THEN v_redemption_op_type_id
                    END,
                    CASE 
                        WHEN t.transaction_type = 1 THEN -ABS(COALESCE(tpm.payment, 0))
                        WHEN t.transaction_type = 2 THEN ABS(COALESCE(tpm.payment, 0))
                        WHEN t.transaction_type = 3 THEN ABS(COALESCE(tpm.payment, 0))
                        ELSE COALESCE(tpm.payment, 0)
                    END,
                    COALESCE(tpm.currency_id, 1),
                    t.transaction_date,
                    t.id,
                    pa.asset_id,
                    -- amount_rub с тем же знаком, что и amount (Buy — отрицательный, Sell/Redemption — положительный)
                    (CASE WHEN t.transaction_type = 1 THEN -1 ELSE 1 END)
                    * (CASE
                        WHEN COALESCE(tpm.currency_id, 1) IN (1, v_rub_currency_id) THEN ABS(COALESCE(tpm.payment, 0))
                        ELSE ABS(COALESCE(tpm.payment, 0)) * COALESCE(
                            (SELECT price FROM asset_prices
                             WHERE asset_id = COALESCE(tpm.currency_id, 1)
                               AND trade_date <= t.transaction_date::date
                             ORDER BY trade_date DESC
                             LIMIT 1),
                            (SELECT curr_price FROM asset_latest_prices
                             WHERE asset_id = COALESCE(tpm.currency_id, 1)
                             LIMIT 1),
                            1
                        )
                    END)
                FROM transactions t
                JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
                JOIN portfolios p ON p.id = pa.portfolio_id
                LEFT JOIN temp_tx_payment_map tpm ON tpm.transaction_id = t.id
                WHERE t.id = ANY(v_tx_ids)
                  AND t.transaction_type IN (1, 2, 3)
                  AND NOT EXISTS (
                      SELECT 1 
                      FROM cash_operations co 
                      WHERE co.transaction_id = t.id
                  );
            END IF;
        END IF;
    END IF;

    -- ========== Денежные операции (Dividend, Coupon, Commission, Tax, Deposit, Withdraw) — после транзакций ==========
    FOR v_op_record IN SELECT * FROM temp_sorted_ops
    LOOP
        IF v_op_record.operation_type IN (v_buy_op_type_id, v_sell_op_type_id, v_redemption_op_type_id) THEN
            CONTINUE;
        END IF;

        BEGIN
            v_portfolio_id := v_op_record.portfolio_id;
            v_operation_type := v_op_record.operation_type;
            v_asset_id := v_op_record.asset_id;
            v_portfolio_asset_id := v_op_record.portfolio_asset_id;
            v_operation_date := v_op_record.operation_date;

            IF v_asset_id IS NULL AND v_portfolio_asset_id IS NOT NULL THEN
                SELECT asset_id INTO v_asset_id
                FROM portfolio_assets
                WHERE id = v_portfolio_asset_id;
            END IF;

            -- Валюта: из переданных данных, иначе валюта актива (quote_asset_id), иначе RUB
            v_currency_id := COALESCE(
                v_op_record.currency_id,
                (SELECT quote_asset_id FROM assets WHERE id = v_asset_id LIMIT 1),
                1
            );

            SELECT EXISTS(SELECT 1 FROM portfolios WHERE id = v_portfolio_id AND user_id = v_op_record.user_id)
            INTO v_portfolio_exists;
            
            IF NOT v_portfolio_exists THEN
                RAISE EXCEPTION 'Портфель % не найден или не принадлежит пользователю', v_portfolio_id;
            END IF;

            SELECT id INTO v_op_type_id
            FROM operations_type
            WHERE id = v_operation_type;
            
            IF v_op_type_id IS NULL THEN
                RAISE EXCEPTION 'Тип операции % не найден', v_operation_type;
            END IF;
            
            IF v_asset_id IS NOT NULL AND v_operation_type IN (3, 4, 7, 8) THEN
                SELECT min(t.transaction_date)
                INTO v_first_buy_date
                FROM transactions t
                JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
                WHERE pa.portfolio_id = v_portfolio_id
                  AND pa.asset_id = v_asset_id
                  AND t.transaction_type = 1;
                
                IF v_first_buy_date IS NULL THEN
                    RAISE EXCEPTION 'Невозможно создать операцию по активу до первой покупки. Сначала создайте транзакцию покупки актива.';
                END IF;
                
                IF v_operation_date < v_first_buy_date THEN
                    RAISE EXCEPTION 'Невозможно создать операцию на дату % раньше первой покупки актива (%). Сначала создайте транзакцию покупки.', 
                        v_operation_date, v_first_buy_date;
                END IF;
            END IF;

            -- amount_rub по курсу валюты на дату операции
            IF v_currency_id = v_rub_currency_id OR v_currency_id = 1 THEN
                v_amount_rub := v_op_record.amount;
            ELSE
                SELECT quote_asset_id INTO v_currency_quote_asset_id
                FROM assets
                WHERE id = v_currency_id;
                
                IF v_currency_quote_asset_id IS NOT NULL 
                   AND v_currency_quote_asset_id != v_rub_currency_id 
                   AND v_currency_quote_asset_id != 1 
                   AND v_currency_quote_asset_id > 0 THEN
                    -- Курс валюты к quote (напр. BTC -> USD)
                    SELECT price INTO v_currency_to_quote_rate
                    FROM asset_prices
                    WHERE asset_id = v_currency_id
                      AND trade_date <= v_operation_date::date
                    ORDER BY trade_date DESC
                    LIMIT 1;
                    
                    IF v_currency_to_quote_rate IS NULL THEN
                        SELECT curr_price INTO v_currency_to_quote_rate
                        FROM asset_latest_prices
                        WHERE asset_id = v_currency_id;
                    END IF;
                    
                    IF v_currency_to_quote_rate IS NULL OR v_currency_to_quote_rate <= 0 THEN
                        SELECT ticker INTO v_currency_ticker FROM assets WHERE id = v_currency_id LIMIT 1;
                        RAISE EXCEPTION 'Курс валюты % не найден на дату %. Добавьте цену в asset_prices или выберите другую валюту.', COALESCE(v_currency_ticker, 'ID=' || v_currency_id), v_operation_date::date;
                    END IF;
                    
                    v_amount_in_quote := v_op_record.amount * v_currency_to_quote_rate;
                    
                    -- Курс quote к RUB (напр. USD -> RUB)
                    SELECT price INTO v_quote_to_rub_rate
                    FROM asset_prices
                    WHERE asset_id = v_currency_quote_asset_id
                      AND trade_date <= v_operation_date::date
                    ORDER BY trade_date DESC
                    LIMIT 1;
                    
                    IF v_quote_to_rub_rate IS NULL THEN
                        SELECT curr_price INTO v_quote_to_rub_rate
                        FROM asset_latest_prices
                        WHERE asset_id = v_currency_quote_asset_id;
                    END IF;
                    
                    IF v_quote_to_rub_rate IS NULL OR v_quote_to_rub_rate <= 0 THEN
                        SELECT ticker INTO v_quote_ticker FROM assets WHERE id = v_currency_quote_asset_id LIMIT 1;
                        RAISE EXCEPTION 'Курс валюты % к рублю не найден на дату %. Добавьте цену в asset_prices.', COALESCE(v_quote_ticker, 'ID=' || v_currency_quote_asset_id), v_operation_date::date;
                    END IF;
                    
                    v_amount_rub := v_amount_in_quote * v_quote_to_rub_rate;
                ELSE
                    -- Прямой курс валюты к рублю (для валют с quote_asset_id=RUB)
                    SELECT price INTO v_currency_rate
                    FROM asset_prices
                    WHERE asset_id = v_currency_id
                      AND trade_date <= v_operation_date::date
                    ORDER BY trade_date DESC
                    LIMIT 1;
                    
                    IF v_currency_rate IS NULL THEN
                        SELECT curr_price INTO v_currency_rate
                        FROM asset_latest_prices
                        WHERE asset_id = v_currency_id;
                    END IF;
                    
                    IF v_currency_rate IS NULL OR v_currency_rate <= 0 THEN
                        SELECT ticker INTO v_currency_ticker FROM assets WHERE id = v_currency_id LIMIT 1;
                        RAISE EXCEPTION 'Курс валюты % к рублю не найден на дату %. Добавьте цену в asset_prices.', COALESCE(v_currency_ticker, 'ID=' || v_currency_id), v_operation_date::date;
                    END IF;
                    
                    v_amount_rub := v_op_record.amount * v_currency_rate;
                END IF;
            END IF;

            INSERT INTO cash_operations (
                user_id,
                portfolio_id,
                type,
                amount,
                currency,
                date,
                asset_id,
                amount_rub
            )
            VALUES (
                v_op_record.user_id,
                v_portfolio_id,
                v_op_type_id,
                v_op_record.amount,
                v_currency_id,
                v_op_record.operation_date,
                v_asset_id,
                v_amount_rub
            )
            RETURNING id INTO v_op_id;

            v_op_ids := array_append(v_op_ids, v_op_id);
            v_inserted_count := v_inserted_count + 1;
            
            v_created_operations := v_created_operations || jsonb_build_object(
                'date', v_operation_date::text,
                'operation_id', v_op_id,
                'type', 'cash_operation'
            );

        EXCEPTION WHEN OTHERS THEN
            v_failed_count := v_failed_count + 1;
            v_error_text := SQLERRM;
            v_failed_ops := v_failed_ops || jsonb_build_object(
                'operation', v_op_record.original_json,
                'error', v_error_text
            );
        END;
    END LOOP;

    -- ========== Обновление portfolio_assets, позиций и истории портфелей ==========
    FOR v_portfolio_asset_id, v_min_date IN
        SELECT pa_id, (MIN(d) - INTERVAL '1 day')::date
        FROM (
            SELECT pa.id AS pa_id, tso.operation_date::date AS d
            FROM temp_sorted_ops tso
            JOIN portfolio_assets pa ON pa.portfolio_id = tso.portfolio_id AND pa.asset_id = tso.asset_id
            WHERE tso.portfolio_id IS NOT NULL AND tso.asset_id IS NOT NULL AND tso.operation_type IN (3, 4, 7, 8)
            UNION ALL
            SELECT t.portfolio_asset_id, t.transaction_date::date
            FROM transactions t
            WHERE array_length(v_tx_ids, 1) > 0 AND t.id = ANY(v_tx_ids)
        ) u
        GROUP BY pa_id
    LOOP
        BEGIN
            PERFORM update_portfolio_asset(v_portfolio_asset_id);
            PERFORM update_portfolio_asset_positions_from_date(v_portfolio_asset_id, v_min_date);
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'Ошибка при обновлении актива/позиций %: %', v_portfolio_asset_id, SQLERRM;
        END;
    END LOOP;

    FOR v_portfolio_id, v_min_date IN
        SELECT p_id, (MIN(d) - INTERVAL '1 day')::date
        FROM (
            SELECT portfolio_id AS p_id, operation_date::date AS d
            FROM temp_sorted_ops
            WHERE portfolio_id IS NOT NULL
            UNION ALL
            SELECT pa.portfolio_id, t.transaction_date::date
            FROM transactions t
            JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
            WHERE array_length(v_tx_ids, 1) > 0 AND t.id = ANY(v_tx_ids)
        ) u
        GROUP BY p_id
    LOOP
        BEGIN
            PERFORM update_portfolio_values_from_date(v_portfolio_id, v_min_date);
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'Ошибка при обновлении истории портфеля %: %', v_portfolio_id, SQLERRM;
        END;
    END LOOP;

    -- ========== Авто-upsert цен для транзакций (перенесено из backend) ==========
    IF array_length(v_tx_ids, 1) > 0 THEN
        INSERT INTO asset_prices (asset_id, price, trade_date)
        SELECT DISTINCT pa.asset_id, tpm.price, tpm.transaction_date::date
        FROM temp_tx_payment_map tpm
        JOIN portfolio_assets pa ON pa.id = tpm.portfolio_asset_id
        WHERE tpm.price > 0
        ON CONFLICT (asset_id, trade_date) DO NOTHING;

        PERFORM update_asset_latest_prices_batch(
            (SELECT array_agg(DISTINCT pa.asset_id)
             FROM temp_tx_payment_map tpm
             JOIN portfolio_assets pa ON pa.id = tpm.portfolio_asset_id)
        );
    END IF;

    -- ========== Авто-проверка missed payouts для Dividend/Coupon (перенесено из backend) ==========
    FOR v_portfolio_asset_id IN
        SELECT DISTINCT tso.portfolio_asset_id
        FROM temp_sorted_ops tso
        WHERE tso.portfolio_asset_id IS NOT NULL
          AND (tso.operation_type IN (3, 4) OR tso.operation_type IN (v_buy_op_type_id))
    LOOP
        BEGIN
            PERFORM check_missed_payouts(v_portfolio_asset_id);
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'Ошибка при проверке missed payouts для %: %', v_portfolio_asset_id, SQLERRM;
        END;
    END LOOP;

    DROP TABLE IF EXISTS temp_sorted_ops;
    DROP TABLE IF EXISTS temp_tx_payment_map;

    RETURN jsonb_build_object(
        'inserted_count', v_inserted_count,
        'failed_count', v_failed_count,
        'failed_operations', v_failed_ops,
        'operation_ids', to_jsonb(v_op_ids),
        'transaction_ids', to_jsonb(v_tx_ids),
        'created', v_created_operations
    );

EXCEPTION
    WHEN OTHERS THEN
        DROP TABLE IF EXISTS temp_sorted_ops;
        DROP TABLE IF EXISTS temp_tx_payment_map;
        DROP TABLE IF EXISTS temp_inserted_buy_tx;
        RAISE;
END;
$$;
