-- ============================================================================
-- Ручные правки брокерских операций переживают синхронизацию
-- ============================================================================
-- Пользователь удалил или изменил операцию, пришедшую от брокера (у неё есть external_id), —
-- запоминаем её в broker_operation_suppressions, и следующая синхронизация её не вернёт.
-- Изменение = удаление + создание заново (update_operations_batch), новая строка уже 'manual'.
--
-- Хватает триггера на cash_operations: у каждой сделки (transactions) есть своя денежная
-- операция с тем же external_id, и она удаляется вместе со сделкой (ON DELETE CASCADE).
--
-- Удаления самой синхронизации (clear_broker_portfolio_data) и явная очистка портфеля
-- (clear_portfolio_full) ставят capitalview.broker_sync = 'on' на время транзакции —
-- такие удаления не запоминаются.
-- ============================================================================

CREATE OR REPLACE FUNCTION remember_deleted_broker_operation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.external_id IS NULL
       OR COALESCE(current_setting('capitalview.broker_sync', true), '') = 'on' THEN
        RETURN NULL;
    END IF;

    -- Портфель удаляется целиком (каскад) — запоминать некуда и незачем
    INSERT INTO broker_operation_suppressions (portfolio_id, external_id)
    SELECT OLD.portfolio_id, OLD.external_id
    WHERE EXISTS (SELECT 1 FROM portfolios WHERE id = OLD.portfolio_id)
    ON CONFLICT DO NOTHING;

    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS cash_operations_remember_broker_delete ON cash_operations;
CREATE TRIGGER cash_operations_remember_broker_delete
AFTER DELETE ON cash_operations
FOR EACH ROW
WHEN (OLD.external_id IS NOT NULL)
EXECUTE FUNCTION remember_deleted_broker_operation();

COMMENT ON FUNCTION remember_deleted_broker_operation() IS
  'Запоминает удалённые/изменённые пользователем брокерские операции, чтобы синхронизация их не вернула';
