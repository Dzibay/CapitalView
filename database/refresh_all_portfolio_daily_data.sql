
DECLARE
    v_positions_count bigint := 0;
    v_values_count bigint := 0;

BEGIN
    ------------------------------------------------------------------
    -- 0. Чистим таблицы
    ------------------------------------------------------------------
    TRUNCATE TABLE portfolio_daily_positions;
    TRUNCATE TABLE portfolio_daily_values;

    ------------------------------------------------------------------
    -- 1. Cчитаем позиции (как раньше – без изменений)
    ------------------------------------------------------------------
    INSERT INTO portfolio_daily_positions (
        portfolio_id, portfolio_asset_id, tx_date, quantity, cumulative_invested, average_price
    )
    WITH RECURSIVE
    tx_ordered AS (
        SELECT 
            t.id AS tx_id,
            t.portfolio_asset_id,
            pa.portfolio_id,
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
    ),
    calc_positions AS (
        SELECT 
            tx_id, portfolio_id, portfolio_asset_id, tx_date, rn,
            CASE WHEN transaction_type = 1 THEN quantity ELSE 0 END AS current_qty,
            CASE WHEN transaction_type = 1 THEN quantity*price ELSE 0 END AS current_invested
        FROM tx_ordered
        WHERE rn=1

        UNION ALL

        SELECT
            curr.tx_id, curr.portfolio_id, curr.portfolio_asset_id,
            curr.tx_date, curr.rn,
            GREATEST(
                0,
                prev.current_qty +
                CASE WHEN curr.transaction_type=1 THEN curr.quantity ELSE -curr.quantity END
            ),
            CASE 
                WHEN curr.transaction_type=1 THEN prev.current_invested + curr.quantity*curr.price
                WHEN curr.transaction_type=2 AND prev.current_qty>0 THEN
                    prev.current_invested - (curr.quantity * (prev.current_invested / prev.current_qty))
                ELSE prev.current_invested
            END
        FROM tx_ordered curr 
        JOIN calc_positions prev 
        ON curr.portfolio_asset_id=prev.portfolio_asset_id AND curr.rn=prev.rn+1
    ),
    last_tx AS (
        SELECT portfolio_asset_id, tx_date, MAX(rn) AS max_rn
        FROM calc_positions
        GROUP BY portfolio_asset_id, tx_date
    )
    SELECT
        c.portfolio_id, c.portfolio_asset_id, c.tx_date,
        c.current_qty, c.current_invested,
        CASE WHEN c.current_qty=0 THEN 0 ELSE c.current_invested/c.current_qty END
    FROM calc_positions c
    JOIN last_tx d
      ON d.portfolio_asset_id=c.portfolio_asset_id AND d.tx_date=c.tx_date AND d.max_rn=c.rn;

    GET DIAGNOSTICS v_positions_count = ROW_COUNT;



    ------------------------------------------------------------------
    -- 2. FIFO РЕАЛИЗОВАННАЯ ПРИБЫЛЬ (отдельный процесс!)
    ------------------------------------------------------------------
    CREATE TEMP TABLE tmp_realized_fifo (
        portfolio_id int,
        asset_id int,
        tx_date date,
        realized numeric
    ) ON COMMIT DROP;

    DECLARE 
        r_portfolio RECORD;
        r_asset RECORD;
        r_tx RECORD;
        buy_qty numeric[];
        buy_price numeric[];
        remaining numeric;
        i int;
    BEGIN
        FOR r_portfolio IN 
            SELECT DISTINCT portfolio_id FROM portfolio_assets
        LOOP
            FOR r_asset IN 
                SELECT DISTINCT asset_id 
                FROM portfolio_assets 
                WHERE portfolio_id = r_portfolio.portfolio_id
            LOOP
                buy_qty := ARRAY[]::numeric[];
                buy_price := ARRAY[]::numeric[];

                FOR r_tx IN 
                    SELECT 
                        t.transaction_type,
                        t.quantity::numeric AS qty,
                        t.price::numeric AS price,
                        t.transaction_date::date AS tx_date
                    FROM transactions t
                    JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
                    WHERE pa.portfolio_id = r_portfolio.portfolio_id
                      AND pa.asset_id = r_asset.asset_id
                    ORDER BY t.transaction_date, t.id
                LOOP
                    IF r_tx.transaction_type = 1 THEN
                        buy_qty := array_append(buy_qty, r_tx.qty);
                        buy_price := array_append(buy_price, r_tx.price);

                    ELSIF r_tx.transaction_type = 2 THEN
                        remaining := r_tx.qty;
                        i := 1;

                        WHILE remaining > 0 AND i <= array_length(buy_qty,1)
                        LOOP
                            IF buy_qty[i] <= 0 THEN 
                                i := i+1;
                                CONTINUE;
                            END IF;

                            IF buy_qty[i] <= remaining THEN
                                INSERT INTO tmp_realized_fifo VALUES (
                                    r_portfolio.portfolio_id,
                                    r_asset.asset_id,
                                    r_tx.tx_date,
                                    buy_qty[i] * (r_tx.price - buy_price[i])
                                );
                                remaining := remaining - buy_qty[i];
                                buy_qty[i] := 0;
                            ELSE
                                INSERT INTO tmp_realized_fifo VALUES (
                                    r_portfolio.portfolio_id,
                                    r_asset.asset_id,
                                    r_tx.tx_date,
                                    remaining * (r_tx.price - buy_price[i])
                                );
                                buy_qty[i] := buy_qty[i] - remaining;
                                remaining := 0;
                            END IF;

                            i := i+1;
                        END LOOP;
                    END IF;
                END LOOP;
            END LOOP;
        END LOOP;
    END;



    ------------------------------------------------------------------
    -- 3. Теперь превращаем realized в cumulative-realized
    ------------------------------------------------------------------
    CREATE TEMP TABLE tmp_realized_daily AS
    SELECT 
        portfolio_id,
        tx_date AS report_date,
        SUM(realized) AS realized_day
    FROM tmp_realized_fifo
    GROUP BY portfolio_id, tx_date;

    CREATE TEMP TABLE tmp_realized_cumulative AS
    SELECT
        d.portfolio_id,
        d.report_date,
        SUM(COALESCE(rd.realized_day,0)) OVER (
            PARTITION BY d.portfolio_id ORDER BY d.report_date
        ) AS total_realized
    FROM (
        SELECT 
            pa.portfolio_id,
            generate_series(
                COALESCE(
                    (SELECT MIN(report_date) FROM tmp_realized_daily),
                    (SELECT MIN(pdp.tx_date) FROM portfolio_daily_positions pdp WHERE pdp.portfolio_id = pa.portfolio_id)
                ),
                CURRENT_DATE,
                '1 day'
            )::date AS report_date
        FROM portfolio_assets pa
        GROUP BY pa.portfolio_id
    ) d
    LEFT JOIN tmp_realized_daily rd
      ON rd.portfolio_id=d.portfolio_id 
     AND rd.report_date=d.report_date;

    ------------------------------------------------------------------
    -- 4. PAYOUTS (дивиденды, купоны, налоги)
    ------------------------------------------------------------------
    CREATE TEMP TABLE tmp_payouts AS
    SELECT 
        portfolio_id,
        date::date AS report_date,
        SUM(CASE WHEN type IN (3,4,8) THEN amount ELSE 0 END) AS payout
    FROM cash_operations
    GROUP BY portfolio_id, date::date;

    CREATE TEMP TABLE tmp_payouts_cumulative AS
    SELECT 
        d.portfolio_id,
        d.report_date,
        SUM(COALESCE(p.payout,0)) OVER (
            PARTITION BY d.portfolio_id ORDER BY d.report_date
        ) AS total_payouts
    FROM (
        SELECT 
            pa.portfolio_id,
            generate_series(
                (SELECT MIN(report_date) FROM tmp_payouts),
                CURRENT_DATE,
                '1 day'
            )::date AS report_date
        FROM portfolio_assets pa
        GROUP BY pa.portfolio_id
    ) d
    LEFT JOIN tmp_payouts p 
      ON p.portfolio_id=d.portfolio_id AND p.report_date=d.report_date;




    ------------------------------------------------------------------
    -- 5. TOTAL VALUES
    ------------------------------------------------------------------
    INSERT INTO portfolio_daily_values (
        portfolio_id, report_date, total_value, total_invested,
        total_payouts, total_realized, total_pnl
    )
    WITH
    bounds AS (
        SELECT 
            pa.portfolio_id,
            MIN(pdp.tx_date)::date as start_date
        FROM portfolio_assets pa
        JOIN portfolio_daily_positions pdp ON pdp.portfolio_asset_id = pa.id
        GROUP BY pa.portfolio_id
    ),
    dates AS (
        SELECT 
            b.portfolio_id,
            generate_series(
                b.start_date,
                CURRENT_DATE,
                '1 day'
            )::date AS report_date
        FROM bounds b
    ),
    pos_ranges AS (
        SELECT 
            pdp.portfolio_asset_id,
            pdp.tx_date AS valid_from,
            COALESCE(
                LEAD(pdp.tx_date) OVER (PARTITION BY pdp.portfolio_asset_id ORDER BY pdp.tx_date),
                CURRENT_DATE + 1
            ) AS valid_to,
            pdp.quantity,
            pdp.average_price
        FROM portfolio_daily_positions pdp
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
           ON pr.portfolio_asset_id=pa.id
          AND d.report_date>=pr.valid_from
          AND d.report_date<pr.valid_to
    ),

    price_ranges AS (
        WITH clean_prices AS (
            SELECT DISTINCT ON (asset_id, trade_date::date)
                asset_id,
                price,
                trade_date::date AS day
            FROM asset_prices
            ORDER BY asset_id, day, trade_date DESC, id DESC
        )
        SELECT 
            asset_id,
            price,
            day AS valid_from,
            COALESCE(
                LEAD(day) OVER (PARTITION BY asset_id ORDER BY day),
                CURRENT_DATE+1
            ) AS valid_to
        FROM clean_prices
    ),

    raw AS (
        SELECT
            dp.portfolio_id,
            dp.report_date,
            SUM(dp.quantity * COALESCE(curr_p.price,0) *
                COALESCE(quote_p.price,1) / dp.leverage) AS total_value,
            SUM(dp.quantity * dp.average_price *
                COALESCE(quote_p.price,1) / dp.leverage) AS total_invested,
            COALESCE(pr.total_realized,0) AS total_realized,
            COALESCE(cp.total_payouts,0) AS total_payouts
        FROM daily_positions dp
        LEFT JOIN price_ranges curr_p 
               ON curr_p.asset_id=dp.asset_id
              AND dp.report_date>=curr_p.valid_from
              AND dp.report_date<curr_p.valid_to
        LEFT JOIN assets a ON a.id=dp.asset_id
        LEFT JOIN price_ranges quote_p 
               ON quote_p.asset_id=a.quote_asset_id
              AND dp.report_date>=quote_p.valid_from
              AND dp.report_date<quote_p.valid_to
        LEFT JOIN tmp_realized_cumulative pr
               ON pr.portfolio_id=dp.portfolio_id AND pr.report_date=dp.report_date
        LEFT JOIN tmp_payouts_cumulative cp
               ON cp.portfolio_id=dp.portfolio_id AND cp.report_date=dp.report_date
        GROUP BY dp.portfolio_id, dp.report_date, pr.total_realized, cp.total_payouts
    ),

    filtered AS (
        SELECT 
            *,
            LAG(total_value,1,0) OVER (
                PARTITION BY portfolio_id ORDER BY report_date
            ) AS prev_value
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
    FROM filtered
    WHERE total_value > 0.0001 OR prev_value > 0.0001;

    GET DIAGNOSTICS v_values_count = ROW_COUNT;


    ------------------------------------------------------------------
    -- RETURN
    ------------------------------------------------------------------
    RETURN json_build_object(
        'success', true,
        'positions_rows', v_positions_count,
        'values_rows', v_values_count,
        'updated_at', now()
    );

END;
