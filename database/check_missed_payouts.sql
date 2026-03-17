-- Функция для проверки и добавления неполученных выплат
-- Вызывается после создания транзакции или актива в портфеле
-- Оптимизирована: принимает только portfolio_asset_id и получает остальные данные внутри
CREATE OR REPLACE FUNCTION check_missed_payouts(
    p_portfolio_asset_id bigint
)
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
    v_payout asset_payouts%ROWTYPE;
    v_check_date date;
    v_quantity_on_date numeric;
    v_quantity_on_payment_date numeric;
    v_expected_amount numeric;
    v_received_amount numeric;
    v_missed_count integer := 0;
    v_operation_type_id bigint;
    v_payout_type text;
    v_user_id uuid;
    v_portfolio_id bigint;
    v_asset_id bigint;
BEGIN
    -- Получаем необходимую информацию из portfolio_assets и portfolios
    SELECT 
        p.user_id,
        pa.portfolio_id,
        pa.asset_id
    INTO 
        v_user_id,
        v_portfolio_id,
        v_asset_id
    FROM portfolio_assets pa
    JOIN portfolios p ON p.id = pa.portfolio_id
    WHERE pa.id = p_portfolio_asset_id;
    
    -- Проверяем, что актив найден
    IF v_user_id IS NULL OR v_portfolio_id IS NULL OR v_asset_id IS NULL THEN
        RAISE EXCEPTION 'Портфельный актив с ID % не найден', p_portfolio_asset_id;
    END IF;
    
    -- Сначала удаляем все существующие записи о неполученных выплатах для данного актива в портфеле
    -- Это необходимо, так как при изменении транзакций/операций список неполученных выплат может измениться
    DELETE FROM missed_payouts
    WHERE portfolio_asset_id = p_portfolio_asset_id;
    
    -- Получаем ID типов операций для дивидендов и купонов
    SELECT id INTO v_operation_type_id FROM operations_type WHERE name = 'Dividend' LIMIT 1;
    IF v_operation_type_id IS NULL THEN
        RAISE EXCEPTION 'Operation type "Dividend" not found';
    END IF;
    
    -- Проходим по всем выплатам для данного актива
    FOR v_payout IN 
        SELECT * FROM asset_payouts 
        WHERE asset_id = v_asset_id
        ORDER BY payment_date DESC
    LOOP
        -- Определяем дату проверки в зависимости от типа выплаты
        -- Для купонов используем record_date, для дивидендов - last_buy_date
        v_payout_type := LOWER(TRIM(COALESCE(v_payout.type, '')));
        
        IF v_payout_type = 'coupon' THEN
            v_check_date := v_payout.record_date;
        ELSIF v_payout_type = 'dividend' THEN
            v_check_date := v_payout.last_buy_date;
        ELSE
            -- Для других типов используем record_date, если есть, иначе last_buy_date
            v_check_date := COALESCE(v_payout.record_date, v_payout.last_buy_date);
        END IF;
        
        -- Пропускаем выплаты без даты проверки
        IF v_check_date IS NULL THEN
            CONTINUE;
        END IF;
        
        -- Если выплата еще не наступила (payment_date в будущем), пропускаем
        IF v_payout.payment_date IS NULL OR v_payout.payment_date > CURRENT_DATE THEN
            CONTINUE;
        END IF;
        
        -- Проверяем, был ли актив в портфеле на дату проверки (record_date/last_buy_date)
        -- Ищем ближайшую дату до или равную дате проверки
        SELECT quantity INTO v_quantity_on_date
        FROM portfolio_daily_positions
        WHERE portfolio_asset_id = p_portfolio_asset_id
          AND report_date <= v_check_date
        ORDER BY report_date DESC
        LIMIT 1;
        
        -- Если актива не было в портфеле на дату проверки или количество было 0, пропускаем
        IF v_quantity_on_date IS NULL OR v_quantity_on_date <= 0 THEN
            CONTINUE;
        END IF;
        
        -- Дополнительно проверяем количество на дату выплаты (payment_date)
        -- Если на дату выплаты актива не было или количество было 0, не учитываем выплату
        SELECT quantity INTO v_quantity_on_payment_date
        FROM portfolio_daily_positions
        WHERE portfolio_asset_id = p_portfolio_asset_id
          AND report_date <= v_payout.payment_date
        ORDER BY report_date DESC
        LIMIT 1;
        
        -- Если на дату выплаты актива не было или количество было 0, пропускаем
        IF v_quantity_on_payment_date IS NULL OR v_quantity_on_payment_date <= 0 THEN
            CONTINUE;
        END IF;
        
        -- Рассчитываем ожидаемую сумму выплаты на основе количества на дату проверки
        v_expected_amount := v_payout.value * v_quantity_on_date;
        
        -- Определяем тип операции для проверки в cash_operations
        IF v_payout_type = 'coupon' THEN
            SELECT id INTO v_operation_type_id FROM operations_type WHERE name = 'Coupon' LIMIT 1;
        ELSIF v_payout_type = 'dividend' THEN
            SELECT id INTO v_operation_type_id FROM operations_type WHERE name = 'Dividend' LIMIT 1;
        ELSE
            -- Для других типов используем Dividend по умолчанию
            SELECT id INTO v_operation_type_id FROM operations_type WHERE name = 'Dividend' LIMIT 1;
        END IF;
        
        -- Проверяем, получал ли пользователь эту выплату
        -- Для всех типов выплат (купонов и дивидендов) допускаем погрешность ±7 дней
        -- Дата операции может отклоняться от даты выплаты на неделю
        SELECT COALESCE(SUM(COALESCE(amount_rub, amount)), 0) INTO v_received_amount
        FROM cash_operations
        WHERE user_id = v_user_id
          AND portfolio_id = v_portfolio_id
          AND asset_id = v_asset_id
          AND type = v_operation_type_id
          AND date::date BETWEEN v_payout.payment_date - INTERVAL '14 days' AND v_payout.payment_date + INTERVAL '14 days'
          AND ABS(COALESCE(amount_rub, amount) - v_expected_amount) < 0.01; -- Допускаем небольшую погрешность в сумме
        
        -- Если выплата не была получена (или получена не полностью)
        IF v_received_amount < v_expected_amount - 0.01 THEN
            -- Добавляем в таблицу неполученных выплат
            -- Записи для этого актива уже удалены в начале функции, поэтому дубликатов не будет
            INSERT INTO missed_payouts (
                user_id,
                portfolio_id,
                portfolio_asset_id,
                asset_id,
                payout_id
            ) VALUES (
                v_user_id,
                v_portfolio_id,
                p_portfolio_asset_id,
                v_asset_id,
                v_payout.id
            );
            
            v_missed_count := v_missed_count + 1;
        END IF;
    END LOOP;
    
    RETURN v_missed_count;
END;
$$;
