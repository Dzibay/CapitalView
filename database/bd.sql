-- WARNING: This schema is for context only and is not meant to be run.
-- Синхронизировано по смыслу с init.sql (NOT NULL, CASCADE, import_tasks.broker_id bigint).

CREATE TABLE public.users (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  email text NOT NULL UNIQUE,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  last_login_at timestamp with time zone,
  password_hash text,
  name text DEFAULT 'Профессиональный инвестор',
  email_verified boolean NOT NULL DEFAULT false,
  CONSTRAINT users_pkey PRIMARY KEY (id)
);

CREATE TABLE public.email_verification_tokens (
  id bigserial PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  token varchar(64) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL DEFAULT now() + interval '24 hours',
  used boolean NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS idx_evt_user_id ON public.email_verification_tokens(user_id);

CREATE TABLE public.support_messages (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  user_id uuid NOT NULL,
  message text NOT NULL,
  is_from_admin boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT support_messages_pkey PRIMARY KEY (id),
  CONSTRAINT support_messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_support_messages_user_id ON public.support_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_support_messages_created_at ON public.support_messages(created_at DESC);

CREATE TABLE public.asset_types (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  name text,
  is_custom boolean,
  CONSTRAINT asset_types_pkey PRIMARY KEY (id)
);

CREATE TABLE public.brokers (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  name text,
  CONSTRAINT brokers_pkey PRIMARY KEY (id)
);

CREATE TABLE public.operations_type (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  name text,
  CONSTRAINT operations_type_pkey PRIMARY KEY (id)
);

CREATE TABLE public.transactions_type (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  name text,
  CONSTRAINT transactions_type_pkey PRIMARY KEY (id)
);

CREATE TABLE public.portfolios (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  user_id uuid NOT NULL,
  parent_portfolio_id bigint,
  name text,
  description jsonb,
  CONSTRAINT portfolios_pkey PRIMARY KEY (id),
  CONSTRAINT portfolios_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT portfolios_parent_portfolio_id_fkey FOREIGN KEY (parent_portfolio_id) REFERENCES public.portfolios(id)
);

CREATE TABLE public.assets (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  asset_type_id bigint NOT NULL,
  user_id uuid,
  name text,
  ticker text,
  properties jsonb,
  quote_asset_id bigint NOT NULL DEFAULT 1,
  CONSTRAINT assets_pkey PRIMARY KEY (id),
  CONSTRAINT assets_asset_type_id_fkey FOREIGN KEY (asset_type_id) REFERENCES public.asset_types(id),
  CONSTRAINT assets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT assets_quote_asset_id_fkey FOREIGN KEY (quote_asset_id) REFERENCES public.assets(id)
);

CREATE TABLE public.portfolio_assets (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  portfolio_id bigint NOT NULL,
  asset_id bigint NOT NULL,
  quantity numeric(20,6),
  average_price numeric(20,6),
  created_at timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP,
  leverage bigint NOT NULL DEFAULT 1,
  CONSTRAINT portfolio_assets_pkey PRIMARY KEY (id),
  CONSTRAINT portfolio_assets_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id) ON DELETE CASCADE,
  CONSTRAINT portfolio_assets_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id)
);

CREATE TABLE public.transactions (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  portfolio_asset_id bigint NOT NULL,
  transaction_type bigint NOT NULL,
  price numeric(20,6) NOT NULL,
  quantity numeric(20,6) NOT NULL,
  transaction_date timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP,
  realized_pnl numeric(20,6),
  CONSTRAINT transactions_pkey PRIMARY KEY (id),
  CONSTRAINT transactions_portfolio_asset_id_fkey FOREIGN KEY (portfolio_asset_id) REFERENCES public.portfolio_assets(id) ON DELETE CASCADE,
  CONSTRAINT transactions_transaction_type_fkey FOREIGN KEY (transaction_type) REFERENCES public.transactions_type(id)
);

CREATE TABLE public.cash_operations (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  user_id uuid NOT NULL,
  portfolio_id bigint NOT NULL,
  type bigint NOT NULL,
  amount numeric(20,6) NOT NULL,
  currency bigint NOT NULL,
  date date NOT NULL,
  transaction_id bigint,
  asset_id bigint,
  amount_rub numeric(20,6),
  commission numeric(20,6) NOT NULL DEFAULT 0,
  commission_rub numeric(20,6),
  CONSTRAINT cash_operations_pkey PRIMARY KEY (id),
  CONSTRAINT cash_operations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT cash_operations_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id) ON DELETE CASCADE,
  CONSTRAINT cash_operations_currency_fkey FOREIGN KEY (currency) REFERENCES public.assets(id),
  CONSTRAINT cash_operations_type_fkey FOREIGN KEY (type) REFERENCES public.operations_type(id),
  CONSTRAINT cash_operations_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES public.transactions(id) ON DELETE CASCADE,
  CONSTRAINT cash_operations_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id)
);

