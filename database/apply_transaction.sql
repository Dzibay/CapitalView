drop function apply_transaction;
create or replace function apply_transaction(
  p_user_id uuid,
  p_portfolio_asset_id bigint,
  p_transaction_type int,   -- 1=buy, 2=sell
  p_quantity numeric,
  p_price numeric,
  p_transaction_date date
)
returns bigint
language plpgsql
as $$
declare
  v_tx_id bigint;
  v_remaining numeric;
  v_realized numeric := 0;
  v_portfolio_id bigint;
  lot record;
begin
  ------------------------------------------------------------------
  -- 0. Получаем portfolio_id
  ------------------------------------------------------------------
  select portfolio_id
  into v_portfolio_id
  from portfolio_assets
  where id = p_portfolio_asset_id;

  if v_portfolio_id is null then
    raise exception
      'Portfolio not found for portfolio_asset_id=%',
      p_portfolio_asset_id;
  end if;

  ------------------------------------------------------------------
  -- 1. Создаём транзакцию
  ------------------------------------------------------------------
  insert into transactions (
    user_id,
    portfolio_asset_id,
    transaction_type,
    quantity,
    price,
    transaction_date,
    realized_pnl
  )
  values (
    p_user_id,
    p_portfolio_asset_id,
    p_transaction_type,
    p_quantity,
    p_price,
    p_transaction_date,
    0
  )
  returning id into v_tx_id;

  ------------------------------------------------------------------
  -- 2. BUY → FIFO-лот
  ------------------------------------------------------------------
  if p_transaction_type = 1 then
    insert into fifo_lots (
      portfolio_asset_id,
      remaining_qty,
      price,
      created_at
    )
    values (
      p_portfolio_asset_id,
      p_quantity,
      p_price,
      p_transaction_date
    );

  ------------------------------------------------------------------
  -- 3. SELL → FIFO
  ------------------------------------------------------------------
  elsif p_transaction_type = 2 then
    v_remaining := p_quantity;

    for lot in
      select *
      from fifo_lots
      where portfolio_asset_id = p_portfolio_asset_id
        and remaining_qty > 0
      order by created_at, id
      for update
    loop
      exit when v_remaining <= 0;

      if lot.remaining_qty <= v_remaining then
        v_realized := v_realized +
          lot.remaining_qty * (p_price - lot.price);

        v_remaining := v_remaining - lot.remaining_qty;

        update fifo_lots
        set remaining_qty = 0
        where id = lot.id;
      else
        v_realized := v_realized +
          v_remaining * (p_price - lot.price);

        update fifo_lots
        set remaining_qty = lot.remaining_qty - v_remaining
        where id = lot.id;

        v_remaining := 0;
      end if;
    end loop;

    if v_remaining > 0 then
      raise exception
        'Not enough quantity to sell (portfolio_asset_id=%)',
        p_portfolio_asset_id;
    end if;

    update transactions
    set realized_pnl = v_realized
    where id = v_tx_id;
  end if;

  ------------------------------------------------------------------
  -- 4. Пересчёты
  ------------------------------------------------------------------
  perform update_portfolio_asset_positions_from_date(
    p_portfolio_asset_id,
    p_transaction_date - 1
  );

  perform update_portfolio_values_from_date(
    v_portfolio_id,
    p_transaction_date - 1
  );

  ------------------------------------------------------------------
  return v_tx_id;
end;
$$;
