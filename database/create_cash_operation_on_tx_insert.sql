-- ============================================================================
-- 1. Улучшенная функция триггера с проверкой на дубликаты
-- ============================================================================
CREATE OR REPLACE FUNCTION create_cash_operation_on_tx_insert()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    tx_type_name text;
    op_type_id bigint;
    cash_amount numeric;
    existing_op_id bigint;
BEGIN
    -- Получаем тип транзакции (1=BUY, 2=SELL)
    SELECT name INTO tx_type_name FROM transactions_type WHERE id = NEW.transaction_type;

    IF tx_type_name = 'Buy' THEN
        SELECT id INTO op_type_id FROM operations_type WHERE name = 'Buy';
        cash_amount := -(NEW.price * NEW.quantity);
    ELSIF tx_type_name = 'Sell' THEN
        SELECT id INTO op_type_id FROM operations_type WHERE name = 'Sell';
        cash_amount := (NEW.price * NEW.quantity);
    ELSE
        RETURN NEW;
    END IF;

    -- КРИТИЧНО: Проверяем, не существует ли уже денежная операция для этой транзакции
    -- Это предотвращает дубликаты при повторном срабатывании триггера
    SELECT id INTO existing_op_id
    FROM cash_operations
    WHERE transaction_id = NEW.id;

    -- Если операция уже существует, не создаем дубликат
    IF existing_op_id IS NOT NULL THEN
        RETURN NEW;
    END IF;

    -- Создаем денежную операцию только если её еще нет
    INSERT INTO cash_operations (user_id, portfolio_id, type, amount, currency, date, transaction_id)
    SELECT
        NEW.user_id,
        pa.portfolio_id,
        op_type_id,
        cash_amount,
        47, -- RUB
        NEW.transaction_date,
        NEW.id
    FROM portfolio_assets pa
    WHERE pa.id = NEW.portfolio_asset_id;

    RETURN NEW;
END;
$$;