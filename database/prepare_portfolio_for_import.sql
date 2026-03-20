-- ============================================================================
-- Подготовка портфеля к импорту от брокера (1 вызов вместо 7)
-- Находит или создаёт портфель, блокирует, загружает существующие данные
-- ============================================================================

CREATE OR REPLACE FUNCTION prepare_portfolio_for_import(
    p_user_id uuid,
    p_parent_portfolio_id bigint,
    p_portfolio_name text,
    p_broker_id int
) RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    v_portfolio_id bigint;
    v_just_created boolean := false;
    v_connection jsonb := 'null'::jsonb;
    v_pa_list jsonb;
    v_tx_keys jsonb;
    v_op_keys jsonb;
BEGIN
    -- 1. Найти существующий портфель
    SELECT id INTO v_portfolio_id
    FROM portfolios
    WHERE parent_portfolio_id = p_parent_portfolio_id
      AND name = p_portfolio_name
      AND user_id = p_user_id;

    -- 2. Создать, если не найден
    IF v_portfolio_id IS NULL THEN
        INSERT INTO portfolios (user_id, parent_portfolio_id, name, description)
        VALUES (p_user_id, p_parent_portfolio_id, p_portfolio_name, '{"source":"broker"}'::jsonb)
        ON CONFLICT DO NOTHING
        RETURNING id INTO v_portfolio_id;

        IF v_portfolio_id IS NOT NULL THEN
            v_just_created := true;
        ELSE
            SELECT id INTO v_portfolio_id
            FROM portfolios
            WHERE parent_portfolio_id = p_parent_portfolio_id
              AND name = p_portfolio_name
              AND user_id = p_user_id;
        END IF;
    END IF;

    IF v_portfolio_id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Не удалось найти или создать портфель');
    END IF;

    -- 3. Блокировка (NOWAIT — если занят, сразу ошибка)
    BEGIN
        PERFORM id FROM portfolios WHERE id = v_portfolio_id FOR UPDATE NOWAIT;
    EXCEPTION WHEN lock_not_available THEN
        RETURN jsonb_build_object('success', false, 'error', 'locked', 'portfolio_id', v_portfolio_id);
    END;

    -- 4. Broker connection
    SELECT to_jsonb(bc) INTO v_connection
    FROM (
        SELECT id, broker_id, api_key, last_sync_at
        FROM user_broker_connections
        WHERE portfolio_id = v_portfolio_id
          AND broker_id = p_broker_id
        LIMIT 1
    ) bc;

    -- 5. Существующие portfolio_assets
    SELECT COALESCE(jsonb_agg(jsonb_build_object('id', pa.id, 'asset_id', pa.asset_id)), '[]'::jsonb)
    INTO v_pa_list
    FROM portfolio_assets pa
    WHERE pa.portfolio_id = v_portfolio_id;

    -- 6. Ключи существующих транзакций (для дедупликации)
    -- Формат ключа: [portfolio_asset_id, date_str, transaction_type, price_rounded, quantity_rounded]
    SELECT COALESCE(jsonb_agg(jsonb_build_array(
        t.portfolio_asset_id,
        to_char(t.transaction_date, 'YYYY-MM-DD"T"HH24:MI:SS'),
        t.transaction_type,
        round(t.price::numeric, 6),
        round(t.quantity::numeric, 6)
    )), '[]'::jsonb)
    INTO v_tx_keys
    FROM transactions t
    JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
    WHERE pa.portfolio_id = v_portfolio_id;

    -- 7. Ключи существующих cash_operations
    -- Формат: [portfolio_id, type, date_str, amount_rounded, asset_id_or_null]
    SELECT COALESCE(jsonb_agg(jsonb_build_array(
        co.portfolio_id,
        co.type,
        to_char(co.date, 'YYYY-MM-DD"T"HH24:MI:SS'),
        round(co.amount::numeric, 2),
        co.asset_id
    )), '[]'::jsonb)
    INTO v_op_keys
    FROM cash_operations co
    WHERE co.portfolio_id = v_portfolio_id;

    RETURN jsonb_build_object(
        'success', true,
        'portfolio_id', v_portfolio_id,
        'just_created', v_just_created,
        'broker_connection', v_connection,
        'portfolio_assets', v_pa_list,
        'existing_tx_keys', v_tx_keys,
        'existing_op_keys', v_op_keys
    );
END;
$$;

COMMENT ON FUNCTION prepare_portfolio_for_import IS
  'Подготовка портфеля к импорту: find/create + lock + load existing data (1 RT вместо 7)';
