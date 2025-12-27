
  SELECT t.id, a.name, a.ticker, tt.name,
         t.quantity, t.price, t.transaction_date
  FROM transactions t
  JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
  JOIN assets a ON a.id = pa.asset_id
  JOIN transactions_type tt ON tt.id = t.transaction_type
  WHERE pa.portfolio_id = p_portfolio_id
  ORDER BY t.transaction_date DESC;
