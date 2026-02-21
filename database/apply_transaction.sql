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
  v_asset_id bigint;
  v_buy_op_type_id bigint;
  v_sell_op_type_id bigint;
  v_op_type_id bigint;
  v_cash_amount numeric;
  v_amount_rub numeric;
  v_tx_after integer;
  v_needs_rebuild boolean := false;
  v_asset_quote_asset_id bigint;
  v_rub_currency_id bigint;
  v_currency_to_quote_rate numeric(20,6);
  v_quote_to_rub_rate numeric(20,6);
  v_amount_in_quote numeric(20,6);
  v_currency_rate numeric(20,6);
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
  -- 0.5. Проверяем, не нарушает ли новая транзакция порядок FIFO
  ------------------------------------------------------------------
  -- FIFO должен быть пересчитан, если новая транзакция вставляется
  -- между существующими транзакциями (есть транзакции после неё)
  -- Это нужно, чтобы продажи использовали правильные лоты в правильном порядке
  SELECT 
    COUNT(*) FILTER (WHERE transaction_date::date > p_transaction_date::date) AS tx_after
  INTO v_tx_after
  FROM transactions
  WHERE portfolio_asset_id = p_portfolio_asset_id;
  
  -- Пересчитываем FIFO если есть транзакции после новой
  -- (новая вставляется между существующими или раньше всех)
  IF v_tx_after > 0 THEN
    v_needs_rebuild := true;
  END IF;

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
  -- 2. Обрабатываем FIFO
  ------------------------------------------------------------------
  IF v_needs_rebuild THEN
    -- Если новая транзакция нарушает порядок - пересчитываем FIFO для всех транзакций
    PERFORM rebuild_fifo_for_portfolio_asset(p_portfolio_asset_id);
  ELSE
    -- Обычная обработка: создаем лот для покупки или обрабатываем продажу
    IF p_transaction_type = 1 THEN
      -- BUY → FIFO-лот
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
    ELSIF p_transaction_type = 2 THEN
      -- SELL → FIFO
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
    END IF;
  END IF;

  ------------------------------------------------------------------
  -- 4. Создаём денежную операцию для транзакции
  ------------------------------------------------------------------
  -- Получаем asset_id из portfolio_assets
  SELECT asset_id INTO v_asset_id
  FROM portfolio_assets
  WHERE id = p_portfolio_asset_id;
  
  -- Получаем quote_asset_id актива (валюта, в которой выражена цена актива)
  SELECT quote_asset_id INTO v_asset_quote_asset_id
  FROM assets
  WHERE id = v_asset_id;
  
  -- Получаем ID рубля
  SELECT id INTO v_rub_currency_id
  FROM assets
  WHERE ticker = 'RUB' AND user_id IS NULL
  LIMIT 1;
  
  -- Если v_rub_currency_id не найден, используем 47 как fallback
  IF v_rub_currency_id IS NULL THEN
    v_rub_currency_id := 47;
  END IF;
  
  -- Получаем ID типов операций
  SELECT id INTO v_buy_op_type_id FROM operations_type WHERE name = 'Buy' LIMIT 1;
  SELECT id INTO v_sell_op_type_id FROM operations_type WHERE name = 'Sell' LIMIT 1;
  
  -- Определяем тип операции и сумму в валюте актива
  IF p_transaction_type = 1 THEN
    v_op_type_id := v_buy_op_type_id;
    v_cash_amount := -(p_price * p_quantity);
  ELSIF p_transaction_type = 2 THEN
    v_op_type_id := v_sell_op_type_id;
    v_cash_amount := (p_price * p_quantity);
  END IF;
  
  -- Убеждаемся, что v_cash_amount не NULL
  IF v_cash_amount IS NULL THEN
    v_cash_amount := 0;
  END IF;
  
  -- Рассчитываем amount_rub: конвертируем из валюты актива в рубли
  -- p_price передается в валюте quote_asset_id актива (например, для BTC это USD)
  -- v_cash_amount = p_price * p_quantity в валюте quote_asset_id актива
  
  -- Если quote_asset_id актива = RUB или NULL, то цена уже в рублях
  IF v_asset_quote_asset_id IS NULL OR v_asset_quote_asset_id = v_rub_currency_id OR v_asset_quote_asset_id = 47 THEN
    -- Цена уже в рублях
    v_amount_rub := v_cash_amount;
  ELSE
    -- Цена в другой валюте (quote_asset_id актива), нужно конвертировать в рубли
    -- Например, для BTC: quote_asset_id = USD, нужно конвертировать USD -> RUB
    
    -- Получаем курс quote_asset актива к рублю на дату транзакции
    SELECT price INTO v_quote_to_rub_rate
    FROM asset_prices
    WHERE asset_id = v_asset_quote_asset_id
      AND CAST(trade_date AS date) <= CAST(p_transaction_date AS date)
    ORDER BY trade_date DESC
    LIMIT 1;
    
    -- Если исторический курс не найден, пробуем взять текущий курс
    IF v_quote_to_rub_rate IS NULL THEN
      SELECT price INTO v_quote_to_rub_rate
      FROM asset_last_currency_prices
      WHERE asset_id = v_asset_quote_asset_id;
    END IF;
    
    -- Если курс все еще не найден, используем 1 (fallback)
    IF v_quote_to_rub_rate IS NULL OR v_quote_to_rub_rate <= 0 THEN
      v_quote_to_rub_rate := 1;
      RAISE WARNING 'Курс для актива % (quote_asset актива) к рублю не найден для транзакции на дату %. Используется fallback = 1', v_asset_quote_asset_id, p_transaction_date;
    END IF;
    
    -- Рассчитываем сумму в рублях: amount в quote_asset * курс quote_asset->RUB
    -- Пример: для BTC с ценой 115700 USD и количеством 0.001:
    -- v_cash_amount = -115.7 USD
    -- v_amount_rub = -115.7 * курс_USD_to_RUB
    v_amount_rub := v_cash_amount * v_quote_to_rub_rate;
  END IF;
  
  -- Создаем cash_operation только если тип определен и её еще нет
  -- Для транзакций Buy/Sell валюта всегда RUB, но amount_rub рассчитывается с учетом валюты актива
  IF v_op_type_id IS NOT NULL THEN
    INSERT INTO cash_operations (user_id, portfolio_id, type, amount, currency, date, transaction_id, asset_id, amount_rub)
    SELECT
      p_user_id,
      v_portfolio_id,
      v_op_type_id,
      v_cash_amount,
      47, -- RUB (валюта операции всегда RUB)
      p_transaction_date,
      v_tx_id,
      v_asset_id,
      COALESCE(v_amount_rub, v_cash_amount) -- amount_rub конвертирован из валюты актива в рубли
    WHERE NOT EXISTS (
      SELECT 1 
      FROM cash_operations 
      WHERE transaction_id = v_tx_id
    );
  END IF;

  ------------------------------------------------------------------
  -- 5. Пересчёты
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
