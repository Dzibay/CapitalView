DECLARE
    total_quantity numeric := 0;
    total_cost numeric := 0;
    first_tx_date date;
    avg_price numeric := 0;
    r RECORD;
BEGIN
    SELECT MIN(t.transaction_date)::date
    INTO first_tx_date
    FROM transactions AS t
    WHERE t.portfolio_asset_id = pa_id;

    FOR r IN
        SELECT t.transaction_type, t.quantity::numeric AS q, t.price::numeric AS p
        FROM transactions AS t
        WHERE t.portfolio_asset_id = pa_id
        ORDER BY t.transaction_date, t.id
    LOOP
        IF r.transaction_type = 1 THEN
            -- 🟢 Покупка
            total_cost := total_cost + r.q * r.p;
            total_quantity := total_quantity + r.q;

        ELSIF r.transaction_type IN (2, 3) THEN
            -- 🔴 Продажа или Погашение — уменьшаем количество и стоимость
            IF total_quantity > 0 THEN
                avg_price := total_cost / total_quantity;

                total_quantity := total_quantity - r.q;
                IF total_quantity < 0 THEN
                    -- защита от перехода в шорт
                    total_quantity := 0;
                    total_cost := 0;
                ELSE
                    total_cost := total_cost - avg_price * r.q;
                END IF;
            END IF;
        END IF;
    END LOOP;

    UPDATE portfolio_assets AS pa
    SET
        quantity = COALESCE(total_quantity, 0),
        average_price = CASE
            WHEN total_quantity = 0 THEN 0
            ELSE total_cost / total_quantity
        END,
        created_at = COALESCE(first_tx_date, pa.created_at)
    WHERE pa.id = pa_id;
END;