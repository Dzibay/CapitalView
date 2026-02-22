-- Функция для создания операций по активу
-- Поддерживает все типы операций: Dividend, Coupon, Commission, Tax, Deposit, Withdraw, Other
-- Buy/Sell обрабатываются через apply_transaction

-- Удаляем старую версию функции (если есть) с параметрами p_record_date и p_payment_date
DROP FUNCTION IF EXISTS apply_operation;

CREATE OR REPLACE FUNCTION apply_operation(
    p_user_id uuid,
    p_portfolio_id bigint,
    p_operation_type int,  -- 3=Dividend, 4=Coupon, 5=Deposit, 6=Withdraw, 7=Commission, 8=Tax, 9=Other
    p_amount numeric,
    p_operation_date timestamp without time zone,
    p_currency_id bigint DEFAULT 47,  -- RUB по умолчанию (может быть любой валютой, включая криптовалюты)
    p_asset_id bigint DEFAULT NULL,
    p_dividend_yield numeric DEFAULT NULL
)
RETURNS bigint
LANGUAGE plpgsql
AS $$
DECLARE
    v_operation_id bigint;
    v_op_type_id bigint;
    v_portfolio_exists boolean;
    v_currency_rate numeric(20,6);
    v_amount_rub numeric(20,6);
    v_rub_currency_id bigint;
    v_currency_quote_asset_id bigint;
    v_currency_to_quote_rate numeric(20,6);
    v_quote_to_rub_rate numeric(20,6);
    v_amount_in_quote numeric(20,6);
