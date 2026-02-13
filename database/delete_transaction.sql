-- ============================================================================
-- Функция безопасного удаления транзакции с пересчетом FIFO
-- ============================================================================
-- При удалении транзакции:
-- 1. Если это была покупка (BUY) - удаляет соответствующий FIFO лот
-- 2. Если это была продажа (SELL) - пересчитывает FIFO для всех 
--    последующих транзакций этого portfolio_asset начиная с даты удаленной транзакции
-- 3. Обновляет portfolio_asset и историю портфеля
-- ============================================================================

CREATE OR REPLACE FUNCTION delete_transaction(p_transaction_id bigint)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
    v_tx_record record;
    v_portfolio_asset_id bigint;
    v_portfolio_id bigint;
    v_transaction_date date;
    v_transaction_type int;
    v_quantity numeric;
    v_price numeric;
    v_user_id uuid;
    v_fifo_lot_id bigint;
    v_min_tx_date date;
BEGIN
    -- 1. Получаем информацию о транзакции
    SELECT 
        t.id,
        t.portfolio_asset_id,
        t.transaction_type,
        t.quantity,
        t.price,
        t.transaction_date::date,
        t.user_id,
        pa.portfolio_id
    INTO v_tx_record
    FROM transactions t
    JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
    WHERE t.id = p_transaction_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Транзакция % не найдена', p_transaction_id;
    END IF;
    
    v_portfolio_asset_id := v_tx_record.portfolio_asset_id;
    v_portfolio_id := v_tx_record.portfolio_id;
    v_transaction_date := v_tx_record.transaction_date;
    v_transaction_type := v_tx_record.transaction_type;
    v_quantity := v_tx_record.quantity;
    v_price := v_tx_record.price;
    v_user_id := v_tx_record.user_id;
    
    -- 2. Обрабатываем FIFO в зависимости от типа транзакции
    IF v_transaction_type = 1 THEN
        -- BUY: удаляем соответствующий FIFO лот
        -- Ищем лот, созданный этой транзакцией (по дате, количеству и цене)
        -- ВАЖНО: может быть несколько лотов с одинаковыми параметрами,
        -- поэтому берем первый подходящий лот, созданный в эту дату
        SELECT id INTO v_fifo_lot_id
        FROM fifo_lots
        WHERE portfolio_asset_id = v_portfolio_asset_id
            AND created_at::date = v_transaction_date
            AND price = v_price
            AND remaining_qty = v_quantity  -- Лот должен быть полностью неиспользованным
        ORDER BY id
        LIMIT 1;
        
        -- Если не нашли полностью неиспользованный лот, ищем любой лот с этой датой
        -- (возможно, лот был частично использован при продаже, но это не должно происходить
        --  если транзакции обрабатываются последовательно)
        IF v_fifo_lot_id IS NULL THEN
            SELECT id INTO v_fifo_lot_id
            FROM fifo_lots
            WHERE portfolio_asset_id = v_portfolio_asset_id
                AND created_at::date = v_transaction_date
                AND price = v_price
            ORDER BY id
            LIMIT 1;
        END IF;
        
        -- Удаляем найденный лот
        IF v_fifo_lot_id IS NOT NULL THEN
            DELETE FROM fifo_lots WHERE id = v_fifo_lot_id;
        ELSE
            -- Если лот не найден, возможно он уже был удален или использован
            -- Это не критично, продолжаем удаление транзакции
            RAISE WARNING 'FIFO лот для транзакции % не найден', p_transaction_id;
        END IF;
        
    ELSIF v_transaction_type = 2 THEN
        -- SELL: пересчитываем FIFO для всех последующих транзакций
        -- Получаем минимальную дату транзакции для этого portfolio_asset
        SELECT MIN(transaction_date::date) INTO v_min_tx_date
        FROM transactions
        WHERE portfolio_asset_id = v_portfolio_asset_id
            AND id != p_transaction_id;
        
        -- Удаляем все FIFO лоты для этого portfolio_asset
        -- (они будут пересчитаны заново)
        DELETE FROM fifo_lots WHERE portfolio_asset_id = v_portfolio_asset_id;
        
        -- Пересчитываем FIFO для всех транзакций этого portfolio_asset
        -- начиная с минимальной даты (или с даты удаленной транзакции, если она была первой)
        IF v_min_tx_date IS NOT NULL THEN
            -- Пересчитываем все транзакции в хронологическом порядке
            -- Создаем FIFO лоты для покупок и обрабатываем продажи
            FOR v_tx_record IN
                SELECT 
                    t.id,
                    t.transaction_type,
                    t.quantity,
                    t.price,
                    t.transaction_date::date,
                    t.portfolio_asset_id
                FROM transactions t
                WHERE t.portfolio_asset_id = v_portfolio_asset_id
                    AND t.id != p_transaction_id
                ORDER BY t.transaction_date, t.id
            LOOP
                IF v_tx_record.transaction_type = 1 THEN
                    -- BUY: создаем FIFO лот
                    INSERT INTO fifo_lots (
                        portfolio_asset_id,
                        remaining_qty,
                        price,
                        created_at
                    )
                    VALUES (
                        v_tx_record.portfolio_asset_id,
                        v_tx_record.quantity,
                        v_tx_record.price,
                        v_tx_record.transaction_date
                    );
                ELSIF v_tx_record.transaction_type = 2 THEN
                    -- SELL: обрабатываем через FIFO
                    DECLARE
                        v_remaining numeric := v_tx_record.quantity;
                        v_realized numeric := 0;
                        lot_record record;
                    BEGIN
                        FOR lot_record IN
                            SELECT *
                            FROM fifo_lots
                            WHERE portfolio_asset_id = v_tx_record.portfolio_asset_id
                                AND remaining_qty > 0
                            ORDER BY created_at, id
                            FOR UPDATE
                        LOOP
                            EXIT WHEN v_remaining <= 0;
                            
                            IF lot_record.remaining_qty <= v_remaining THEN
                                v_realized := v_realized +
                                    lot_record.remaining_qty * (v_tx_record.price - lot_record.price);
                                
                                v_remaining := v_remaining - lot_record.remaining_qty;
                                
                                UPDATE fifo_lots
                                SET remaining_qty = 0
                                WHERE id = lot_record.id;
                            ELSE
                                v_realized := v_realized +
                                    v_remaining * (v_tx_record.price - lot_record.price);
                                
                                UPDATE fifo_lots
                                SET remaining_qty = lot_record.remaining_qty - v_remaining
                                WHERE id = lot_record.id;
                                
                                v_remaining := 0;
                            END IF;
                        END LOOP;
                        
                        IF v_remaining > 0 THEN
                            RAISE EXCEPTION 
                                'Not enough quantity to sell after deleting transaction % (portfolio_asset_id=%)',
                                p_transaction_id, v_portfolio_asset_id;
                        END IF;
                        
                        -- Обновляем realized_pnl для транзакции
                        UPDATE transactions
                        SET realized_pnl = v_realized
                        WHERE id = v_tx_record.id;
                    END;
                END IF;
            END LOOP;
        END IF;
    END IF;
    
    -- 3. Удаляем транзакцию (триггер delete_cash_operation_on_tx_delete удалит связанную cash_operation)
    DELETE FROM transactions WHERE id = p_transaction_id;
    
    -- 4. Обновляем portfolio_asset
    -- Функция update_portfolio_asset принимает один параметр pa_id
    PERFORM update_portfolio_asset(v_portfolio_asset_id);
    
    -- 5. Обновляем историю портфеля с даты удаленной транзакции
    PERFORM update_portfolio_asset_positions_from_date(
        v_portfolio_asset_id,
        v_transaction_date
    );
    
    PERFORM update_portfolio_values_from_date(
        v_portfolio_id,
        v_transaction_date
    );
    
    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        -- В случае ошибки откатываем транзакцию
        RAISE;
END;
$$;

-- Комментарий к функции
COMMENT ON FUNCTION delete_transaction(bigint) IS 
'Безопасно удаляет транзакцию с пересчетом FIFO. Для покупок удаляет соответствующий FIFO лот, для продаж пересчитывает FIFO для всех последующих транзакций.';
