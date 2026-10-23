-- ============================================================================
-- Очистка брокерского портфеля перед синхронизацией (ручные записи остаются)
-- ============================================================================
-- Удаляет только то, что пришло от брокера (source <> 'manual'; NULL — записи до разметки),
-- в портфеле и его дочерних портфелях. Ручные сделки и операции, дочерние портфели
-- (счета брокера) и их настройки остаются. Удаления не попадают в
-- broker_operation_suppressions — это сама синхронизация, а не правка пользователя.
--
-- Возвращает оставшиеся ручные записи по портфелям, чтобы импорт не задвоил операцию,
-- которую пользователь уже добавил руками:
--   {"kept_manual": {"<portfolio_id>": [{"kind": "tx"|"cash", ...}]}, "kept_manual_count": N, ...}
-- ============================================================================

DROP FUNCTION IF EXISTS clear_broker_portfolio_data(bigint);
CREATE OR REPLACE FUNCTION clear_broker_portfolio_data(p_portfolio_id bigint)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    v_prev_sync_flag text := current_setting('capitalview.broker_sync', true);
    v_portfolio_ids bigint[];
    v_asset_ids bigint[];
    v_touched_pa_ids bigint[];
    v_custom_asset_ids bigint[];
    v_min_date date;
    v_pa_id bigint;
    v_pid bigint;
    v_deleted_tx int := 0;
    v_deleted_ops int := 0;
    v_kept jsonb;
    v_kept_count int;
