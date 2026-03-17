-- ============================================================================
-- ФУНКЦИИ ПРОВЕРКИ ДОСТУПА (batch)
-- Заменяют N+1 запросы в backend на один вызов
-- ============================================================================

CREATE OR REPLACE FUNCTION check_transactions_access(
    p_transaction_ids bigint[],
    p_user_id text  -- передаётся строка из backend, приводим к uuid внутри
) RETURNS boolean
LANGUAGE plpgsql STABLE
AS $$
DECLARE
    v_user_id uuid := p_user_id::uuid;
BEGIN
    IF p_transaction_ids IS NULL OR array_length(p_transaction_ids, 1) IS NULL THEN
        RETURN true;
    END IF;

    IF (SELECT COUNT(*) FROM transactions WHERE id = ANY(p_transaction_ids)) 
       != array_length(p_transaction_ids, 1) THEN
        RETURN false;
    END IF;

    RETURN NOT EXISTS (
        SELECT 1
        FROM transactions t
        JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
        JOIN portfolios p ON p.id = pa.portfolio_id
        WHERE t.id = ANY(p_transaction_ids)
          AND p.user_id != v_user_id
    );
END;
$$;


CREATE OR REPLACE FUNCTION check_operations_access(
    p_operation_ids bigint[],
    p_user_id text  -- передаётся строка из backend, приводим к uuid внутри
) RETURNS boolean
LANGUAGE plpgsql STABLE
AS $$
DECLARE
    v_user_id uuid := p_user_id::uuid;
BEGIN
    IF p_operation_ids IS NULL OR array_length(p_operation_ids, 1) IS NULL THEN
        RETURN true;
    END IF;

    IF (SELECT COUNT(*) FROM cash_operations WHERE id = ANY(p_operation_ids))
       != array_length(p_operation_ids, 1) THEN
        RETURN false;
    END IF;

    RETURN NOT EXISTS (
        SELECT 1
        FROM cash_operations co
        JOIN portfolios p ON p.id = co.portfolio_id
        WHERE co.id = ANY(p_operation_ids)
          AND p.user_id != v_user_id
    );
END;
$$;


CREATE OR REPLACE FUNCTION check_resource_access(
    p_resource_type text,
    p_resource_id bigint,
    p_user_id text  -- передаётся строка из backend, приводим к uuid внутри
) RETURNS boolean
LANGUAGE plpgsql STABLE
AS $$
DECLARE
    v_user_id uuid := p_user_id::uuid;
BEGIN
    RETURN CASE p_resource_type
        WHEN 'portfolio' THEN
            EXISTS(SELECT 1 FROM portfolios WHERE id = p_resource_id AND user_id = v_user_id)
        WHEN 'portfolio_asset' THEN
            EXISTS(
                SELECT 1 FROM portfolio_assets pa
                JOIN portfolios p ON p.id = pa.portfolio_id
                WHERE pa.id = p_resource_id AND p.user_id = v_user_id
            )
        WHEN 'transaction' THEN
            EXISTS(
                SELECT 1 FROM transactions t
                JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
                JOIN portfolios p ON p.id = pa.portfolio_id
                WHERE t.id = p_resource_id AND p.user_id = v_user_id
            )
        WHEN 'operation' THEN
            EXISTS(
                SELECT 1 FROM cash_operations co
                JOIN portfolios p ON p.id = co.portfolio_id
                WHERE co.id = p_resource_id AND p.user_id = v_user_id
            )
        ELSE false
    END;
END;
$$;
