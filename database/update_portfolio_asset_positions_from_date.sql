CREATE OR REPLACE FUNCTION update_portfolio_asset_positions_from_date(
    p_portfolio_asset_id bigint,
    p_from_date date DEFAULT '0001-01-01'
)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
    v_portfolio_id bigint;
    v_asset_id bigint;
    v_quote_asset_id bigint;
    v_leverage numeric;
    v_base_qty numeric := 0;
    v_base_inv numeric := 0;
    v_base_realized numeric := 0;
    v_base_payouts numeric := 0;
    v_base_commissions numeric := 0;
    v_base_taxes numeric := 0;
    v_first_tx_date date;
    v_series_start date;
    v_d date;
    r_tx RECORD;
    v_sell_rem numeric;
    v_lot_id bigint;
    v_lot_q numeric;
    v_lot_c numeric;
    v_take numeric;
    v_unit_cost numeric;
    v_cost_take numeric;
    v_qty numeric;
    v_inv numeric;
    v_avg_quote numeric;
    v_has_tx boolean;
BEGIN
    SELECT 
        pa.portfolio_id,
        pa.asset_id,
        a.quote_asset_id,
        COALESCE(pa.leverage, 1)::numeric,
        COALESCE((SELECT min(t.transaction_date::date) FROM transactions t WHERE t.portfolio_asset_id = p_portfolio_asset_id), p_from_date)
    INTO 
        v_portfolio_id,
        v_asset_id,
        v_quote_asset_id,
        v_leverage,
        v_first_tx_date
    FROM portfolio_assets pa
    JOIN assets a ON a.id = pa.asset_id
    WHERE pa.id = p_portfolio_asset_id;
    
    IF v_portfolio_id IS NULL THEN
        RETURN false;
    END IF;
    
    SELECT 
        pdp.quantity, 
        pdp.cumulative_invested,
        COALESCE(pdp.realized_pnl, 0),
        COALESCE(pdp.payouts, 0),
        COALESCE(pdp.commissions, 0),
        COALESCE(pdp.taxes, 0)
    INTO 
        v_base_qty, 
        v_base_inv,
        v_base_realized,
        v_base_payouts,
        v_base_commissions,
        v_base_taxes
    FROM portfolio_asset_daily_values pdp
    WHERE pdp.portfolio_asset_id = p_portfolio_asset_id
      AND pdp.report_date < p_from_date
    ORDER BY pdp.report_date DESC
    LIMIT 1;
    
    v_base_qty := COALESCE(v_base_qty, 0);
    v_base_inv := COALESCE(v_base_inv, 0);
    v_base_realized := COALESCE(v_base_realized, 0);
    v_base_payouts := COALESCE(v_base_payouts, 0);
    v_base_commissions := COALESCE(v_base_commissions, 0);
    v_base_taxes := COALESCE(v_base_taxes, 0);
    
    DELETE FROM portfolio_asset_daily_values
    WHERE portfolio_asset_id = p_portfolio_asset_id
      AND report_date >= p_from_date;

    PERFORM pg_advisory_xact_lock(hashtext('fifo_pos_' || p_portfolio_asset_id::text));

    DROP TABLE IF EXISTS _fifo_work_pa;
    CREATE TEMP TABLE _fifo_work_pa (
        id bigserial PRIMARY KEY,
        rem_qty numeric NOT NULL,
        rem_cost_rub numeric NOT NULL,
        unit_price_quote numeric NOT NULL
    );

    DROP TABLE IF EXISTS _fifo_daily_pa;
    CREATE TEMP TABLE _fifo_daily_pa (
        report_date date PRIMARY KEY,
        quantity numeric NOT NULL,
        cumulative_invested numeric NOT NULL,
        average_price numeric NOT NULL
    );

    SELECT EXISTS (
        SELECT 1 FROM transactions t WHERE t.portfolio_asset_id = p_portfolio_asset_id
    ) INTO v_has_tx;

    v_series_start := GREATEST(p_from_date, v_first_tx_date);

    IF NOT v_has_tx THEN
        FOR v_d IN
            SELECT generate_series(v_series_start, CURRENT_DATE, interval '1 day')::date AS d
        LOOP
            INSERT INTO _fifo_daily_pa (
                report_date,
                quantity,
                cumulative_invested,
                average_price
            ) VALUES (
                v_d,
                v_base_qty,
                GREATEST(v_base_inv, 0),
                CASE WHEN v_base_qty > 0 THEN v_base_inv / v_base_qty ELSE 0 END
            );
        END LOOP;
    ELSE
        FOR r_tx IN
            SELECT
                t.id,
                t.transaction_date::date AS tx_date,
                t.transaction_type AS tt,
                t.quantity::numeric AS qty,
                t.price::numeric AS price,
                COALESCE(
                    (
                        SELECT ABS(co.amount_rub)::numeric
                        FROM cash_operations co
                        WHERE co.transaction_id = t.id
                          AND co.type IN (1, 2)
                        LIMIT 1
                    ),
                    t.quantity * t.price
                )::numeric AS amount_rub
            FROM transactions t
            WHERE t.portfolio_asset_id = p_portfolio_asset_id
              AND t.transaction_date::date < v_series_start
            ORDER BY t.transaction_date, t.id
        LOOP
            IF r_tx.tt = 1 THEN
                INSERT INTO _fifo_work_pa (rem_qty, rem_cost_rub, unit_price_quote)
                VALUES (r_tx.qty, r_tx.amount_rub, r_tx.price);
            ELSIF r_tx.tt IN (2, 3) THEN
                v_sell_rem := r_tx.qty;
                WHILE v_sell_rem > 0 LOOP
                    v_lot_id := NULL;
                    SELECT w.id, w.rem_qty, w.rem_cost_rub
                    INTO v_lot_id, v_lot_q, v_lot_c
                    FROM _fifo_work_pa w
                    WHERE w.rem_qty > 0
                    ORDER BY w.id
                    LIMIT 1;

                    IF v_lot_id IS NULL THEN
                        RAISE EXCEPTION 'FIFO: недостаточно лотов для продажи (portfolio_asset_id=%)', p_portfolio_asset_id;
                    END IF;

                    v_take := LEAST(v_sell_rem, v_lot_q);
                    v_unit_cost := v_lot_c / NULLIF(v_lot_q, 0);
                    v_cost_take := v_take * v_unit_cost;

                    UPDATE _fifo_work_pa
                    SET
                        rem_qty = rem_qty - v_take,
                        rem_cost_rub = rem_cost_rub - v_cost_take
                    WHERE id = v_lot_id;

                    DELETE FROM _fifo_work_pa WHERE rem_qty <= 0;

                    v_sell_rem := v_sell_rem - v_take;
                END LOOP;
            END IF;
        END LOOP;

        FOR v_d IN
            SELECT generate_series(v_series_start, CURRENT_DATE, interval '1 day')::date AS d
        LOOP
            FOR r_tx IN
                SELECT
                    t.id,
                    t.transaction_date::date AS tx_date,
                    t.transaction_type AS tt,
                    t.quantity::numeric AS qty,
                    t.price::numeric AS price,
                    COALESCE(
                        (
                            SELECT ABS(co.amount_rub)::numeric
                            FROM cash_operations co
                            WHERE co.transaction_id = t.id
                              AND co.type IN (1, 2)
                            LIMIT 1
                        ),
                        t.quantity * t.price
                    )::numeric AS amount_rub
                FROM transactions t
                WHERE t.portfolio_asset_id = p_portfolio_asset_id
                  AND t.transaction_date::date = v_d
                ORDER BY t.transaction_date, t.id
            LOOP
                IF r_tx.tt = 1 THEN
                    INSERT INTO _fifo_work_pa (rem_qty, rem_cost_rub, unit_price_quote)
                    VALUES (r_tx.qty, r_tx.amount_rub, r_tx.price);
                ELSIF r_tx.tt IN (2, 3) THEN
                    v_sell_rem := r_tx.qty;
                    WHILE v_sell_rem > 0 LOOP
                        v_lot_id := NULL;
                        SELECT w.id, w.rem_qty, w.rem_cost_rub
                        INTO v_lot_id, v_lot_q, v_lot_c
                        FROM _fifo_work_pa w
                        WHERE w.rem_qty > 0
                        ORDER BY w.id
                        LIMIT 1;

                        IF v_lot_id IS NULL THEN
                            RAISE EXCEPTION 'FIFO: недостаточно лотов для продажи (portfolio_asset_id=%)', p_portfolio_asset_id;
                        END IF;

                        v_take := LEAST(v_sell_rem, v_lot_q);
                        v_unit_cost := v_lot_c / NULLIF(v_lot_q, 0);
                        v_cost_take := v_take * v_unit_cost;

                        UPDATE _fifo_work_pa
                        SET
                            rem_qty = rem_qty - v_take,
                            rem_cost_rub = rem_cost_rub - v_cost_take
                        WHERE id = v_lot_id;

                        DELETE FROM _fifo_work_pa WHERE rem_qty <= 0;

                        v_sell_rem := v_sell_rem - v_take;
                    END LOOP;
                END IF;
            END LOOP;

            SELECT
                COALESCE(SUM(w.rem_qty), 0),
                COALESCE(SUM(w.rem_cost_rub), 0),
                CASE
                    WHEN COALESCE(SUM(w.rem_qty), 0) > 0 THEN
                        SUM(w.rem_qty * w.unit_price_quote) / SUM(w.rem_qty)
                    ELSE 0::numeric
                END
            INTO v_qty, v_inv, v_avg_quote
            FROM _fifo_work_pa w;

            INSERT INTO _fifo_daily_pa (
                report_date,
                quantity,
                cumulative_invested,
                average_price
            ) VALUES (
                v_d,
                v_qty,
                GREATEST(v_inv, 0),
                COALESCE(v_avg_quote, 0)
            );
        END LOOP;
    END IF;

    DROP TABLE IF EXISTS _fifo_analytics_pa;
    CREATE TEMP TABLE _fifo_analytics_pa (
        report_date date PRIMARY KEY,
        realized_pnl numeric,
        payouts numeric,
        commissions numeric,
        taxes numeric
    );

    INSERT INTO _fifo_analytics_pa (report_date, realized_pnl, payouts, commissions, taxes)
    WITH
    dates AS (
        SELECT report_date FROM _fifo_daily_pa ORDER BY report_date
    ),
    realized_daily AS (
        SELECT
            t.transaction_date::date AS report_date,
            SUM(
                t.realized_pnl::numeric
                * COALESCE(
                    (
                        SELECT price::numeric
                        FROM asset_prices ap
                        WHERE ap.asset_id = v_quote_asset_id
                          AND ap.trade_date <= t.transaction_date::date
                        ORDER BY ap.trade_date DESC
                        LIMIT 1
                    ),
                    (
                        SELECT curr_price::numeric
                        FROM asset_latest_prices
                        WHERE asset_id = v_quote_asset_id
                    ),
                    CASE
                        WHEN v_quote_asset_id IS NULL OR v_quote_asset_id = 1 THEN 1::numeric
                        ELSE 1::numeric
                    END
                )
                / NULLIF(v_leverage, 0)
            ) AS realized_day
        FROM transactions t
        WHERE t.portfolio_asset_id = p_portfolio_asset_id
          AND t.transaction_type IN (2, 3)
          AND t.realized_pnl IS NOT NULL
          AND t.transaction_date::date >= p_from_date
        GROUP BY t.transaction_date::date
    ),
    payouts_daily AS (
        SELECT
            co.date::date AS report_date,
            SUM(COALESCE(co.amount_rub, co.amount))::numeric AS payout_day
        FROM cash_operations co
        WHERE co.portfolio_id = v_portfolio_id
          AND co.asset_id = v_asset_id
          AND co.type IN (3, 4)
          AND co.date::date >= p_from_date
        GROUP BY co.date::date
    ),
    commissions_daily AS (
        SELECT
            co.date::date AS report_date,
            SUM(ABS(COALESCE(co.amount_rub, co.amount)))::numeric AS commission_day
        FROM cash_operations co
        WHERE co.portfolio_id = v_portfolio_id
          AND co.asset_id = v_asset_id
          AND co.type IN (7)
          AND co.date::date >= p_from_date
        GROUP BY co.date::date
    ),
    taxes_daily AS (
        SELECT
            co.date::date AS report_date,
            SUM(ABS(COALESCE(co.amount_rub, co.amount)))::numeric AS tax_day
        FROM cash_operations co
        WHERE co.portfolio_id = v_portfolio_id
          AND co.asset_id = v_asset_id
          AND co.type IN (8)
          AND co.date::date >= p_from_date
        GROUP BY co.date::date
    ),
    analytics_cum AS (
        SELECT
            d.report_date,
            ROUND(
                v_base_realized
                + COALESCE(
                    SUM(COALESCE(rd.realized_day, 0)) OVER (ORDER BY d.report_date),
                    0
                ),
                2
            ) AS realized_pnl,
            ROUND(
                v_base_payouts
                + COALESCE(
                    SUM(COALESCE(pd.payout_day, 0)) OVER (ORDER BY d.report_date),
                    0
                ),
                2
            ) AS payouts,
            ROUND(
                v_base_commissions
                + COALESCE(
                    SUM(COALESCE(cd.commission_day, 0)) OVER (ORDER BY d.report_date),
                    0
                ),
                2
            ) AS commissions,
            ROUND(
                v_base_taxes
                + COALESCE(
                    SUM(COALESCE(td.tax_day, 0)) OVER (ORDER BY d.report_date),
                    0
                ),
                2
            ) AS taxes
        FROM dates d
        LEFT JOIN realized_daily rd ON rd.report_date = d.report_date
        LEFT JOIN payouts_daily pd ON pd.report_date = d.report_date
        LEFT JOIN commissions_daily cd ON cd.report_date = d.report_date
        LEFT JOIN taxes_daily td ON td.report_date = d.report_date
    )
    SELECT report_date, realized_pnl, payouts, commissions, taxes
    FROM analytics_cum;

    INSERT INTO portfolio_asset_daily_values (
        portfolio_id,
        portfolio_asset_id,
        report_date,
        quantity,
        cumulative_invested,
        average_price,
        position_value,
        realized_pnl,
        payouts,
        commissions,
        taxes,
        total_pnl
    )
    SELECT
        v_portfolio_id,
        p_portfolio_asset_id,
        dp.report_date,
        dp.quantity,
        ROUND(dp.cumulative_invested, 2) AS cumulative_invested,
        ROUND(dp.average_price, 2) AS average_price,
        ROUND(
            (
                dp.quantity
                * ud.unit_dirty
                * COALESCE(cr.rate_to_rub, 1)
                / NULLIF(v_leverage, 0)
            ),
            2
        ) AS position_value,
        ROUND(ac.realized_pnl, 2) AS realized_pnl,
        ROUND(ac.payouts, 2) AS payouts,
        ROUND(ac.commissions, 2) AS commissions,
        ROUND(ac.taxes, 2) AS taxes,
        ROUND(
            (
                ROUND(dp.quantity * ud.unit_dirty * COALESCE(cr.rate_to_rub, 1) / NULLIF(v_leverage, 0), 2)
                - ROUND(dp.cumulative_invested, 2)
                + ROUND(ac.realized_pnl, 2)
                + ROUND(ac.payouts, 2)
                - ROUND(ac.commissions, 2)
                - ROUND(ac.taxes, 2)
            ),
            2
        ) AS total_pnl
    FROM _fifo_daily_pa dp
    INNER JOIN _fifo_analytics_pa ac ON ac.report_date = dp.report_date
    LEFT JOIN LATERAL (
        SELECT
            CASE 
                WHEN v_quote_asset_id IS NULL OR v_quote_asset_id = 1 THEN 1::numeric
                ELSE COALESCE(
                    (
                        SELECT ap.price::numeric
                        FROM asset_prices ap
                        WHERE ap.asset_id = v_quote_asset_id
                          AND ap.trade_date <= dp.report_date
                        ORDER BY ap.trade_date DESC
                        LIMIT 1
                    ),
                    (
                        SELECT ap.price::numeric
                        FROM asset_prices ap
                        WHERE ap.asset_id = v_quote_asset_id
                        ORDER BY ap.trade_date DESC
                        LIMIT 1
                    ),
                    1::numeric
                )
            END AS rate_to_rub
    ) cr ON true
    CROSS JOIN LATERAL (
        SELECT COALESCE(
            (
                SELECT ap.price::numeric + COALESCE(ap.accrued_coupon, 0)::numeric
                FROM asset_prices ap
                WHERE ap.asset_id = v_asset_id
                  AND ap.trade_date <= dp.report_date
                ORDER BY ap.trade_date DESC
                LIMIT 1
            ),
            CASE
                WHEN dp.report_date = CURRENT_DATE THEN
                    (
                        SELECT COALESCE(alp.curr_price, 0)::numeric + COALESCE(alp.curr_accrued, 0)::numeric
                        FROM asset_latest_prices alp
                        WHERE alp.asset_id = v_asset_id
                    )
                ELSE NULL::numeric
            END,
            0::numeric
        ) AS unit_dirty
    ) ud;

    DROP TABLE IF EXISTS _fifo_work_pa;
    DROP TABLE IF EXISTS _fifo_daily_pa;
    DROP TABLE IF EXISTS _fifo_analytics_pa;

    RETURN true;
END;
$$;

COMMENT ON FUNCTION update_portfolio_asset_positions_from_date(bigint, date) IS 'Пересчитывает portfolio_asset_daily_values; остаточная себестоимость и средняя цена — FIFO по транзакциям (как у брокера), в рублях по amount_rub покупок; стоимость позиции = qty * (цена+НКД) * курс / leverage';