BEGIN
    -- Проверяем существование портфеля
    SELECT EXISTS(SELECT 1 FROM portfolios WHERE id = p_portfolio_id AND user_id = p_user_id)
    INTO v_portfolio_exists;
    
    IF NOT v_portfolio_exists THEN
        RAISE EXCEPTION 'Портфель % не найден или не принадлежит пользователю', p_portfolio_id;
    END IF;
    
    -- Получаем ID типа операции из operations_type
    SELECT id INTO v_op_type_id
    FROM operations_type
    WHERE id = p_operation_type;
    
    IF v_op_type_id IS NULL THEN
        RAISE EXCEPTION 'Тип операции % не найден', p_operation_type;
    END IF;
    
    -- Получаем ID рубля и доллара (обычно это asset_id = 47 для RUB, но проверим)
    SELECT id INTO v_rub_currency_id
    FROM assets
    WHERE ticker = 'RUB' AND user_id IS NULL
    LIMIT 1;
    
    -- Если v_rub_currency_id не найден, используем 47 как fallback
    IF v_rub_currency_id IS NULL THEN
        v_rub_currency_id := 47;
    END IF;
    
    -- Если валюта операции - рубли, то amount_rub = amount
    IF p_currency_id = v_rub_currency_id OR p_currency_id = 47 THEN
        v_amount_rub := p_amount;
    ELSE
        -- Получаем quote_asset_id валюты операции (например, для BTC это будет USD)
        SELECT quote_asset_id INTO v_currency_quote_asset_id
        FROM assets
        WHERE id = p_currency_id;
        
        -- Если валюта имеет quote_asset_id (например, BTC -> USD), конвертируем через quote_asset
        -- Это двухшаговая конвертация: BTC -> USD -> RUB
        -- ИСПРАВЛЕНИЕ: Более явная проверка условия для двухшаговой конвертации
        IF v_currency_quote_asset_id IS NOT NULL 
           AND v_currency_quote_asset_id != v_rub_currency_id 
           AND v_currency_quote_asset_id != 47 
           AND v_currency_quote_asset_id > 0 THEN
            -- ШАГ 1: Конвертируем валюту операции в quote_asset (например, BTC -> USD)
            -- Ищем исторический курс на дату операции (p_operation_date)
            -- ВАЖНО: Используем CAST для приведения типов, так как trade_date может быть timestamp
            -- Для криптовалют (BTC, ETH и т.д.) курс к quote_asset хранится в asset_prices где asset_id = криптовалюта
            -- ИСПРАВЛЕНИЕ: Используем более надежный поиск курса с явным приведением типов
            SELECT price INTO v_currency_to_quote_rate
            FROM asset_prices
            WHERE asset_id = p_currency_id
              AND CAST(trade_date AS date) <= CAST(p_operation_date AS date)
            ORDER BY trade_date DESC
            LIMIT 1;
            
            -- Если исторический курс не найден, пробуем взять текущий курс
            IF v_currency_to_quote_rate IS NULL THEN
                SELECT curr_price INTO v_currency_to_quote_rate
                FROM asset_latest_prices_full
                WHERE asset_id = p_currency_id;
            END IF;
            
            -- Если курс все еще не найден, используем 1 (fallback)
            -- ВАЖНО: Если курс валюты операции к quote_asset не найден, это критическая ошибка!
            IF v_currency_to_quote_rate IS NULL OR v_currency_to_quote_rate <= 0 THEN
                v_currency_to_quote_rate := 1;
                RAISE WARNING 'Курс для актива % (валюта операции) к quote_asset % не найден для операции на дату %. Используется fallback = 1', p_currency_id, v_currency_quote_asset_id, p_operation_date;
            END IF;
            
            -- Конвертируем в quote_asset (например, 0.001 BTC * 107133 = 107.133 USD)
            v_amount_in_quote := p_amount * v_currency_to_quote_rate;
            
            -- ШАГ 2: Конвертируем quote_asset в рубли (например, USD -> RUB)
            -- Ищем исторический курс quote_asset->RUB на дату операции
            -- ВАЖНО: Используем CAST для приведения типов, так как trade_date может быть timestamp
            -- Для валют (USD, EUR и т.д.) курс к рублю хранится в asset_prices где asset_id = валюта
            -- ИСПРАВЛЕНИЕ: Используем более надежный поиск курса с явным приведением типов
            SELECT price INTO v_quote_to_rub_rate
            FROM asset_prices
            WHERE asset_id = v_currency_quote_asset_id
              AND CAST(trade_date AS date) <= CAST(p_operation_date AS date)
            ORDER BY trade_date DESC
            LIMIT 1;
            
            -- Если исторический курс не найден, пробуем взять текущий курс
            IF v_quote_to_rub_rate IS NULL THEN
                SELECT price INTO v_quote_to_rub_rate
                FROM asset_last_currency_prices
                WHERE asset_id = v_currency_quote_asset_id;
            END IF;
            
            -- Если курс все еще не найден, используем 1 (fallback)
            -- ВАЖНО: Если курс quote_asset->RUB не найден, это критическая ошибка!
            -- Убедитесь, что воркер currency_price_worker загружает курсы валют
            IF v_quote_to_rub_rate IS NULL OR v_quote_to_rub_rate <= 0 THEN
                v_quote_to_rub_rate := 1;
                RAISE WARNING 'Курс для актива % (quote_asset) к рублю не найден для операции на дату %. Используется fallback = 1', v_currency_quote_asset_id, p_operation_date;
            END IF;
            
            -- Рассчитываем итоговую сумму в рублях: amount * (currency -> quote) * (quote -> RUB)
            -- Пример: 0.001 BTC * 107133 (BTC->USD) * 100 (USD->RUB) = 10713.3 RUB
            v_amount_rub := v_amount_in_quote * v_quote_to_rub_rate;
        ELSE
            -- Если quote_asset_id отсутствует или равен RUB, конвертируем напрямую в рубли
            -- ВАЖНО: Используем CAST для приведения типов, так как trade_date может быть timestamp
            -- ИСПРАВЛЕНИЕ: Используем более надежный поиск курса с явным приведением типов
            SELECT price INTO v_currency_rate
            FROM asset_prices
            WHERE asset_id = p_currency_id
              AND CAST(trade_date AS date) <= CAST(p_operation_date AS date)
            ORDER BY trade_date DESC
            LIMIT 1;
            
            -- Если курс не найден, пробуем взять текущий курс из asset_latest_prices_full
            IF v_currency_rate IS NULL THEN
                SELECT curr_price INTO v_currency_rate
                FROM asset_latest_prices_full
                WHERE asset_id = p_currency_id;
            END IF;
            
            -- Если курс все еще не найден, используем 1 (предполагаем, что валюта = рубли)
            IF v_currency_rate IS NULL THEN
                v_currency_rate := 1;
            END IF;
            
            -- Рассчитываем сумму в рублях
            v_amount_rub := p_amount * v_currency_rate;
        END IF;
    END IF;
    
    -- Примечание: доходность рассчитывается на фронтенде и передается через p_dividend_yield
    -- Здесь не рассчитываем автоматически, так как это требует учета валют и курсов
    
    -- Создаем cash_operation
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
        p_user_id,
        p_portfolio_id,
        v_op_type_id,
        p_amount,
        p_currency_id,
        p_operation_date,
        p_asset_id,
        v_amount_rub
    )
    RETURNING id INTO v_operation_id;
    
    -- Примечание: запись в asset_payouts не создается
    -- Вся информация о выплатах хранится в cash_operations
    
    -- Обновляем историю портфеля с даты операции
    PERFORM update_portfolio_values_from_date(
        p_portfolio_id,
        p_operation_date::date - 1
    );
    
    RETURN v_operation_id;
END;
$$;

-- Комментарий к функции
COMMENT ON FUNCTION apply_operation IS 
'Создает операцию по активу. Поддерживает Dividend, Coupon, Commission, Tax, Deposit, Withdraw, Other. 
Для Buy/Sell используйте apply_transaction.
Поддерживает выплаты в любой валюте (включая криптовалюты: BTC, ETH и т.д.) через параметр p_currency_id.';
