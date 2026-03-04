-- Функция для батч-вставки транзакций с автоматическим созданием FIFO-лотов
-- Обеспечивает ACID-совместимость и правильную обработку FIFO
--
-- Параметры:
--   p_transactions - JSON массив транзакций:
--     [
--       {
--         "user_id": "uuid",
--         "portfolio_asset_id": bigint,
--         "transaction_type": int,  -- 1=buy, 2=sell, 3=redemption
--         "quantity": numeric,
--         "price": numeric,
--         "transaction_date": date
--       },
--       ...
--     ]
--
-- Возвращает:
--   JSON объект с результатами:
--     {
--       "inserted_count": integer,
--       "failed_count": integer,
--       "failed_transactions": [...],
--       "transaction_ids": [...]
--     }
--
-- Логика:
-- 1. Все операции выполняются в одной транзакции (ACID)
-- 2. Транзакции сортируются по дате
-- 3. Покупки вставляются батчем и создают FIFO-лоты
-- 4. Продажи и погашения обрабатываются по одной с проверкой количества
-- 5. Денежные операции создаются автоматически через триггер

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
    v_tx_date timestamp without time zone;  -- Для преобразования даты в timestamp
    v_buy_op_type_id bigint;
    v_sell_op_type_id bigint;
    v_redemption_op_type_id bigint;
    v_tx_record RECORD;
