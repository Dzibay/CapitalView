
DECLARE
    v_positions_count bigint := 0;
    v_values_count    bigint := 0;

    r_port RECORD;
    r_asset RECORD;
    r_tx RECORD;

    buy_qty   numeric[];
    buy_price numeric[];
    remaining numeric;
    i int;
BEGIN
    ----------------------------------------------------------------------
    -- 0. Удаляем только данные пользователя
    ----------------------------------------------------------------------
    DELETE FROM portfolio_daily_positions
    WHERE portfolio_id IN (SELECT id FROM portfolios WHERE user_id = p_user_id);

    DELETE FROM portfolio_daily_values
    WHERE portfolio_id IN (SELECT id FROM portfolios WHERE user_id = p_user_id);

    ----------------------------------------------------------------------
    -- 1. ПОЗИЦИИ (как и было)
    ----------------------------------------------------------------------
    INSERT INTO portfolio_daily_positions (
        portfolio_id, portfolio_asset_id, tx_date, quantity, cumulative_invested, average_price
    )
    WITH RECURSIVE

    user_pf AS (
        SELECT id AS portfolio_id
        FROM portfolios
        WHERE user_id = p_user_id
    ),

    tx_ordered AS (
        SELECT 
            t.id AS tx_id,
            pa.portfolio_id,
            t.portfolio_asset_id,
            t.transaction_date::date AS tx_date,
            t.transaction_type,
            t.quantity,
            t.price,
            ROW_NUMBER() OVER (
                PARTITION BY t.portfolio_asset_id
                ORDER BY t.transaction_date, t.id
            ) AS rn
        FROM transactions t
        JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
        JOIN user_pf up ON up.portfolio_id = pa.portfolio_id
    ),

    calc AS (
        SELECT
            tx_id, portfolio_id, portfolio_asset_id, tx_date, rn,
            CASE WHEN transaction_type=1 THEN quantity ELSE 0 END AS q,
            CASE WHEN transaction_type=1 THEN quantity*price ELSE 0 END AS inv
        FROM tx_ordered
        WHERE rn=1

        UNION ALL

        SELECT 
            c.tx_id,
            c.portfolio_id,
            c.portfolio_asset_id,
            c.tx_date,
            c.rn,

            GREATEST(0,
                p.q + CASE WHEN c.transaction_type=1 THEN c.quantity ELSE -c.quantity END
            ) AS q,

            CASE 
                WHEN c.transaction_type=1 THEN p.inv + c.quantity*c.price
                WHEN c.transaction_type=2 AND p.q>0 THEN p.inv - (c.quantity * (p.inv/p.q))
                ELSE p.inv
            END AS inv

        FROM tx_ordered c
        JOIN calc p
          ON c.portfolio_asset_id=p.portfolio_asset_id
         AND c.rn=p.rn+1
    ),

    last_tx AS (
        SELECT portfolio_asset_id, tx_date, MAX(rn) AS max_rn
        FROM calc
        GROUP BY portfolio_asset_id, tx_date
    )

    SELECT 
        c.portfolio_id,
        c.portfolio_asset_id,
        c.tx_date,
        c.q AS quantity,
        c.inv AS cumulative_invested,
        CASE WHEN c.q=0 THEN 0 ELSE c.inv/c.q END AS average_price
    FROM calc c
    JOIN last_tx d
      ON d.portfolio_asset_id=c.portfolio_asset_id
     AND d.tx_date=c.tx_date
     AND d.max_rn=c.rn;

    GET DIAGNOSTICS v_positions_count = ROW_COUNT;

    ----------------------------------------------------------------------
    -- 2. FIFO-РЕАЛИЗОВАННАЯ ПРИБЫЛЬ
    ----------------------------------------------------------------------
    DROP TABLE IF EXISTS tmp_fifo_realized;
    CREATE TEMP TABLE tmp_fifo_realized (
        portfolio_id int,
        asset_id     int,
        tx_date      date,
        realized     numeric
    ) ON COMMIT DROP;

    -- цикл по портфелям пользователя
    FOR r_port IN
        SELECT id AS portfolio_id
        FROM portfolios
        WHERE user_id = p_user_id
    LOOP
        -- цикл по активам портфеля
        FOR r_asset IN 
            SELECT DISTINCT asset_id
            FROM portfolio_assets
            WHERE portfolio_id = r_port.portfolio_id
        LOOP
            buy_qty   := ARRAY[]::numeric[];
            buy_price := ARRAY[]::numeric[];

            -- транзакции по активу
            FOR r_tx IN
                SELECT
                    t.transaction_type,
                    t.quantity::numeric AS qty,
                    t.price::numeric AS price,
                    t.transaction_date::date AS tx_date
                FROM transactions t
                JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
                WHERE pa.portfolio_id = r_port.portfolio_id
                  AND pa.asset_id     = r_asset.asset_id
                ORDER BY t.transaction_date, t.id
            LOOP
                IF r_tx.transaction_type = 1 THEN
                    buy_qty   := array_append(buy_qty,   r_tx.qty);
                    buy_price := array_append(buy_price, r_tx.price);

                ELSIF r_tx.transaction_type = 2 THEN
                    remaining := r_tx.qty;
                    i := 1;

                    WHILE remaining > 0 AND i <= COALESCE(array_length(buy_qty,1),0)
                    LOOP
                        IF buy_qty[i] <= 0 THEN
                            i := i+1;
                            CONTINUE;
                        END IF;

                        IF buy_qty[i] <= remaining THEN
                            INSERT INTO tmp_fifo_realized VALUES (
                                r_port.portfolio_id,
                                r_asset.asset_id,
                                r_tx.tx_date,
                                buy_qty[i] * (r_tx.price - buy_price[i])
                            );

                            remaining := remaining - buy_qty[i];
                            buy_qty[i] := 0;

                        ELSE
                            INSERT INTO tmp_fifo_realized VALUES (
                                r_port.portfolio_id,
                                r_asset.asset_id,
                                r_tx.tx_date,
                                remaining * (r_tx.price - buy_price[i])
                            );

                            buy_qty[i] := buy_qty[i] - remaining;
                            remaining := 0;
                        END IF;

                        i := i + 1;
                    END LOOP;

                END IF;
            END LOOP;
        END LOOP;
    END LOOP;

    ----------------------------------------------------------------------
    -- daily + cumulative (реализованная прибыль)
    ----------------------------------------------------------------------
    DROP TABLE IF EXISTS tmp_realized_daily;
    CREATE TEMP TABLE tmp_realized_daily ON COMMIT DROP AS
    SELECT 
        portfolio_id,
        tx_date AS report_date,
        SUM(realized) AS realized_day
    FROM tmp_fifo_realized
    GROUP BY portfolio_id, tx_date;

    DROP TABLE IF EXISTS tmp_realized_cum;
    CREATE TEMP TABLE tmp_realized_cum ON COMMIT DROP AS
    SELECT
        d.portfolio_id,
        d.report_date,
        SUM(COALESCE(rd.realized_day,0)) OVER (
            PARTITION BY d.portfolio_id ORDER BY d.report_date
        ) AS total_realized
    FROM (
        SELECT 
            p.id AS portfolio_id,
            generate_series(
                (SELECT MIN(report_date) FROM tmp_realized_daily rd 
                    WHERE rd.portfolio_id = p.id),
                CURRENT_DATE,
                '1 day'
            )::date AS report_date
        FROM portfolios p
        WHERE p.user_id = p_user_id
    ) d
    LEFT JOIN tmp_realized_daily rd
      ON rd.portfolio_id=d.portfolio_id
     AND rd.report_date=d.report_date;

    ----------------------------------------------------------------------
    -- 3. PAYOUTS (dividend + coupon + tax)
    ----------------------------------------------------------------------
    DROP TABLE IF EXISTS tmp_payouts;
    CREATE TEMP TABLE tmp_payouts ON COMMIT DROP AS
    SELECT
        co.portfolio_id,
        co.date::date AS report_date,
        SUM(CASE WHEN type IN (3,4,8) THEN amount ELSE 0 END) AS payout
    FROM cash_operations co
    WHERE co.portfolio_id IN (SELECT id FROM portfolios WHERE user_id = p_user_id)
    GROUP BY portfolio_id, date::date;

    DROP TABLE IF EXISTS tmp_payouts_cum;
    CREATE TEMP TABLE tmp_payouts_cum ON COMMIT DROP AS
    SELECT
        d.portfolio_id,
        d.report_date,
        SUM(COALESCE(p.payout,0)) OVER (
            PARTITION BY d.portfolio_id ORDER BY d.report_date
        ) AS total_payouts
    FROM (
        SELECT 
            p.id AS portfolio_id,
            generate_series(
                (SELECT MIN(report_date) FROM tmp_payouts WHERE portfolio_id=p.id),
                CURRENT_DATE,
                '1 day'
            )::date AS report_date
        FROM portfolios p
        WHERE p.user_id = p_user_id
    ) d
    LEFT JOIN tmp_payouts p
      ON p.portfolio_id=d.portfolio_id
     AND p.report_date=d.report_date;

    ----------------------------------------------------------------------
    -- 4. TOTAL VALUES (как в all-version)
    ----------------------------------------------------------------------
    INSERT INTO portfolio_daily_values (
        portfolio_id, report_date, total_value, total_invested,
        total_payouts, total_realized, total_pnl
    )
    WITH

    bounds AS (
        SELECT 
            pa.portfolio_id,
            MIN(pdp.tx_date) AS start_date
        FROM portfolio_assets pa
        JOIN portfolio_daily_positions pdp ON pdp.portfolio_asset_id = pa.id
        WHERE pa.portfolio_id IN (SELECT id FROM portfolios WHERE user_id = p_user_id)
        GROUP BY pa.portfolio_id
    ),

    dates AS (
        SELECT 
            portfolio_id,
            generate_series(start_date, CURRENT_DATE, '1 day')::date AS report_date
        FROM bounds
    ),

    pos_ranges AS (
        SELECT 
            pdp.portfolio_asset_id,
            pdp.portfolio_id,
            pdp.tx_date AS valid_from,
            COALESCE(
                LEAD(pdp.tx_date) OVER (PARTITION BY pdp.portfolio_asset_id ORDER BY pdp.tx_date),
                CURRENT_DATE + 1
            ) AS valid_to,
            pdp.quantity,
            pdp.average_price
        FROM portfolio_daily_positions pdp
        WHERE pdp.portfolio_id IN (SELECT id FROM portfolios WHERE user_id = p_user_id)
    ),

    daily_positions AS (
        SELECT
            d.report_date,
            d.portfolio_id,
            pa.asset_id,
            pa.leverage,
            COALESCE(pr.quantity,0) AS quantity,
            COALESCE(pr.average_price,0) AS average_price
        FROM dates d
        JOIN portfolio_assets pa ON pa.portfolio_id = d.portfolio_id
        LEFT JOIN pos_ranges pr
          ON pr.portfolio_asset_id = pa.id
         AND d.report_date >= pr.valid_from
         AND d.report_date <  pr.valid_to
    ),

    clean AS (
        SELECT DISTINCT ON (asset_id, trade_date::date)
            asset_id,
            price,
            trade_date::date AS day
        FROM asset_prices
        ORDER BY asset_id, day, trade_date DESC, id DESC
    ),

    price_ranges AS (
        SELECT
            asset_id,
            price,
            day AS valid_from,
            COALESCE(
                LEAD(day) OVER (PARTITION BY asset_id ORDER BY day),
                CURRENT_DATE+1
            ) AS valid_to
        FROM clean
    ),

    raw AS (
        SELECT
            dp.portfolio_id,
            dp.report_date,
            SUM(dp.quantity * COALESCE(cp.price,0) * COALESCE(qp.price,1) / dp.leverage) AS total_value,
            SUM(dp.quantity * dp.average_price * COALESCE(qp.price,1) / dp.leverage) AS total_invested,
            COALESCE(pc.total_payouts,0) AS total_payouts,
            COALESCE(rc.total_realized,0) AS total_realized
        FROM daily_positions dp
        LEFT JOIN price_ranges cp
          ON cp.asset_id = dp.asset_id
         AND dp.report_date >= cp.valid_from
         AND dp.report_date <  cp.valid_to

        LEFT JOIN assets a ON a.id = dp.asset_id

        LEFT JOIN price_ranges qp
          ON qp.asset_id = a.quote_asset_id
         AND dp.report_date >= qp.valid_from
         AND dp.report_date <  qp.valid_to

        LEFT JOIN tmp_payouts_cum pc
          ON pc.portfolio_id=dp.portfolio_id
         AND pc.report_date=dp.report_date

        LEFT JOIN tmp_realized_cum rc
          ON rc.portfolio_id=dp.portfolio_id
         AND rc.report_date=dp.report_date

        GROUP BY dp.portfolio_id, dp.report_date, pc.total_payouts, rc.total_realized
    ),

    filt AS (
        SELECT
            *,
            LAG(total_value,1,0) OVER (PARTITION BY portfolio_id ORDER BY report_date) AS prev_v
        FROM raw
    )

    SELECT
        portfolio_id,
        report_date,
        total_value,
        total_invested,
        total_payouts,
        total_realized,
        (total_value - total_invested + total_payouts + total_realized) AS total_pnl
    FROM filt
    WHERE total_value > 0.0001 OR prev_v > 0.0001;

    GET DIAGNOSTICS v_values_count = ROW_COUNT;

    ----------------------------------------------------------------------
    -- RETURN
    ----------------------------------------------------------------------
    RETURN json_build_object(
        'success', true,
        'updated_at', now(),
        'positions_rows', v_positions_count,
        'values_rows', v_values_count
    );
END;