CREATE TABLE public.fifo_lots (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  portfolio_asset_id bigint NOT NULL,
  remaining_qty numeric,
  price numeric,
  created_at timestamp without time zone,
  CONSTRAINT fifo_lots_pkey PRIMARY KEY (id),
  CONSTRAINT fifo_lots_portfolio_asset_id_fkey FOREIGN KEY (portfolio_asset_id) REFERENCES public.portfolio_assets(id) ON DELETE CASCADE
);

CREATE TABLE public.asset_prices (
  asset_id bigint NOT NULL,
  price numeric(20,6) NOT NULL,
  trade_date date NOT NULL,
  accrued_coupon numeric(20,6) NOT NULL DEFAULT 0,
  CONSTRAINT asset_prices_pkey PRIMARY KEY (asset_id, trade_date),
  CONSTRAINT asset_prices_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE CASCADE
);

CREATE TABLE public.payout_types (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  code text NOT NULL,
  name_ru text NOT NULL,
  CONSTRAINT payout_types_pkey PRIMARY KEY (id),
  CONSTRAINT payout_types_code_key UNIQUE (code)
);

CREATE TABLE public.asset_payouts (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  asset_id bigint NOT NULL,
  value numeric(20,6),
  dividend_yield numeric(10,4),
  last_buy_date date,
  record_date date,
  payment_date date,
  type_id bigint NOT NULL,
  CONSTRAINT asset_payouts_pkey PRIMARY KEY (id),
  CONSTRAINT asset_payouts_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE CASCADE,
  CONSTRAINT asset_payouts_type_id_fkey FOREIGN KEY (type_id) REFERENCES public.payout_types(id)
);

CREATE TABLE public.asset_splits (
  asset_id bigint NOT NULL,
  trade_date date NOT NULL,
  ratio_before numeric(20,6) NOT NULL,
  ratio_after numeric(20,6) NOT NULL,
  CONSTRAINT asset_splits_pkey PRIMARY KEY (asset_id, trade_date),
  CONSTRAINT asset_splits_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE CASCADE,
  CONSTRAINT asset_splits_ratio_positive CHECK (ratio_before > 0 AND ratio_after > 0)
);

CREATE TABLE public.asset_latest_prices (
  asset_id bigint NOT NULL,
  today_price numeric(20,6),
  today_date date,
  yesterday_price numeric(20,6),
  yesterday_date date,
  curr_price numeric(20,6),
  curr_date date,
  prev_price numeric(20,6),
  prev_date date,
  curr_accrued numeric(20,6) DEFAULT 0,
  updated_at timestamp(0) without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT asset_latest_prices_pkey PRIMARY KEY (asset_id),
  CONSTRAINT asset_latest_prices_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE CASCADE
);

CREATE TABLE public.portfolio_asset_daily_values (
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
  CONSTRAINT portfolio_asset_daily_values_portfolio_asset_id_fkey FOREIGN KEY (portfolio_asset_id) REFERENCES public.portfolio_assets(id) ON DELETE CASCADE,
  CONSTRAINT portfolio_asset_daily_values_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id) ON DELETE CASCADE
);

CREATE TABLE public.portfolio_daily_values (
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
  CONSTRAINT portfolio_daily_values_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id) ON DELETE CASCADE
);

CREATE TABLE public.import_tasks (
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
  CONSTRAINT import_tasks_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id) ON DELETE CASCADE,
  CONSTRAINT import_tasks_broker_id_fkey FOREIGN KEY (broker_id) REFERENCES public.brokers(id)
);

CREATE TABLE public.user_broker_connections (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  broker_id bigint NOT NULL,
  portfolio_id bigint NOT NULL,
  api_key text,
  last_sync_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP(0),
  CONSTRAINT user_broker_connections_pkey PRIMARY KEY (id),
  CONSTRAINT user_broker_connections_broker_id_fkey FOREIGN KEY (broker_id) REFERENCES public.brokers(id),
  CONSTRAINT user_broker_connections_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id) ON DELETE CASCADE,
  CONSTRAINT user_broker_connections_portfolio_broker_unique UNIQUE (portfolio_id, broker_id)
);

CREATE TABLE public.missed_payouts (
  portfolio_asset_id bigint NOT NULL,
  payout_id bigint NOT NULL,
  CONSTRAINT missed_payouts_pkey PRIMARY KEY (portfolio_asset_id, payout_id),
  CONSTRAINT missed_payouts_portfolio_asset_id_fkey FOREIGN KEY (portfolio_asset_id) REFERENCES public.portfolio_assets(id) ON DELETE CASCADE,
  CONSTRAINT missed_payouts_payout_id_fkey FOREIGN KEY (payout_id) REFERENCES public.asset_payouts(id) ON DELETE CASCADE
);
