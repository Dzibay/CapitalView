CREATE OR REPLACE FUNCTION update_portfolio_asset(pa_id bigint)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    first_tx_date date;
    total_quantity numeric := 0;
    avg_price numeric := 0;
BEGIN
    SELECT MIN(t.transaction_date)::date
    INTO first_tx_date
    FROM transactions AS t
    WHERE t.portfolio_asset_id = pa_id;

    PERFORM rebuild_fifo_for_portfolio_asset(pa_id);

    SELECT COALESCE(SUM(fl.remaining_qty), 0)
    INTO total_quantity
    FROM fifo_lots fl
    WHERE fl.portfolio_asset_id = pa_id;

    IF total_quantity > 0 THEN
        SELECT SUM(fl.remaining_qty * fl.price) / SUM(fl.remaining_qty)
        INTO avg_price
        FROM fifo_lots fl
        WHERE fl.portfolio_asset_id = pa_id
          AND fl.remaining_qty > 0;
    ELSE
        avg_price := 0;
    END IF;

    UPDATE portfolio_assets AS pa
    SET
        quantity = COALESCE(total_quantity, 0),
        average_price = COALESCE(avg_price, 0),
        created_at = COALESCE(first_tx_date, pa.created_at)
    WHERE pa.id = pa_id;
END;
$$;

COMMENT ON FUNCTION update_portfolio_asset(bigint) IS 'Пересчитывает quantity и average_price по открытым FIFO-лотам (fifo_lots); лоты синхронизируются с транзакциями через rebuild_fifo_for_portfolio_asset';
