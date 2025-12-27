 SELECT DISTINCT ON (a.id) a.id AS asset_id,
    a.name,
    a.ticker,
    ap.price,
    ap.trade_date
   FROM (assets a
     JOIN asset_prices ap ON ((ap.asset_id = a.id)))
  WHERE (a.id IN ( SELECT DISTINCT assets.quote_asset_id
           FROM assets
          WHERE (assets.quote_asset_id IS NOT NULL)))
  ORDER BY a.id, ap.trade_date DESC;