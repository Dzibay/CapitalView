-- =============================================================================
-- CapitalView — Инициализация БД (таблицы, справочники, индексы)
-- =============================================================================
-- Запуск с сервера (БД без внешнего IP, доступна только из приватной сети):
--   docker compose run --rm backend python -m scripts.init_db
-- =============================================================================

-- Таблицы в порядке зависимостей (FK)
CREATE TABLE IF NOT EXISTS users (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  email text NOT NULL UNIQUE,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  password_hash text,
  name text DEFAULT 'Профессиональный инвестор',
  CONSTRAINT users_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS asset_types (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  name text,
  is_custom boolean,
  CONSTRAINT asset_types_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS brokers (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  name text,
  CONSTRAINT brokers_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS operations_type (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  name text,
  CONSTRAINT operations_type_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS transactions_type (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  name text,
  CONSTRAINT transactions_type_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS portfolios (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  user_id uuid NOT NULL,
  parent_portfolio_id bigint,
  name text,
  description jsonb,
  CONSTRAINT portfolios_pkey PRIMARY KEY (id),
  CONSTRAINT portfolios_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT portfolios_parent_portfolio_id_fkey FOREIGN KEY (parent_portfolio_id) REFERENCES portfolios(id)
);

-- assets: сначала без FK quote_asset_id (циклическая ссылка)
CREATE TABLE IF NOT EXISTS assets (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  asset_type_id bigint NOT NULL,
  user_id uuid,
  name text,
  ticker text,
  properties jsonb,
  quote_asset_id bigint NOT NULL DEFAULT 1,
  CONSTRAINT assets_pkey PRIMARY KEY (id),
  CONSTRAINT assets_asset_type_id_fkey FOREIGN KEY (asset_type_id) REFERENCES asset_types(id),
  CONSTRAINT assets_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS portfolio_assets (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  portfolio_id bigint NOT NULL,
  asset_id bigint NOT NULL,
  quantity numeric(20,6),
  average_price numeric(20,6),
  created_at timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP,
  leverage bigint NOT NULL DEFAULT 1,
  CONSTRAINT portfolio_assets_pkey PRIMARY KEY (id),
  CONSTRAINT portfolio_assets_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
  CONSTRAINT portfolio_assets_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES assets(id)
);

CREATE TABLE IF NOT EXISTS transactions (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  portfolio_asset_id bigint NOT NULL,
  transaction_type bigint NOT NULL,
  price numeric(20,6) NOT NULL,
  quantity numeric(20,6) NOT NULL,
  transaction_date timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP,
  realized_pnl numeric(20,6),
  CONSTRAINT transactions_pkey PRIMARY KEY (id),
  CONSTRAINT transactions_portfolio_asset_id_fkey FOREIGN KEY (portfolio_asset_id) REFERENCES portfolio_assets(id) ON DELETE CASCADE,
  CONSTRAINT transactions_transaction_type_fkey FOREIGN KEY (transaction_type) REFERENCES transactions_type(id)
);

CREATE TABLE IF NOT EXISTS cash_operations (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  user_id uuid NOT NULL,
  portfolio_id bigint NOT NULL,
  type bigint NOT NULL,
  amount numeric(20,6) NOT NULL,
  currency bigint NOT NULL,
  date date NOT NULL,
  transaction_id bigint,
  asset_id bigint,
  amount_rub numeric(20,2),
  CONSTRAINT cash_operations_pkey PRIMARY KEY (id),
  CONSTRAINT cash_operations_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT cash_operations_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
  CONSTRAINT cash_operations_currency_fkey FOREIGN KEY (currency) REFERENCES assets(id),
  CONSTRAINT cash_operations_type_fkey FOREIGN KEY (type) REFERENCES operations_type(id),
  CONSTRAINT cash_operations_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE SET NULL,
  CONSTRAINT cash_operations_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES assets(id)
);

CREATE TABLE IF NOT EXISTS fifo_lots (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  portfolio_asset_id bigint NOT NULL,
  remaining_qty numeric,
  price numeric,
  created_at timestamp without time zone,
  CONSTRAINT fifo_lots_pkey PRIMARY KEY (id),
  CONSTRAINT fifo_lots_portfolio_asset_id_fkey FOREIGN KEY (portfolio_asset_id) REFERENCES portfolio_assets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS asset_prices (
  asset_id bigint NOT NULL,
  price numeric(20,6) NOT NULL,
  trade_date date NOT NULL,
  CONSTRAINT asset_prices_pkey PRIMARY KEY (asset_id, trade_date),
  CONSTRAINT asset_prices_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS asset_payouts (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  asset_id bigint NOT NULL,
  value numeric(20,6),
  dividend_yield numeric(10,4),
  last_buy_date date,
  record_date date,
  payment_date date,
  type text,
  CONSTRAINT asset_payouts_pkey PRIMARY KEY (id),
  CONSTRAINT asset_payouts_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS asset_latest_prices (
  asset_id bigint NOT NULL,
  today_price numeric(20,6),
  today_date date,
  yesterday_price numeric(20,6),
  yesterday_date date,
  curr_price numeric(20,6),
  curr_date date,
  prev_price numeric(20,6),
  prev_date date,
  updated_at timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT asset_latest_prices_pkey PRIMARY KEY (asset_id),
  CONSTRAINT asset_latest_prices_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS portfolio_asset_daily_values (
  portfolio_id bigint NOT NULL,
  portfolio_asset_id bigint NOT NULL,
  report_date date NOT NULL,
  quantity numeric NOT NULL,
  cumulative_invested numeric NOT NULL,
  average_price numeric NOT NULL,
  position_value numeric,
  realized_pnl numeric DEFAULT 0,
  payouts numeric DEFAULT 0,
  commissions numeric DEFAULT 0,
  taxes numeric DEFAULT 0,
  total_pnl numeric,
  CONSTRAINT portfolio_asset_daily_values_pkey PRIMARY KEY (portfolio_asset_id, report_date),
  CONSTRAINT portfolio_asset_daily_values_portfolio_asset_id_fkey FOREIGN KEY (portfolio_asset_id) REFERENCES portfolio_assets(id) ON DELETE CASCADE,
  CONSTRAINT portfolio_asset_daily_values_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS portfolio_daily_values (
  portfolio_id bigint NOT NULL,
  report_date date NOT NULL,
  total_value numeric,
  total_invested numeric,
  total_payouts numeric,
  total_realized numeric,
  total_pnl numeric,
  total_commissions numeric DEFAULT 0,
  total_taxes numeric DEFAULT 0,
  balance numeric DEFAULT 0,
  CONSTRAINT portfolio_daily_values_pkey PRIMARY KEY (portfolio_id, report_date),
  CONSTRAINT portfolio_daily_values_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS import_tasks (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  portfolio_id bigint NOT NULL,
  task_type character varying NOT NULL,
  status character varying NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
  broker_id bigint NOT NULL,
  broker_token text,
  priority integer DEFAULT 0,
  created_at timestamp without time zone DEFAULT now(),
  started_at timestamp without time zone,
  completed_at timestamp without time zone,
  error_message text,
  result jsonb,
  retry_count integer DEFAULT 0,
  max_retries integer DEFAULT 3,
  progress integer DEFAULT 0,
  progress_message text,
  portfolio_name character varying,
  CONSTRAINT import_tasks_pkey PRIMARY KEY (id),
  CONSTRAINT import_tasks_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
  CONSTRAINT import_tasks_broker_id_fkey FOREIGN KEY (broker_id) REFERENCES brokers(id)
);

CREATE TABLE IF NOT EXISTS user_broker_connections (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  broker_id bigint NOT NULL,
  portfolio_id bigint NOT NULL,
  api_key text,
  last_sync_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP(0),
  CONSTRAINT user_broker_connections_pkey PRIMARY KEY (id),
  CONSTRAINT user_broker_connections_broker_id_fkey FOREIGN KEY (broker_id) REFERENCES brokers(id),
  CONSTRAINT user_broker_connections_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
  CONSTRAINT user_broker_connections_portfolio_broker_unique UNIQUE (portfolio_id, broker_id)
);

CREATE TABLE IF NOT EXISTS missed_payouts (
  portfolio_asset_id bigint NOT NULL,
  payout_id bigint NOT NULL,
  CONSTRAINT missed_payouts_pkey PRIMARY KEY (portfolio_asset_id, payout_id),
  CONSTRAINT missed_payouts_portfolio_asset_id_fkey FOREIGN KEY (portfolio_asset_id) REFERENCES portfolio_assets(id) ON DELETE CASCADE,
  CONSTRAINT missed_payouts_payout_id_fkey FOREIGN KEY (payout_id) REFERENCES asset_payouts(id) ON DELETE CASCADE
);

-- Справочные данные (если пусто)
INSERT INTO asset_types (id, name, is_custom) OVERRIDING SYSTEM VALUE VALUES
  (1, 'Акция', false),
  (2, 'Облигация', false),
  (3, 'Фонд', false),
  (4, 'Опцион', false),
  (5, 'Фьючерс', false),
  (6, 'Криптовалюта', false),
  (7, 'Валюта', false),
  (8, 'Недвижимость', true),
  (9, 'Драгоценная монета', true),
  (10, 'Вклад', true),
  (11, 'Другое', true)
ON CONFLICT (id) DO NOTHING;

-- Валюты (asset_type_id=7, quote_asset_id=1=RUB)
-- RUB — id=1 обязателен (базовая валюта, циклическая ссылка)
INSERT INTO assets (id, asset_type_id, user_id, name, ticker, quote_asset_id) OVERRIDING SYSTEM VALUE
SELECT 1, 7, NULL, 'Российский рубль', 'RUB', 1
WHERE NOT EXISTS (SELECT 1 FROM assets WHERE id = 1);

-- Остальные валюты — по ticker (без фиксированного id, чтобы не конфликтовать с MOEX и др.)
INSERT INTO assets (asset_type_id, user_id, name, ticker, quote_asset_id)
SELECT 7, NULL, 'Доллар США', 'USD', 1
WHERE NOT EXISTS (SELECT 1 FROM assets WHERE ticker = 'USD' AND user_id IS NULL);

INSERT INTO assets (asset_type_id, user_id, name, ticker, quote_asset_id)
SELECT 7, NULL, 'Евро', 'EUR', 1
WHERE NOT EXISTS (SELECT 1 FROM assets WHERE ticker = 'EUR' AND user_id IS NULL);

INSERT INTO assets (asset_type_id, user_id, name, ticker, quote_asset_id)
SELECT 7, NULL, 'Китайский юань', 'CNY', 1
WHERE NOT EXISTS (SELECT 1 FROM assets WHERE ticker = 'CNY' AND user_id IS NULL);

INSERT INTO assets (asset_type_id, user_id, name, ticker, quote_asset_id)
SELECT 7, NULL, 'Швейцарский франк', 'CHF', 1
WHERE NOT EXISTS (SELECT 1 FROM assets WHERE ticker = 'CHF' AND user_id IS NULL);

-- FK quote_asset_id (циклическая ссылка)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'assets_quote_asset_id_fkey') THEN
    ALTER TABLE assets ADD CONSTRAINT assets_quote_asset_id_fkey FOREIGN KEY (quote_asset_id) REFERENCES assets(id);
  END IF;
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

SELECT setval('asset_types_id_seq', (SELECT COALESCE(MAX(id), 1) FROM asset_types));
SELECT setval('assets_id_seq', (SELECT COALESCE(MAX(id), 1) FROM assets));

INSERT INTO brokers (id, name) OVERRIDING SYSTEM VALUE VALUES
  (1, 'Т-Инвестиции'),
  (2, 'БКС')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

INSERT INTO operations_type (id, name) OVERRIDING SYSTEM VALUE VALUES
  (1, 'Buy'),
  (2, 'Sell'),
  (3, 'Dividend'),
  (4, 'Coupon'),
  (5, 'Deposit'),
  (6, 'Withdraw'),
  (7, 'Commission'),
  (8, 'Tax'),
  (9, 'Redemption'),
  (10, 'Other')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

INSERT INTO transactions_type (id, name) OVERRIDING SYSTEM VALUE VALUES
  (1, 'Buy'),
  (2, 'Sell'),
  (3, 'Redemption')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;