BEGIN
    -- Проверяем входные данные
    IF p_transactions IS NULL OR jsonb_array_length(p_transactions) = 0 THEN
        RETURN jsonb_build_object(
            'inserted_count', 0,
            'failed_count', 0,
            'failed_transactions', '[]'::jsonb,
            'transaction_ids', '[]'::jsonb
        );
    END IF;

    -- Сортируем транзакции по дате и времени (важно для FIFO)
    -- Используем временную таблицу для сортировки
    -- КРИТИЧНО: Используем timestamp, а не date, чтобы различать транзакции с разницей во времени
    CREATE TEMP TABLE temp_sorted_tx AS
    SELECT 
        (tx->>'user_id')::uuid as user_id,
        (tx->>'portfolio_asset_id')::bigint as portfolio_asset_id,
        (tx->>'transaction_type')::int as transaction_type,
        (tx->>'quantity')::numeric as quantity,
        (tx->>'price')::numeric as price,
        -- Используем timestamp для сохранения времени (не только даты)
        -- Если передан timestamp - используем его, если только date - преобразуем в timestamp
        CASE 
            WHEN (tx->>'transaction_date')::text ~ 'T' OR (tx->>'transaction_date')::text ~ ' ' THEN
                (tx->>'transaction_date')::timestamp without time zone
            ELSE
                (tx->>'transaction_date')::date::timestamp without time zone
        END as transaction_date,
        tx as original_json
    FROM jsonb_array_elements(p_transactions) tx
    ORDER BY 
        transaction_date,  -- Сортируем по timestamp (включая время)
        (tx->>'portfolio_asset_id')::bigint,
        (tx->>'transaction_type')::int;
    
    -- Создаем временную таблицу для хранения соответствия между вставленными транзакциями и исходными данными
    -- Это позволит надежно сопоставить payment из original_json с вставленными транзакциями
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

    -- ========================================================================
    -- 1. ВСТАВКА ПОКУПОК БАТЧЕМ С АТОМАРНОЙ ПРОВЕРКОЙ ДУБЛИКАТОВ
    -- ========================================================================
    IF EXISTS (SELECT 1 FROM temp_sorted_tx WHERE transaction_type = 1) THEN
        -- Создаем временную таблицу для хранения данных вставленных транзакций
        CREATE TEMP TABLE temp_inserted_buy_tx (
            tx_id bigint,
            portfolio_asset_id bigint,
            quantity numeric,
            price numeric,
            transaction_date timestamp without time zone
        );
        
        -- Вставляем покупки батчем с проверкой дубликатов
        -- Используем CTE для вставки и сохранения данных вставленных транзакций
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
              -- АТОМАРНАЯ ПРОВЕРКА ДУБЛИКАТОВ: проверяем, что такой транзакции еще нет
              -- Сравниваем по portfolio_asset_id, transaction_date, transaction_type, price, quantity
              AND NOT EXISTS (
                  SELECT 1
                  FROM transactions existing
                  WHERE existing.portfolio_asset_id = t.portfolio_asset_id
                    -- КРИТИЧНО: Сравниваем timestamp с точностью, чтобы различать транзакции с разницей во времени
                    -- Оба поля имеют тип timestamp, поэтому сравнение учитывает время
                    AND existing.transaction_date::timestamp without time zone = t.transaction_date
                    AND existing.transaction_type = t.transaction_type
                    AND ABS(existing.price - t.price) < 0.000001  -- Сравнение с учетом округления
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
        
        -- Сохраняем соответствие между вставленными транзакциями и payment из исходных данных
        -- Используем temp_inserted_buy_tx и LEFT JOIN с temp_sorted_tx для получения payment
        -- КРИТИЧНО: Используем LEFT JOIN, чтобы не потерять транзакции, если JOIN не найдет совпадение
        -- Также используем более гибкое сравнение для transaction_date (с учетом возможных различий в миллисекундах)
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
            -- Более гибкое сравнение transaction_date: учитываем возможные различия в миллисекундах
            AND (
                tst.transaction_date = tibt.transaction_date
                OR ABS(EXTRACT(EPOCH FROM (tst.transaction_date - tibt.transaction_date))) < 1  -- Разница менее 1 секунды
            )
            AND ABS(COALESCE(tst.price, 0) - COALESCE(tibt.price, 0)) < 0.0001
            AND ABS(COALESCE(tst.quantity, 0) - COALESCE(tibt.quantity, 0)) < 0.0001;
        
        -- Попытка найти payment для транзакций, которые не были найдены первым способом
        -- Используем более широкий поиск (по дате без времени)
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
        
        -- Подсчитываем количество вставленных транзакций
        SELECT COUNT(*) INTO v_inserted_count FROM temp_inserted_buy_tx;
        
        -- Собираем ID вставленных транзакций
        SELECT COALESCE(array_agg(tx_id), ARRAY[]::bigint[]) INTO v_tx_ids FROM temp_inserted_buy_tx;
        
        -- Создаем FIFO-лоты ТОЛЬКО из успешно вставленных покупок
        -- КРИТИЧНО: Каждая вставленная транзакция получает свой лот
        -- Даже если две транзакции имеют одинаковое время, цену и количество,
        -- они должны создать два отдельных лота
        -- Используем tx_id для связи, чтобы гарантировать, что каждая транзакция получит свой лот
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
        -- НЕ проверяем дубликаты лотов здесь, т.к.:
        -- 1. Мы уже проверили дубликаты транзакций выше
        -- 2. Каждая вставленная транзакция должна получить свой лот
        -- 3. Если две транзакции имеют одинаковые параметры, они обе должны создать лоты
        -- Это важно для правильной работы FIFO при продажах
        ORDER BY t.transaction_date, t.tx_id;  -- Сортируем также по ID для детерминированности
        
        -- Удаляем временную таблицу
        DROP TABLE temp_inserted_buy_tx;
    END IF;

    -- ========================================================================
    -- 2. ОБРАБОТКА ПРОДАЖ И ПОГАШЕНИЙ С ПРОВЕРКОЙ КОЛИЧЕСТВА
    -- ========================================================================
    IF EXISTS (SELECT 1 FROM temp_sorted_tx WHERE transaction_type IN (2, 3)) THEN
        FOR v_tx_item IN 
            SELECT original_json 
            FROM temp_sorted_tx 
            WHERE transaction_type IN (2, 3)
            ORDER BY transaction_date
        LOOP
            BEGIN
                -- Получаем portfolio_id
                SELECT portfolio_id
                INTO v_portfolio_id
                FROM portfolio_assets
                WHERE id = (v_tx_item->>'portfolio_asset_id')::bigint;

                IF v_portfolio_id IS NULL THEN
                    RAISE EXCEPTION 'Portfolio not found for portfolio_asset_id=%', 
                        (v_tx_item->>'portfolio_asset_id')::bigint;
                END IF;

                -- АТОМАРНАЯ ПРОВЕРКА ДУБЛИКАТОВ перед вставкой продажи
                -- Проверяем, что такой транзакции еще нет
                -- КРИТИЧНО: Преобразуем transaction_date в timestamp для точного сравнения с учетом времени
                -- Преобразуем дату в timestamp (сохраняем время)
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
                    -- Транзакция уже существует, пропускаем
                    v_failed_count := v_failed_count + 1;
                    v_failed_tx := v_failed_tx || jsonb_build_object(
                        'transaction', v_tx_item,
                        'error', 'Transaction already exists (duplicate)'
                    );
                    CONTINUE;  -- Пропускаем эту транзакцию
                END IF;

                -- Создаем транзакцию продажи
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
                    v_tx_date,  -- Используем преобразованную дату с временем
                    0
                )
                RETURNING id INTO v_tx_id;
                
                -- Проверяем, что транзакция была успешно вставлена
                IF v_tx_id IS NULL THEN
                    RAISE EXCEPTION 'Failed to insert transaction: transaction_id is NULL';
                END IF;
                
                -- Сохраняем соответствие между вставленной транзакцией и payment из исходных данных
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

                -- Обновляем realized_pnl для SELL и REDEMPTION
                IF (v_tx_item->>'transaction_type')::int IN (2, 3) AND v_realized != 0 THEN
                    UPDATE transactions
                    SET realized_pnl = v_realized
                    WHERE id = v_tx_id;
                END IF;

                -- Добавляем ID успешной транзакции
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
    -- Создаем cash_operations батчем для лучшей производительности
    -- Затем включаем триггер обратно
    
    -- Получаем ID типов операций один раз (если есть вставленные транзакции)
    IF array_length(v_tx_ids, 1) > 0 THEN
        SELECT id INTO v_buy_op_type_id FROM operations_type WHERE name = 'Buy' LIMIT 1;
        SELECT id INTO v_sell_op_type_id FROM operations_type WHERE name = 'Sell' LIMIT 1;
        
        -- Получаем ID типа операции Redemption (или Ammortization для обратной совместимости)
        SELECT id INTO v_redemption_op_type_id FROM operations_type WHERE name = 'Redemption' LIMIT 1;
        IF v_redemption_op_type_id IS NULL THEN
            SELECT id INTO v_redemption_op_type_id FROM operations_type WHERE name = 'ammortization' LIMIT 1;
        END IF;
        
        -- Создаем cash_operations батчем для всех вставленных транзакций
        -- ВАЖНО: Используем ТОЛЬКО payment из исходных данных транзакции
        -- Это необходимо для облигаций с накопленным купонным доходом (НКД),
        -- где payment может отличаться от price * quantity
        -- КРИТИЧНО: Для импорта от брокера payment всегда должен быть передан
        -- Используем temp_tx_payment_map для надежного сопоставления payment с транзакциями
        INSERT INTO cash_operations (user_id, portfolio_id, type, amount, currency, date, transaction_id, asset_id)
        SELECT
            t.user_id,
            pa.portfolio_id,
            CASE 
                WHEN t.transaction_type = 1 THEN v_buy_op_type_id
                WHEN t.transaction_type = 2 THEN v_sell_op_type_id
                WHEN t.transaction_type = 3 THEN v_redemption_op_type_id
            END,
            -- Используем payment из temp_tx_payment_map (надежное сопоставление по transaction_id)
            -- Если payment не найден - логируем ошибку и используем 0
            COALESCE(tpm.payment, 0),
            47, -- RUB
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

    -- Удаляем временные таблицы
    DROP TABLE IF EXISTS temp_sorted_tx;
    DROP TABLE IF EXISTS temp_tx_payment_map;

    -- Возвращаем результат
    RETURN jsonb_build_object(
        'inserted_count', v_inserted_count,
        'failed_count', v_failed_count,
        'failed_transactions', v_failed_tx,
        'transaction_ids', to_jsonb(v_tx_ids)
    );

EXCEPTION
    WHEN OTHERS THEN
        -- В случае ошибки откатываем транзакцию
        DROP TABLE IF EXISTS temp_sorted_tx;
        DROP TABLE IF EXISTS temp_tx_payment_map;
        RAISE;
END;
$$;

-- Комментарий к функции
COMMENT ON FUNCTION apply_transactions_batch IS 
'Батч-вставка транзакций с автоматическим созданием FIFO-лотов. Обеспечивает ACID-совместимость и правильную обработку FIFO. Все операции выполняются в одной транзакции БД.';
