Drop function create_portfolio_asset;
CREATE OR REPLACE FUNCTION create_portfolio_asset(
    p_user_id uuid,
    p_portfolio_id bigint,
    p_asset_id bigint DEFAULT NULL,  -- NULL для кастомного актива
    p_asset_type_id bigint DEFAULT NULL,
    p_name text DEFAULT NULL,
    p_ticker text DEFAULT NULL,  -- Не используется для кастомных активов
    p_currency_id bigint DEFAULT NULL,  -- quote_asset_id
    p_quantity numeric DEFAULT 0,
    p_price numeric DEFAULT 0,
    p_transaction_date date DEFAULT CURRENT_DATE
)
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
    v_asset_id bigint;
    v_portfolio_asset_id bigint;
    v_existing_pa_id bigint;
    v_current_quantity numeric;
    v_current_avg_price numeric;
    v_new_quantity numeric;
    v_new_avg_price numeric;
    v_tx_id bigint;
    v_last_price numeric;
    v_asset_name text;
    v_asset_ticker text;
    v_result text;
BEGIN
    -- Начинаем транзакцию (автоматически в PostgreSQL)
    
    -- Валидация входных данных
    IF p_portfolio_id IS NULL THEN
        RETURN json_build_object(
            'success', false,
            'error', 'portfolio_id обязателен'
        )::text;
    END IF;
    
    -- Проверяем существование портфеля и принадлежность пользователю
    IF NOT EXISTS (
        SELECT 1 FROM portfolios 
        WHERE id = p_portfolio_id AND user_id = p_user_id
    ) THEN
        RETURN json_build_object(
            'success', false,
            'error', 'Портфель не найден или не принадлежит пользователю'
        )::text;
    END IF;
    
    -- Если актив кастомный (p_asset_id IS NULL) - всегда создаем новый уникальный актив
    IF p_asset_id IS NULL THEN
        -- Валидация для кастомного актива
        IF p_asset_type_id IS NULL OR p_name IS NULL OR p_currency_id IS NULL THEN
            RETURN json_build_object(
                'success', false,
                'error', 'Для кастомного актива обязательны: asset_type_id, name, currency_id'
            )::text;
        END IF;
        
        -- Проверяем, что тип актива кастомный
        IF NOT EXISTS (
            SELECT 1 FROM asset_types 
            WHERE id = p_asset_type_id AND is_custom = true
        ) THEN
            RETURN json_build_object(
                'success', false,
                'error', 'Указанный тип актива не является кастомным'
            )::text;
        END IF;
        
        -- Создаем новый кастомный актив (всегда новый, не ищем существующий)
        INSERT INTO assets (
            asset_type_id,
            user_id,
            name,
            ticker,  -- Может быть NULL для кастомных активов
            properties,
            quote_asset_id
        ) VALUES (
            p_asset_type_id,
            p_user_id,
            p_name,
            NULL,  -- Тикер не обязателен для кастомных активов
            '{}'::jsonb,
            p_currency_id
        ) RETURNING id INTO v_asset_id;
        
        -- Добавляем цену кастомного актива
        INSERT INTO asset_prices (
            asset_id,
            price,
            trade_date
        ) VALUES (
            v_asset_id,
            p_price,
            p_transaction_date
        );
        
        -- Обновляем последнюю цену актива
        PERFORM update_asset_latest_price(v_asset_id);
        
        v_asset_name := p_name;
        v_asset_ticker := NULL;
        
    ELSE
        -- Системный актив - используем существующий
        SELECT name, ticker INTO v_asset_name, v_asset_ticker
        FROM assets
        WHERE id = p_asset_id;
        
        IF v_asset_name IS NULL THEN
            RETURN json_build_object(
                'success', false,
                'error', format('Системный актив с ID %s не найден', p_asset_id)
            )::text;
        END IF;
        
        v_asset_id := p_asset_id;
        
        -- Проверяем, есть ли цена на эту дату, если нет - добавляем
        IF NOT EXISTS (
            SELECT 1 FROM asset_prices 
            WHERE asset_id = v_asset_id AND trade_date = p_transaction_date
        ) THEN
            INSERT INTO asset_prices (
                asset_id,
                price,
                trade_date
            ) VALUES (
                v_asset_id,
                p_price,
                p_transaction_date
            );
            
            -- Обновляем последнюю цену актива
            PERFORM update_asset_latest_price(v_asset_id);
        END IF;
    END IF;
    
    -- Проверяем, есть ли актив в портфеле
    SELECT id, quantity, average_price
    INTO v_existing_pa_id, v_current_quantity, v_current_avg_price
    FROM portfolio_assets
    WHERE portfolio_id = p_portfolio_id AND asset_id = v_asset_id;
    
    IF v_existing_pa_id IS NOT NULL THEN
        -- Актив уже есть в портфеле - обновляем количество и среднюю цену
        v_new_quantity := v_current_quantity + p_quantity;
        IF v_new_quantity > 0 THEN
            v_new_avg_price := ((v_current_avg_price * v_current_quantity) + (p_price * p_quantity)) / v_new_quantity;
        ELSE
            v_new_avg_price := 0;
        END IF;
        
        UPDATE portfolio_assets
        SET 
            quantity = v_new_quantity,
            average_price = v_new_avg_price
        WHERE id = v_existing_pa_id;
        
        v_portfolio_asset_id := v_existing_pa_id;
    ELSE
        -- Создаем новую запись в portfolio_assets
        INSERT INTO portfolio_assets (
            portfolio_id,
            asset_id,
            quantity,
            average_price
        ) VALUES (
            p_portfolio_id,
            v_asset_id,
            p_quantity,
            p_price
        ) RETURNING id INTO v_portfolio_asset_id;
        
        v_new_quantity := p_quantity;
        v_new_avg_price := p_price;
    END IF;
    
    -- Добавляем транзакцию покупки только если quantity > 0
    IF p_quantity > 0 THEN
        v_tx_id := apply_transaction(
            p_user_id := p_user_id,
            p_portfolio_asset_id := v_portfolio_asset_id,
            p_transaction_type := 1,  -- BUY
            p_quantity := p_quantity,
            p_price := p_price,
            p_transaction_date := p_transaction_date
        );
    END IF;
    
    -- Обновляем историю портфеля с даты транзакции
    BEGIN
        PERFORM update_portfolio_values_from_date(p_portfolio_id, p_transaction_date);
    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'Ошибка при обновлении истории портфеля: %', SQLERRM;
    END;
    
    -- Получаем последнюю цену актива
    SELECT price INTO v_last_price
    FROM asset_prices
    WHERE asset_id = v_asset_id
    ORDER BY trade_date DESC
    LIMIT 1;
    
    IF v_last_price IS NULL THEN
        v_last_price := p_price;
    END IF;
    
    -- Формируем результат
    v_result := json_build_object(
        'success', true,
        'message', 'Актив успешно добавлен в портфель',
        'asset', json_build_object(
            'asset_id', v_asset_id,
            'portfolio_asset_id', v_portfolio_asset_id,
            'name', v_asset_name,
            'ticker', v_asset_ticker,
            'quantity', v_new_quantity,
            'average_price', v_new_avg_price,
            'last_price', v_last_price,
            'total_value', round(v_new_quantity * v_last_price, 2),
            'profit', 0,
            'profit_rub', 0,
            'currency_rate_to_rub', 1,
            'currency_ticker', 'RUB',
            'leverage', 1,
            'type', 'Неизвестно'
        )
    )::text;
    
    RETURN v_result;
    
EXCEPTION WHEN OTHERS THEN
    -- В случае ошибки транзакция автоматически откатывается
    RETURN json_build_object(
        'success', false,
        'error', format('Ошибка при создании актива: %s', SQLERRM)
    )::text;
END;
$$;
