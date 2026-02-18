-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.accounts (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  portfolio_id bigint,
  name text,
  balance real,
  currency_id bigint,
  CONSTRAINT accounts_pkey PRIMARY KEY (id),
  CONSTRAINT accounts_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id),
  CONSTRAINT accounts_currency_id_fkey FOREIGN KEY (currency_id) REFERENCES public.assets(id)
);
CREATE TABLE public.asset_latest_prices_full (
  asset_id bigint NOT NULL,
  today_price real,
  today_date date,
  yesterday_price real,
  yesterday_date date,
  curr_price real,
  curr_date date,
  prev_price real,
  prev_date date,
  updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT asset_latest_prices_full_pkey PRIMARY KEY (asset_id),
  CONSTRAINT asset_latest_prices_full_table_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id)
);
CREATE TABLE public.asset_payouts (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  asset_id bigint,
  value real,
  dividend_yield real,
  last_buy_date date,
  record_date date,
  payment_date date,
  type text,
  CONSTRAINT asset_payouts_pkey PRIMARY KEY (id),
  CONSTRAINT asset_payouts_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id)
);
CREATE TABLE public.asset_prices (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL UNIQUE,
  asset_id bigint,
  price real,
  trade_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP(0),
  CONSTRAINT asset_prices_pkey PRIMARY KEY (id),
  CONSTRAINT asset_prices_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id)
);
CREATE TABLE public.asset_types (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  name text,
  is_custom boolean,
  CONSTRAINT asset_types_pkey PRIMARY KEY (id)
);
CREATE TABLE public.assets (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  asset_type_id bigint,
  user_id uuid,
  name text,
  ticker text,
  properties jsonb,
  quote_asset_id bigint DEFAULT '47'::bigint,
  CONSTRAINT assets_pkey PRIMARY KEY (id),
  CONSTRAINT assets1_asset_type_id_fkey FOREIGN KEY (asset_type_id) REFERENCES public.asset_types(id),
  CONSTRAINT assets1_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT assets_quote_asset_id_fkey FOREIGN KEY (quote_asset_id) REFERENCES public.assets(id)
);
CREATE TABLE public.brokers (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  name text,
  CONSTRAINT brokers_pkey PRIMARY KEY (id)
);
CREATE TABLE public.cash_operations (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  user_id uuid,
  portfolio_id bigint,
  type bigint,
  amount real,
  currency bigint,
  date timestamp without time zone,
  transaction_id bigint,
  asset_id bigint,
  CONSTRAINT cash_operations_pkey PRIMARY KEY (id),
  CONSTRAINT cash_operations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT cash_operations_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id),
  CONSTRAINT cash_operations_currency_fkey FOREIGN KEY (currency) REFERENCES public.assets(id),
  CONSTRAINT cash_operations_type_fkey FOREIGN KEY (type) REFERENCES public.operations_type(id),
  CONSTRAINT cash_operations_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES public.transactions(id),
  CONSTRAINT cash_operations_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id)
);
CREATE TABLE public.fifo_lots (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  portfolio_asset_id bigint,
  remaining_qty numeric,
  price numeric,
  created_at timestamp without time zone,
  CONSTRAINT fifo_lots_pkey PRIMARY KEY (id),
  CONSTRAINT fifo_lots_portfolio_asset_id_fkey FOREIGN KEY (portfolio_asset_id) REFERENCES public.portfolio_assets(id)
);
CREATE TABLE public.import_tasks (
  id integer NOT NULL DEFAULT nextval('import_tasks_id_seq'::regclass) UNIQUE,
  user_id uuid NOT NULL,
  portfolio_id integer,
  task_type character varying NOT NULL,
  status character varying NOT NULL DEFAULT 'pending'::character varying CHECK (status::text = ANY (ARRAY['pending'::character varying, 'processing'::character varying, 'completed'::character varying, 'failed'::character varying, 'cancelled'::character varying]::text[])),
  broker_id character varying,
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
  CONSTRAINT import_tasks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT import_tasks_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id)
);
CREATE TABLE public.operations_type (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  name text,
  CONSTRAINT operations_type_pkey PRIMARY KEY (id)
);
CREATE TABLE public.portfolio_assets (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  portfolio_id bigint,
  asset_id bigint,
  quantity real,
  average_price double precision,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP(0),
  leverage bigint DEFAULT '1'::bigint,
  CONSTRAINT portfolio_assets_pkey PRIMARY KEY (id),
  CONSTRAINT portfolio_assets_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id),
  CONSTRAINT portfolio_assets_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id)
);
CREATE TABLE public.portfolio_daily_positions (
  portfolio_id bigint NOT NULL,
  portfolio_asset_id bigint NOT NULL,
  tx_date date NOT NULL,
  quantity numeric NOT NULL,
  cumulative_invested numeric NOT NULL,
  average_price numeric NOT NULL,
  CONSTRAINT portfolio_daily_positions_pkey PRIMARY KEY (portfolio_asset_id, tx_date)
);
CREATE TABLE public.portfolio_daily_values (
  portfolio_id bigint NOT NULL,
  report_date date NOT NULL,
  total_value numeric,
  total_invested numeric,
  total_payouts numeric,
  total_realized numeric,
  total_commissions numeric,
  total_taxes numeric,
  total_pnl numeric,
  CONSTRAINT portfolio_daily_values_pkey PRIMARY KEY (portfolio_id, report_date)
);
CREATE TABLE public.portfolios (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  user_id uuid,
  parent_portfolio_id bigint,
  name text,
  description jsonb,
  CONSTRAINT portfolios_pkey PRIMARY KEY (id),
  CONSTRAINT portfolios_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT portfolios_parent_portfolio_id_fkey FOREIGN KEY (parent_portfolio_id) REFERENCES public.portfolios(id)
);
CREATE TABLE public.transactions (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  portfolio_asset_id bigint,
  transaction_type bigint,
  price double precision,
  quantity double precision,
  transaction_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP(0),
  user_id uuid,
  realized_pnl numeric,
  CONSTRAINT transactions_pkey PRIMARY KEY (id),
  CONSTRAINT transactions_portfolio_asset_id_fkey FOREIGN KEY (portfolio_asset_id) REFERENCES public.portfolio_assets(id),
  CONSTRAINT transactions_transaction_type_fkey FOREIGN KEY (transaction_type) REFERENCES public.transactions_type(id),
  CONSTRAINT transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.transactions_type (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  name text,
  CONSTRAINT transactions_type_pkey PRIMARY KEY (id)
);
CREATE TABLE public.user_broker_connections (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  user_id uuid,
  broker_id bigint,
  portfolio_id bigint,
  api_key text,
  last_sync_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP(0),
  CONSTRAINT user_broker_connections_pkey PRIMARY KEY (id),
  CONSTRAINT user_broker_connections_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT user_broker_connections_broker_id_fkey FOREIGN KEY (broker_id) REFERENCES public.brokers(id),
  CONSTRAINT user_broker_connections_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES public.portfolios(id)
);
CREATE TABLE public.users (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  email text NOT NULL UNIQUE,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  password_hash text,
  name text DEFAULT 'Профессиональный инвестор'::text,
  CONSTRAINT users_pkey PRIMARY KEY (id)
);