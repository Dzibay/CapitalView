DECLARE
    result jsonb;

    -- Инвестировано / текущая стоимость / нереализованная прибыль
    v_total_invested numeric := 0;
    v_total_value numeric := 0;
    v_unrealized_pl numeric := 0;

    -- FIFO реализованная прибыль
    v_realized_pl numeric := 0;

    -- Кэш-потоки
    v_dividends numeric := 0;
    v_coupons numeric := 0;
    v_commissions numeric := 0;
    v_taxes numeric := 0;
    v_inflow numeric := 0;
    v_outflow numeric := 0;

    -- Финальные показатели
    v_total_profit numeric := 0;
    v_return_percent numeric := 0;

    -- FIFO очереди
    buy_qty    numeric[];
    buy_price  numeric[];
    remaining numeric;
    i int;

    r RECORD;
    r_asset RECORD;
BEGIN
    -------------------------------------------------------------------
    -- 1️⃣ КЭШ-ОПЕРАЦИИ
    -------------------------------------------------------------------
    SELECT
        -- Для Deposit используем amount, для остальных операций используем amount_rub (уже в рублях)
        COALESCE(SUM(CASE WHEN ot.name='Deposit'  THEN co.amount ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN ot.name='Withdraw' THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END), 0),
        -- Для выплат (Dividend, Coupon) используем amount_rub (уже переведено в рубли по курсу на дату операции)
        COALESCE(SUM(CASE WHEN ot.name='Dividend' THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN ot.name='Coupon'   THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN ot.name='Commision' THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN ot.name='Tax'      THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END), 0)
    INTO v_inflow, v_outflow, v_dividends, v_coupons, v_commissions, v_taxes
    FROM cash_operations co
    JOIN operations_type ot ON ot.id = co.type
    WHERE co.portfolio_id = p_portfolio_id;


    -------------------------------------------------------------------
    -- 2️⃣ UNREALIZED P/L (по текущим позициям)
    -------------------------------------------------------------------
    SELECT
        COALESCE(SUM(pa.quantity * pa.average_price * COALESCE(curr.curr_price,1) / pa.leverage), 0),
        COALESCE(SUM(pa.quantity * ap.curr_price    * COALESCE(curr.curr_price,1) / pa.leverage), 0),
        COALESCE(SUM(pa.quantity * (ap.curr_price - pa.average_price) * COALESCE(curr.curr_price,1) / pa.leverage), 0)
    INTO v_total_invested, v_total_value, v_unrealized_pl
    FROM portfolio_assets pa
    JOIN assets a ON a.id = pa.asset_id
    LEFT JOIN asset_latest_prices_full ap   ON ap.asset_id   = pa.asset_id
    LEFT JOIN asset_latest_prices_full curr ON curr.asset_id = a.quote_asset_id
    WHERE pa.portfolio_id = p_portfolio_id;


    -------------------------------------------------------------------
    -- 3️⃣ REALIZED P/L — FIFO, ОТДЕЛЬНО ДЛЯ КАЖДОГО АКТИВА
    -------------------------------------------------------------------
    v_realized_pl := 0;

    FOR r_asset IN
        SELECT DISTINCT pa.asset_id
        FROM portfolio_assets pa
        JOIN transactions t ON t.portfolio_asset_id = pa.id
        WHERE pa.portfolio_id = p_portfolio_id
    LOOP
        buy_qty := ARRAY[]::numeric[];
        buy_price := ARRAY[]::numeric[];

        FOR r IN
            SELECT
                t.transaction_type,
                t.quantity::numeric AS qty,
                t.price::numeric AS price
            FROM transactions t
            JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
            WHERE pa.portfolio_id = p_portfolio_id
              AND pa.asset_id = r_asset.asset_id
            ORDER BY t.transaction_date, t.id
        LOOP
            IF r.transaction_type = 1 THEN
                buy_qty   := array_append(buy_qty, r.qty);
                buy_price := array_append(buy_price, r.price);

            ELSIF r.transaction_type = 2 THEN
                remaining := r.qty;
                i := 1;

                WHILE remaining > 0 AND i <= array_length(buy_qty, 1) LOOP
                    IF buy_qty[i] <= 0 THEN
                        i := i + 1;
                        CONTINUE;
                    END IF;

                    IF buy_qty[i] <= remaining THEN
                        v_realized_pl := v_realized_pl +
                            buy_qty[i] * (r.price - buy_price[i]);

                        remaining := remaining - buy_qty[i];
                        buy_qty[i] := 0;
                    ELSE
                        v_realized_pl := v_realized_pl +
                            remaining * (r.price - buy_price[i]);

                        buy_qty[i] := buy_qty[i] - remaining;
                        remaining := 0;
                    END IF;

                    i := i + 1;
                END LOOP;
            END IF;
        END LOOP;
    END LOOP;


    -------------------------------------------------------------------
    -- 4️⃣ TOTAL PROFIT + RETURN %
    -------------------------------------------------------------------
    v_total_profit :=
          v_unrealized_pl
        + v_realized_pl
        + v_dividends
        + v_coupons
        + v_commissions
        + v_taxes;

    IF v_total_invested > 0 THEN
        v_return_percent := v_total_profit / v_total_invested;
    ELSE
        v_return_percent := 0;
    END IF;


    -------------------------------------------------------------------
    -- 5️⃣ Формирование результата
    -------------------------------------------------------------------
    result := jsonb_build_object(
        'total_invested',  v_total_invested,
        'total_value',     v_total_value,
        'unrealized_pl',   v_unrealized_pl,
        'realized_pl',     v_realized_pl,
        'dividends',       v_dividends,
        'coupons',         v_coupons,
        'commissions',     v_commissions,
        'taxes',           v_taxes,
        'total_profit',    v_total_profit,
        'return_percent',  v_return_percent,
        'cash_flow', jsonb_build_object(
            'inflow', v_inflow,
            'outflow', v_outflow
        )
    );

    RETURN result;
END;