-- Позиции с выплатами для дерева портфелей (страница «Дивиденды»).
-- Валюта сумм: ap.value, expected_total, received_total — в валюте котировки актива (currency_ticker = qa.ticker).
-- Фронт: карточка показывает сумму в этой валюте; агрегаты по дню/месяцу — перевод в ₽ по справочнику.
-- 1) Отсекаем выплаты до появления позиции: portfolio_assets.created_at::date.
-- 2) Будущие: payment_date IS NULL или payment_date > CURRENT_DATE (как в check_missed_payouts — в проверку неполученных не входят).
-- 3) Прошедшие: та же логика, что check_missed_payouts (даты отсечки по type_id, quantity из
--    portfolio_asset_daily_values, сумма из cash_operations ±14 дней, валюта/RUB, допуск 3%).
-- 4) received / missed / future + объединённый payouts (с полем status) для обратной совместимости.
CREATE OR REPLACE FUNCTION get_portfolio_payout_positions(p_user_id uuid, p_root_portfolio_id int)
RETURNS json
LANGUAGE plpgsql
AS $$
DECLARE
    v_rub_currency_id bigint;
    v_type_dividend bigint;
    v_type_coupon bigint;
    v_type_amortization bigint;
    r_pa RECORD;
    r_payout RECORD;
    v_check_date date;
    v_quantity_on_date numeric;
    v_quantity_on_payment_date numeric;
    v_expected_amount numeric;
    v_expected_tolerance numeric;
    v_received_amount_in_payout_ccy numeric;
    v_payout_currency_id bigint;
    v_payout_currency_to_rub_rate numeric(20,6);
    v_quote_currency_id bigint;
    v_currency_to_quote_rate numeric(20,6);
    v_quote_to_rub_rate numeric(20,6);
    v_operation_type_id bigint;
    v_status text;
    v_obj jsonb;
    v_received jsonb;
    v_future jsonb;
    v_missed jsonb;
    v_payouts jsonb;
    v_positions jsonb := '[]'::jsonb;
    v_elem jsonb;