BEGIN
    PERFORM set_config('capitalview.broker_sync', 'on', true);

    WITH RECURSIVE tree AS (
        SELECT id FROM portfolios WHERE id = p_portfolio_id
        UNION ALL
        SELECT p.id FROM portfolios p JOIN tree t ON p.parent_portfolio_id = t.id
    )
    SELECT array_agg(id) INTO v_portfolio_ids FROM tree;

    IF v_portfolio_ids IS NULL THEN
        RAISE EXCEPTION 'Portfolio not found or access denied';
    END IF;

    SELECT array_agg(DISTINCT asset_id) INTO v_asset_ids
    FROM portfolio_assets
    WHERE portfolio_id = ANY(v_portfolio_ids);

    -- С какой даты пересчитывать то, что останется
    SELECT LEAST(
        (SELECT MIN(co.date)::date
         FROM cash_operations co
         WHERE co.portfolio_id = ANY(v_portfolio_ids)
           AND co.source IS DISTINCT FROM 'manual'),
        (SELECT MIN(t.transaction_date)::date
         FROM transactions t
         JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
         WHERE pa.portfolio_id = ANY(v_portfolio_ids)
           AND t.source IS DISTINCT FROM 'manual')
    ) INTO v_min_date;

    -- Позиции, у которых пропадут брокерские записи (пересчитаем, если в них останутся ручные)
    SELECT array_agg(pa.id) INTO v_touched_pa_ids
    FROM portfolio_assets pa
    WHERE pa.portfolio_id = ANY(v_portfolio_ids)
      AND (
          EXISTS (SELECT 1 FROM transactions t
                  WHERE t.portfolio_asset_id = pa.id AND t.source IS DISTINCT FROM 'manual')
          OR EXISTS (SELECT 1 FROM cash_operations co
                     WHERE co.portfolio_id = pa.portfolio_id AND co.asset_id = pa.asset_id
                       AND co.source IS DISTINCT FROM 'manual')
      );

    -- Сделки брокера; их денежные операции уходят каскадом по transaction_id
    DELETE FROM transactions t
    USING portfolio_assets pa
    WHERE pa.id = t.portfolio_asset_id
      AND pa.portfolio_id = ANY(v_portfolio_ids)
      AND t.source IS DISTINCT FROM 'manual';
    GET DIAGNOSTICS v_deleted_tx = ROW_COUNT;

    -- Остальные операции брокера (дивиденды, купоны, комиссии, пополнения...)
    DELETE FROM cash_operations
    WHERE portfolio_id = ANY(v_portfolio_ids)
      AND transaction_id IS NULL
      AND source IS DISTINCT FROM 'manual';
    GET DIAGNOSTICS v_deleted_ops = ROW_COUNT;

    -- Позиции без единой записи (каскад: fifo_lots, portfolio_asset_daily_values, missed_payouts)
    DELETE FROM portfolio_assets pa
    WHERE pa.portfolio_id = ANY(v_portfolio_ids)
      AND NOT EXISTS (SELECT 1 FROM transactions t WHERE t.portfolio_asset_id = pa.id)
      AND NOT EXISTS (SELECT 1 FROM cash_operations co
                      WHERE co.portfolio_id = pa.portfolio_id AND co.asset_id = pa.asset_id);

    -- Пересчёт позиций, где остались ручные записи
    IF v_min_date IS NOT NULL AND v_touched_pa_ids IS NOT NULL THEN
        FOR v_pa_id IN
            SELECT id FROM portfolio_assets WHERE id = ANY(v_touched_pa_ids)
        LOOP
            BEGIN
                PERFORM update_portfolio_asset(v_pa_id);
                PERFORM update_portfolio_asset_positions_from_date(v_pa_id, v_min_date - 1);
            EXCEPTION WHEN OTHERS THEN
                RAISE WARNING 'Ошибка при пересчёте позиции % после очистки: %', v_pa_id, SQLERRM;
            END;
        END LOOP;
    END IF;

    -- Кастомные активы, которые больше нигде не используются
    SELECT array_agg(a.id) INTO v_custom_asset_ids
    FROM assets a
    JOIN asset_types at ON at.id = a.asset_type_id
    WHERE at.is_custom = true
      AND a.id = ANY(v_asset_ids)
      AND NOT EXISTS (SELECT 1 FROM portfolio_assets pa WHERE pa.asset_id = a.id)
      AND NOT EXISTS (SELECT 1 FROM cash_operations co WHERE co.asset_id = a.id);

    IF v_custom_asset_ids IS NOT NULL THEN
        DELETE FROM asset_latest_prices WHERE asset_id = ANY(v_custom_asset_ids);
        DELETE FROM asset_prices WHERE asset_id = ANY(v_custom_asset_ids);
        DELETE FROM assets WHERE id = ANY(v_custom_asset_ids);
    END IF;

    -- История стоимости: пустые портфели — с нуля, с ручными записями — пересчёт
    FOREACH v_pid IN ARRAY v_portfolio_ids
    LOOP
        IF EXISTS (SELECT 1 FROM portfolio_assets WHERE portfolio_id = v_pid)
           OR EXISTS (SELECT 1 FROM cash_operations WHERE portfolio_id = v_pid) THEN
            IF v_min_date IS NOT NULL THEN
                BEGIN
                    PERFORM update_portfolio_values_from_date(v_pid, v_min_date - 1);
                EXCEPTION WHEN OTHERS THEN
                    RAISE WARNING 'Ошибка при пересчёте истории портфеля % после очистки: %', v_pid, SQLERRM;
                END;
            END IF;
        ELSE
            DELETE FROM portfolio_daily_values WHERE portfolio_id = v_pid;
        END IF;
    END LOOP;

    -- Завершённые задачи импорта (активные не трогаем)
    DELETE FROM import_tasks
    WHERE portfolio_id = ANY(v_portfolio_ids)
      AND status NOT IN ('pending', 'processing');

    -- Что осталось от пользователя: по этим записям импорт не создаст дубль
    SELECT COALESCE(jsonb_object_agg(g.pid::text, g.rows), '{}'::jsonb),
           COALESCE(SUM(g.cnt), 0)::int
    INTO v_kept, v_kept_count
    FROM (
        SELECT x.pid, jsonb_agg(x.r) AS rows, count(*) AS cnt
        FROM (
            SELECT pa.portfolio_id AS pid,
                   jsonb_build_object(
                       'kind', 'tx',
                       'type', t.transaction_type,
                       'date', t.transaction_date,
                       'asset_id', pa.asset_id,
                       'quantity', t.quantity,
                       'price', t.price
                   ) AS r
            FROM transactions t
            JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
            WHERE pa.portfolio_id = ANY(v_portfolio_ids)
            UNION ALL
            SELECT co.portfolio_id,
                   jsonb_build_object(
                       'kind', 'cash',
                       'type', co.type,
                       'date', co.date,
                       'asset_id', co.asset_id,
                       'amount', co.amount
                   )
            FROM cash_operations co
            WHERE co.portfolio_id = ANY(v_portfolio_ids)
              AND co.transaction_id IS NULL
        ) x
        GROUP BY x.pid
    ) g;

    PERFORM set_config('capitalview.broker_sync', COALESCE(v_prev_sync_flag, ''), true);

    RETURN jsonb_build_object(
        'kept_manual', v_kept,
        'kept_manual_count', v_kept_count,
        'deleted_transactions', v_deleted_tx,
        'deleted_operations', v_deleted_ops
    );
END;
$$;

COMMENT ON FUNCTION clear_broker_portfolio_data(bigint) IS
  'Перед синхронизацией удаляет только брокерские записи портфеля и дочерних счетов; ручные остаются и возвращаются списком для дедупликации';
