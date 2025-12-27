 SELECT id AS asset_id,
    ( SELECT ap.price
           FROM asset_prices ap
          WHERE ((ap.asset_id = a.id) AND ((ap.trade_date)::date = CURRENT_DATE))
          ORDER BY ap.trade_date DESC
         LIMIT 1) AS today_price,
    ( SELECT (ap.trade_date)::date AS trade_date
           FROM asset_prices ap
          WHERE ((ap.asset_id = a.id) AND ((ap.trade_date)::date = CURRENT_DATE))
          ORDER BY ap.trade_date DESC
         LIMIT 1) AS today_date,
    ( SELECT ap.price
           FROM asset_prices ap
          WHERE ((ap.asset_id = a.id) AND ((ap.trade_date)::date = (CURRENT_DATE - 1)))
          ORDER BY ap.trade_date DESC
         LIMIT 1) AS yesterday_price,
    ( SELECT (ap.trade_date)::date AS trade_date
           FROM asset_prices ap
          WHERE ((ap.asset_id = a.id) AND ((ap.trade_date)::date = (CURRENT_DATE - 1)))
          ORDER BY ap.trade_date DESC
         LIMIT 1) AS yesterday_date,
    COALESCE(( SELECT ap.price
           FROM asset_prices ap
          WHERE ((ap.asset_id = a.id) AND ((ap.trade_date)::date = ANY (ARRAY[CURRENT_DATE, (CURRENT_DATE - 1)])))
          ORDER BY ap.trade_date DESC
         LIMIT 1), ( SELECT ap.price
           FROM asset_prices ap
          WHERE (ap.asset_id = a.id)
          ORDER BY ap.trade_date DESC
         LIMIT 1)) AS curr_price,
    COALESCE(( SELECT (ap.trade_date)::date AS trade_date
           FROM asset_prices ap
          WHERE ((ap.asset_id = a.id) AND ((ap.trade_date)::date = ANY (ARRAY[CURRENT_DATE, (CURRENT_DATE - 1)])))
          ORDER BY ap.trade_date DESC
         LIMIT 1), ( SELECT (ap.trade_date)::date AS trade_date
           FROM asset_prices ap
          WHERE (ap.asset_id = a.id)
          ORDER BY ap.trade_date DESC
         LIMIT 1)) AS curr_date,
    ( SELECT ap.price
           FROM asset_prices ap
          WHERE ((ap.asset_id = a.id) AND (ap.trade_date < ( SELECT max(ap2.trade_date) AS max
                   FROM asset_prices ap2
                  WHERE (ap2.asset_id = a.id))))
          ORDER BY ap.trade_date DESC
         LIMIT 1) AS prev_price,
    ( SELECT (ap.trade_date)::date AS trade_date
           FROM asset_prices ap
          WHERE ((ap.asset_id = a.id) AND (ap.trade_date < ( SELECT max(ap2.trade_date) AS max
                   FROM asset_prices ap2
                  WHERE (ap2.asset_id = a.id))))
          ORDER BY ap.trade_date DESC
         LIMIT 1) AS prev_date
   FROM assets a;