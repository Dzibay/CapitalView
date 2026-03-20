-- Батчевое обновление операций: удаление нужных операций и связанных транзакций,
-- затем повторное создание через apply_operations_batch (единая логика пересчёта).
-- Вход: p_updates — jsonb-массив объектов:
--   { "operation_id": bigint, "date": text (опц.), "amount": numeric (опц.),
--     "quantity": numeric (опц.), "price": numeric (опц.) }

CREATE OR REPLACE FUNCTION update_operations_batch(p_updates jsonb)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    v_elem jsonb;
    v_op_id bigint;
    v_new_date date;
    v_new_amount numeric;
    v_new_quantity numeric;
    v_new_price numeric;
    v_apply_payload jsonb := '[]'::jsonb;
    v_op_ids bigint[];
    v_transaction_ids bigint[];
    v_apply_result jsonb;
    v_row record;
    v_operation_date_ts timestamp without time zone;
BEGIN
    IF p_updates IS NULL OR jsonb_array_length(p_updates) = 0 THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Массив обновлений пуст',
            'updated_count', 0
        );
    END IF;

    CREATE TEMP TABLE temp_updates (
        operation_id bigint PRIMARY KEY,
        new_date date,
        new_amount numeric,
        new_quantity numeric,
        new_price numeric
    );

    FOR v_elem IN SELECT * FROM jsonb_array_elements(p_updates)
    LOOP
        v_op_id := (v_elem->>'operation_id')::bigint;
        IF v_op_id IS NULL THEN
            CONTINUE;
        END IF;

        v_new_date := NULL;
        IF v_elem ? 'date' AND v_elem->>'date' IS NOT NULL AND (v_elem->>'date') <> '' THEN
            BEGIN
                IF (v_elem->>'date')::text ~ 'T' OR (v_elem->>'date')::text ~ ' ' THEN
                    v_new_date := (v_elem->>'date')::timestamp::date;
                ELSE
                    v_new_date := (v_elem->>'date')::date;
                END IF;
            EXCEPTION WHEN OTHERS THEN
                NULL;
            END;
        END IF;

        v_new_amount := NULL;
        IF v_elem ? 'amount' AND v_elem->>'amount' IS NOT NULL THEN
            v_new_amount := (v_elem->>'amount')::numeric;
        END IF;

        v_new_quantity := NULL;
        IF v_elem ? 'quantity' AND v_elem->>'quantity' IS NOT NULL THEN
            v_new_quantity := (v_elem->>'quantity')::numeric;
        END IF;

        v_new_price := NULL;
        IF v_elem ? 'price' AND v_elem->>'price' IS NOT NULL THEN
            v_new_price := (v_elem->>'price')::numeric;
        END IF;

        INSERT INTO temp_updates (operation_id, new_date, new_amount, new_quantity, new_price)
        VALUES (v_op_id, v_new_date, v_new_amount, v_new_quantity, v_new_price)
        ON CONFLICT (operation_id) DO UPDATE SET
            new_date     = COALESCE(EXCLUDED.new_date,     temp_updates.new_date),
            new_amount   = COALESCE(EXCLUDED.new_amount,   temp_updates.new_amount),
            new_quantity = COALESCE(EXCLUDED.new_quantity,  temp_updates.new_quantity),
            new_price    = COALESCE(EXCLUDED.new_price,    temp_updates.new_price);
    END LOOP;

    -- Текущие данные операций и связанных транзакций (до удаления)
    CREATE TEMP TABLE temp_current AS
    SELECT
        co.id AS co_id,
        co.user_id,
        co.portfolio_id,
        co.type AS operation_type,
        co.amount,
        co.currency AS currency_id,
        co.date AS op_date,
        co.transaction_id,
        co.asset_id,
        u.new_date,
        u.new_amount,
        u.new_quantity,
        u.new_price,
        t.portfolio_asset_id,
        t.transaction_type,
        t.quantity,
        t.price
    FROM cash_operations co
    JOIN temp_updates u ON u.operation_id = co.id
    LEFT JOIN transactions t ON t.id = co.transaction_id;

    IF NOT EXISTS (SELECT 1 FROM temp_current) THEN
        DROP TABLE IF EXISTS temp_updates;
        DROP TABLE IF EXISTS temp_current;
        RETURN jsonb_build_object(
            'success', true,
            'updated_count', 0,
            'message', 'Нет операций для обновления'
        );
    END IF;

    -- Собираем payload для apply_operations_batch
    FOR v_row IN SELECT * FROM temp_current ORDER BY op_date, co_id
    LOOP
        v_operation_date_ts := (COALESCE(v_row.new_date, v_row.op_date))::timestamp without time zone;

        IF v_row.transaction_id IS NOT NULL AND v_row.portfolio_asset_id IS NOT NULL THEN
            v_apply_payload := v_apply_payload || jsonb_build_object(
                'user_id',            v_row.user_id,
                'portfolio_id',       v_row.portfolio_id,
                'operation_type',     v_row.operation_type,
                'operation_date',     to_char(v_operation_date_ts, 'YYYY-MM-DD"T"HH24:MI:SS'),
                'portfolio_asset_id', v_row.portfolio_asset_id,
                'asset_id',           v_row.asset_id,
                'quantity',           COALESCE(v_row.new_quantity, v_row.quantity),
                'price',              COALESCE(v_row.new_price,   v_row.price),
                'payment',            COALESCE(v_row.new_amount,  ABS(v_row.amount)),
                'currency_id',        v_row.currency_id
            );
        ELSE
            v_apply_payload := v_apply_payload || jsonb_build_object(
                'user_id',        v_row.user_id,
                'portfolio_id',   v_row.portfolio_id,
                'operation_type', v_row.operation_type,
                'amount',         COALESCE(v_row.new_amount, v_row.amount),
                'currency_id',    COALESCE(v_row.currency_id, 1),
                'operation_date', to_char(v_operation_date_ts, 'YYYY-MM-DD"T"HH24:MI:SS'),
                'asset_id',       v_row.asset_id
            );
        END IF;
    END LOOP;

    -- ID операций и транзакций для удаления
    SELECT array_agg(co_id ORDER BY co_id) INTO v_op_ids FROM temp_current;
    SELECT array_agg(DISTINCT transaction_id) FILTER (WHERE transaction_id IS NOT NULL)
    INTO v_transaction_ids FROM temp_current;

    -- Только удаление: без пересчёта (пересчёт сделает apply_operations_batch)
    IF v_transaction_ids IS NOT NULL AND array_length(v_transaction_ids, 1) > 0 THEN
        DELETE FROM transactions WHERE id = ANY(v_transaction_ids);
    END IF;
    DELETE FROM cash_operations WHERE id = ANY(v_op_ids) AND transaction_id IS NULL;

    -- Повторно создаём операции через apply_operations_batch
    -- (вставка + единый пересчёт: update_portfolio_asset, позиции, история)
    v_apply_result := apply_operations_batch(v_apply_payload);

    DROP TABLE IF EXISTS temp_updates;
    DROP TABLE IF EXISTS temp_current;

    IF v_apply_result IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'apply_operations_batch вернул NULL',
            'updated_count', 0
        );
    END IF;

    IF COALESCE((v_apply_result->>'inserted_count')::int, 0) < jsonb_array_length(v_apply_payload) THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Не все операции восстановлены после обновления',
            'updated_count', COALESCE((v_apply_result->>'inserted_count')::int, 0),
            'apply_result', v_apply_result
        );
    END IF;

    RETURN jsonb_build_object(
        'success', true,
        'updated_count', (v_apply_result->>'inserted_count')::int,
        'apply_result', v_apply_result
    );
EXCEPTION
    WHEN OTHERS THEN
        DROP TABLE IF EXISTS temp_updates;
        DROP TABLE IF EXISTS temp_current;
        RETURN jsonb_build_object(
            'success', false,
            'error', SQLERRM,
            'updated_count', 0
        );
END;
$$;