BEGIN
    SELECT id INTO v_rub_currency_id FROM assets WHERE UPPER(ticker) = 'RUB' LIMIT 1;
    IF v_rub_currency_id IS NULL THEN
        v_rub_currency_id := 1;
    END IF;

    SELECT id INTO v_type_dividend FROM operations_type WHERE name = 'Dividend' LIMIT 1;
    SELECT id INTO v_type_coupon FROM operations_type WHERE name = 'Coupon' LIMIT 1;
    SELECT id INTO v_type_amortization FROM operations_type WHERE name = 'Amortization' LIMIT 1;
    IF v_type_dividend IS NULL OR v_type_coupon IS NULL OR v_type_amortization IS NULL THEN
        RAISE EXCEPTION 'operations_type: требуются Dividend, Coupon, Amortization';
    END IF;

    FOR r_pa IN
        WITH RECURSIVE tree AS (
            SELECT id FROM portfolios WHERE id = p_root_portfolio_id AND user_id = p_user_id
            UNION ALL
            SELECT p.id
            FROM portfolios p
            INNER JOIN tree t ON p.parent_portfolio_id = t.id
        )
        SELECT
            pa.id AS pa_id,
            pa.portfolio_id,
            pa.asset_id,
            pa.quantity,
            pa.created_at::date AS position_since,
            p.user_id,
            a.name AS asset_name,
            a.ticker AS asset_ticker,
            qa.ticker AS currency_ticker
        FROM portfolio_assets pa
        INNER JOIN tree tr ON tr.id = pa.portfolio_id
        INNER JOIN portfolios p ON p.id = pa.portfolio_id
        INNER JOIN assets a ON a.id = pa.asset_id
        LEFT JOIN assets qa ON qa.id = a.quote_asset_id
        WHERE pa.asset_id IS NOT NULL
        ORDER BY pa.id
    LOOP
        SELECT COALESCE(a.quote_asset_id, v_rub_currency_id)
        INTO v_payout_currency_id
        FROM assets a
        WHERE a.id = r_pa.asset_id;
        IF v_payout_currency_id IS NULL THEN
            v_payout_currency_id := v_rub_currency_id;
        END IF;

        v_received := '[]'::jsonb;
        v_future := '[]'::jsonb;
        v_missed := '[]'::jsonb;
        v_payouts := '[]'::jsonb;

        FOR r_payout IN
            SELECT
                ap.id,
                ap.asset_id,
                ap.value,
                ap.dividend_yield,
                ap.last_buy_date,
                ap.record_date,
                ap.payment_date,
                ap.type_id,
                pt.code AS type_code
            FROM asset_payouts ap
            INNER JOIN payout_types pt ON pt.id = ap.type_id
            WHERE ap.asset_id = r_pa.asset_id
              AND (
                  COALESCE(ap.record_date, ap.payment_date) IS NULL
                  OR COALESCE(ap.record_date, ap.payment_date)::date >= r_pa.position_since
              )
            ORDER BY ap.payment_date DESC NULLS LAST, ap.record_date DESC NULLS LAST
        LOOP
            IF r_payout.type_id = 2 THEN
                v_check_date := r_payout.record_date;
            ELSIF r_payout.type_id = 1 THEN
                v_check_date := r_payout.last_buy_date;
            ELSE
                v_check_date := COALESCE(
                    r_payout.record_date,
                    r_payout.last_buy_date,
                    r_payout.payment_date
                );
            END IF;

            -- Будущие / без даты выплаты — как в check_missed_payouts (не проверяем cash_operations)
            IF r_payout.payment_date IS NULL OR r_payout.payment_date > CURRENT_DATE THEN
                v_obj := jsonb_build_object(
                    'id', r_payout.id,
                    'last_buy_date', r_payout.last_buy_date,
                    'record_date', r_payout.record_date,
                    'payment_date', r_payout.payment_date,
                    'value', r_payout.value,
                    'dividend_yield', r_payout.dividend_yield,
                    'type', r_payout.type_code,
                    'status', 'future'
                );
                v_future := v_future || jsonb_build_array(v_obj);
                v_payouts := v_payouts || jsonb_build_array(v_obj);
                CONTINUE;
            END IF;

            IF v_check_date IS NULL THEN
                CONTINUE;
            END IF;

            SELECT pav.quantity
            INTO v_quantity_on_date
            FROM portfolio_asset_daily_values pav
            WHERE pav.portfolio_asset_id = r_pa.pa_id
              AND pav.report_date <= v_check_date
            ORDER BY pav.report_date DESC
            LIMIT 1;

            IF v_quantity_on_date IS NULL OR v_quantity_on_date <= 0 THEN
                CONTINUE;
            END IF;

            SELECT pav.quantity
            INTO v_quantity_on_payment_date
            FROM portfolio_asset_daily_values pav
            WHERE pav.portfolio_asset_id = r_pa.pa_id
              AND pav.report_date <= r_payout.payment_date
            ORDER BY pav.report_date DESC
            LIMIT 1;

            IF v_quantity_on_payment_date IS NULL OR v_quantity_on_payment_date <= 0 THEN
                CONTINUE;
            END IF;

            v_expected_amount := r_payout.value * v_quantity_on_date;
            v_expected_tolerance := GREATEST(0.01, ABS(v_expected_amount) * 0.03);

            IF r_payout.type_id = 2 THEN
                v_operation_type_id := v_type_coupon;
            ELSIF r_payout.type_id = 1 THEN
                v_operation_type_id := v_type_dividend;
            ELSE
                v_operation_type_id := v_type_amortization;
            END IF;

            IF v_payout_currency_id = v_rub_currency_id THEN
                v_payout_currency_to_rub_rate := 1;
            ELSE
                SELECT quote_asset_id INTO v_quote_currency_id
                FROM assets
                WHERE id = v_payout_currency_id;

                IF v_quote_currency_id IS NULL OR v_quote_currency_id = v_rub_currency_id OR v_quote_currency_id = 1 THEN
                    SELECT price INTO v_payout_currency_to_rub_rate
                    FROM asset_prices
                    WHERE asset_id = v_payout_currency_id
                      AND trade_date <= r_payout.payment_date
                    ORDER BY trade_date DESC
                    LIMIT 1;
                ELSE
                    SELECT price INTO v_currency_to_quote_rate
                    FROM asset_prices
                    WHERE asset_id = v_payout_currency_id
                      AND trade_date <= r_payout.payment_date
                    ORDER BY trade_date DESC
                    LIMIT 1;

                    SELECT price INTO v_quote_to_rub_rate
                    FROM asset_prices
                    WHERE asset_id = v_quote_currency_id
                      AND trade_date <= r_payout.payment_date
                    ORDER BY trade_date DESC
                    LIMIT 1;

                    IF v_currency_to_quote_rate IS NOT NULL AND v_quote_to_rub_rate IS NOT NULL THEN
                        v_payout_currency_to_rub_rate := v_currency_to_quote_rate * v_quote_to_rub_rate;
                    ELSE
                        v_payout_currency_to_rub_rate := NULL;
                    END IF;
                END IF;

                IF v_payout_currency_to_rub_rate IS NULL OR v_payout_currency_to_rub_rate <= 0 THEN
                    SELECT curr_price INTO v_payout_currency_to_rub_rate
                    FROM asset_latest_prices
                    WHERE asset_id = v_payout_currency_id;
                END IF;
            END IF;

            SELECT COALESCE(
                SUM(
                    CASE
                        WHEN co.currency = v_payout_currency_id THEN ABS(COALESCE(co.amount, 0))
                        WHEN co.currency = v_rub_currency_id
                             AND v_payout_currency_to_rub_rate IS NOT NULL
                             AND v_payout_currency_to_rub_rate > 0
                        THEN ABS(COALESCE(co.amount_rub, co.amount, 0)) / v_payout_currency_to_rub_rate
                        ELSE 0
                    END
                ),
                0
            )
            INTO v_received_amount_in_payout_ccy
            FROM cash_operations co
            WHERE co.user_id = r_pa.user_id
              AND co.portfolio_id = r_pa.portfolio_id
              AND co.asset_id = r_pa.asset_id
              AND co.type = v_operation_type_id
              AND co.date::date BETWEEN r_payout.payment_date - INTERVAL '14 days'
                                    AND r_payout.payment_date + INTERVAL '14 days';

            IF v_received_amount_in_payout_ccy >= v_expected_amount - v_expected_tolerance THEN
                v_status := 'received';
            ELSE
                v_status := 'missed';
            END IF;

            v_obj := jsonb_build_object(
                'id', r_payout.id,
                'last_buy_date', r_payout.last_buy_date,
                'record_date', r_payout.record_date,
                'payment_date', r_payout.payment_date,
                'value', r_payout.value,
                'dividend_yield', r_payout.dividend_yield,
                'type', r_payout.type_code,
                'status', v_status,
                'expected_total', v_expected_amount,
                'basis_quantity', v_quantity_on_date,
                'received_total', v_received_amount_in_payout_ccy
            );

            IF v_status = 'received' THEN
                v_received := v_received || jsonb_build_array(v_obj);
            ELSE
                v_missed := v_missed || jsonb_build_array(v_obj);
            END IF;
            v_payouts := v_payouts || jsonb_build_array(v_obj);
        END LOOP;

        v_elem := jsonb_build_object(
            'portfolio_id', r_pa.portfolio_id,
            'portfolio_asset_id', r_pa.pa_id,
            'asset_id', r_pa.asset_id,
            'name', r_pa.asset_name,
            'ticker', r_pa.asset_ticker,
            'quantity', COALESCE(r_pa.quantity, 0),
            'currency_ticker', r_pa.currency_ticker,
            'received_payouts', v_received,
            'future_payouts', v_future,
            'missed_payouts', v_missed,
            'payouts', v_payouts
        );
        v_positions := v_positions || jsonb_build_array(v_elem);
    END LOOP;

    RETURN json_build_object(
        'positions',
        COALESCE(
            (
                SELECT jsonb_agg(elem ORDER BY (elem->>'portfolio_asset_id'))
                FROM jsonb_array_elements(v_positions) AS t(elem)
            ),
            '[]'::jsonb
        )
    )::json;
END;
$$;
