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
BEGIN
    IF p_operations IS NULL OR jsonb_array_length(p_operations) = 0 THEN
        RETURN jsonb_build_object(
            'inserted_count', 0,
            'failed_count', 0,
            'failed_operations', '[]'::jsonb,
            'operation_ids', '[]'::jsonb,
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

    -- Сортируем операции по дате
    CREATE TEMP TABLE temp_sorted_ops AS
    SELECT 
        (op->>'user_id')::uuid as user_id,
        (op->>'portfolio_id')::bigint as portfolio_id,
        (op->>'operation_type')::int as operation_type,
        (op->>'amount')::numeric as amount,
        COALESCE((op->>'currency_id')::bigint, 1) as currency_id,
        CASE 
            WHEN (op->>'operation_date')::text ~ 'T' OR (op->>'operation_date')::text ~ ' ' THEN
                (op->>'operation_date')::timestamp without time zone
            ELSE
                (op->>'operation_date')::date::timestamp without time zone
        END as operation_date,
        (op->>'asset_id')::bigint as asset_id,
        (op->>'portfolio_asset_id')::bigint as portfolio_asset_id,
        (op->>'dividend_yield')::numeric as dividend_yield,
        op as original_json
    FROM jsonb_array_elements(p_operations) op
    ORDER BY 
        operation_date,
        (op->>'portfolio_id')::bigint,
        (op->>'operation_type')::int;

    -- Обрабатываем каждую операцию
    FOR v_op_record IN SELECT * FROM temp_sorted_ops
    LOOP
        BEGIN
            v_portfolio_id := v_op_record.portfolio_id;
            v_operation_type := v_op_record.operation_type;
            v_asset_id := v_op_record.asset_id;
            v_portfolio_asset_id := v_op_record.portfolio_asset_id;
            -- Сохраняем полную дату с временем (не обрезаем до date)
            v_operation_date := v_op_record.operation_date;

            -- Если asset_id не передан, но есть portfolio_asset_id, получаем asset_id из portfolio_assets
            IF v_asset_id IS NULL AND v_portfolio_asset_id IS NOT NULL THEN
                SELECT asset_id INTO v_asset_id
                FROM portfolio_assets
                WHERE id = v_portfolio_asset_id;
            END IF;

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
            
            -- ВАЛИДАЦИЯ: Если операция связана с активом (Commission, Tax, Dividend, Coupon),
            -- Операции без актива (Deposit, Withdraw) можно создавать в любое время
            IF v_asset_id IS NOT NULL AND v_operation_type IN (3, 4, 7, 8) THEN
                SELECT min(t.transaction_date)
                INTO v_first_buy_date
                FROM transactions t
                JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
                WHERE pa.portfolio_id = v_portfolio_id
                  AND pa.asset_id = v_asset_id
                  AND t.transaction_type = 1;  -- Только покупки (Buy)
                
                -- Если нет покупок, запрещаем создание операций по активу
                IF v_first_buy_date IS NULL THEN
                    RAISE EXCEPTION 'Невозможно создать операцию по активу до первой покупки. Сначала создайте транзакцию покупки актива.';
                END IF;
                
                -- Если дата операции раньше первой покупки, запрещаем
                -- Сравниваем timestamp с timestamp (сохраняем время)
                IF v_operation_date < v_first_buy_date THEN
                    RAISE EXCEPTION 'Невозможно создать операцию на дату % раньше первой покупки актива (%). Сначала создайте транзакцию покупки.', 
                        v_operation_date, v_first_buy_date;
                END IF;
            END IF;

            -- Рассчитываем amount_rub
            IF v_op_record.currency_id = v_rub_currency_id OR v_op_record.currency_id = 1 THEN
                v_amount_rub := v_op_record.amount;
            ELSE
                SELECT quote_asset_id INTO v_currency_quote_asset_id
                FROM assets
                WHERE id = v_op_record.currency_id;
                
                -- Двухшаговая конвертация через quote_asset (например, BTC -> USD -> RUB)
                IF v_currency_quote_asset_id IS NOT NULL 
                   AND v_currency_quote_asset_id != v_rub_currency_id 
                   AND v_currency_quote_asset_id != 1 
                   AND v_currency_quote_asset_id > 0 THEN
                    -- ШАГ 1: Конвертируем валюту операции в quote_asset
                    SELECT price INTO v_currency_to_quote_rate
                    FROM asset_prices
                    WHERE asset_id = v_op_record.currency_id
                      AND trade_date <= v_operation_date::date
                    ORDER BY trade_date DESC
                    LIMIT 1;
                    
                    IF v_currency_to_quote_rate IS NULL THEN
                        SELECT curr_price INTO v_currency_to_quote_rate
                        FROM asset_latest_prices
                        WHERE asset_id = v_op_record.currency_id;
                    END IF;
                    
                    IF v_currency_to_quote_rate IS NULL OR v_currency_to_quote_rate <= 0 THEN
                        v_currency_to_quote_rate := 1;
                    END IF;
                    
                    v_amount_in_quote := v_op_record.amount * v_currency_to_quote_rate;
                    
                    -- ШАГ 2: Конвертируем quote_asset в рубли
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
                        v_quote_to_rub_rate := 1;
                    END IF;
                    
                    v_amount_rub := v_amount_in_quote * v_quote_to_rub_rate;
                ELSE
                    -- Прямая конвертация в рубли
                    SELECT price INTO v_currency_rate
                    FROM asset_prices
                    WHERE asset_id = v_op_record.currency_id
                      AND trade_date <= v_operation_date::date
                    ORDER BY trade_date DESC
                    LIMIT 1;
                    
                    IF v_currency_rate IS NULL THEN
                        SELECT curr_price INTO v_currency_rate
                        FROM asset_latest_prices
                        WHERE asset_id = v_op_record.currency_id;
                    END IF;
                    
                    IF v_currency_rate IS NULL THEN
                        v_currency_rate := 1;
                    END IF;
                    
                    v_amount_rub := v_op_record.amount * v_currency_rate;
                END IF;
            END IF;

            -- Вставляем операцию
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
                v_op_record.currency_id,
                v_op_record.operation_date,
                v_asset_id,
                v_amount_rub
            )
            RETURNING id INTO v_op_id;

            -- Добавляем в список успешных операций
            v_op_ids := array_append(v_op_ids, v_op_id);
            v_inserted_count := v_inserted_count + 1;
            
            -- Добавляем в список created для совместимости с create_operations_batch
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

    -- ШАГ 1: Обновляем позиции активов для операций с asset_id (Commission/Tax/Dividend/Coupon)
    -- ОПТИМИЗАЦИЯ: Вызываем один раз для каждого уникального portfolio_asset_id с минимальной датой операции
    -- Это нужно сделать ПЕРВЫМ, так как portfolio_daily_values агрегирует данные из portfolio_daily_positions
    FOR v_portfolio_asset_id, v_min_date IN 
        SELECT 
            pa.id,
            MIN(tso.operation_date::date) - INTERVAL '1 day' AS min_date
        FROM temp_sorted_ops tso
        JOIN portfolio_assets pa ON pa.portfolio_id = tso.portfolio_id 
                                 AND pa.asset_id = tso.asset_id
        WHERE tso.portfolio_id IS NOT NULL
          AND tso.asset_id IS NOT NULL
          AND tso.operation_type IN (3, 4, 7, 8)  -- Dividend, Coupon, Commission, Tax
        GROUP BY pa.id
    LOOP
        BEGIN
            PERFORM update_portfolio_asset_positions_from_date(
                v_portfolio_asset_id,
                v_min_date::date
            );
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'Ошибка при обновлении позиций актива %: %', v_portfolio_asset_id, SQLERRM;
        END;
    END LOOP;

    -- ШАГ 2: Обновляем историю портфелей один раз для каждого портфеля с минимальной датой операции
    -- ОПТИМИЗАЦИЯ: Вызываем один раз для каждого портфеля с минимальной датой вместо вызова для каждой даты
    -- Это агрегирует данные из portfolio_daily_positions в portfolio_daily_values
    FOR v_portfolio_id, v_min_date IN 
        SELECT 
            portfolio_id,
            MIN(operation_date::date) - INTERVAL '1 day' AS min_date
        FROM temp_sorted_ops
        WHERE portfolio_id IS NOT NULL
        GROUP BY portfolio_id
    LOOP
        BEGIN
            PERFORM update_portfolio_values_from_date(
                v_portfolio_id,
                v_min_date::date
            );
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'Ошибка при обновлении истории портфеля %: %', v_portfolio_id, SQLERRM;
        END;
    END LOOP;

    -- Примечание: проверка неполученных выплат НЕ выполняется здесь автоматически
    -- Это сделано для предотвращения ложных срабатываний при батч-импорте от брокера,
    -- когда операции могут быть еще не вставлены на момент проверки.
    -- Проверку следует вызывать отдельно после завершения всех батч-операций.

    -- Удаляем временную таблицу
    DROP TABLE IF EXISTS temp_sorted_ops;

    -- Возвращаем результат
    RETURN jsonb_build_object(
        'inserted_count', v_inserted_count,
        'failed_count', v_failed_count,
        'failed_operations', v_failed_ops,
        'operation_ids', to_jsonb(v_op_ids),
        'created', v_created_operations
    );

EXCEPTION
    WHEN OTHERS THEN
        -- Удаляем временную таблицу в случае ошибки
        DROP TABLE IF EXISTS temp_sorted_ops;
        RAISE;
END;
$$;
