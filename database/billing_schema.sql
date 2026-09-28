-- =============================================================================
-- Billing: тарифы, настройки ЮKassa, подписки и платежи
-- =============================================================================

CREATE TABLE IF NOT EXISTS billing_settings (
  id integer PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  trial_days integer NOT NULL DEFAULT 14 CHECK (trial_days >= 0),
  yookassa_shop_id text NOT NULL DEFAULT '',
  yookassa_secret_key text NOT NULL DEFAULT '',
  updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO billing_settings (id, trial_days)
VALUES (1, 14)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS tariffs (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name text NOT NULL,
  description text NOT NULL DEFAULT '',
  price_rub numeric(12, 2) NOT NULL CHECK (price_rub >= 0),
  period_days integer NOT NULL CHECK (period_days > 0),
  is_active boolean NOT NULL DEFAULT true,
  sort_order integer NOT NULL DEFAULT 0,
  features jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_subscriptions (
  user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  status text NOT NULL DEFAULT 'trial'
    CHECK (status IN ('trial', 'active', 'expired')),
  tariff_id bigint REFERENCES tariffs(id) ON DELETE SET NULL,
  trial_ends_at timestamptz,
  current_period_ends_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_status
  ON user_subscriptions(status);

CREATE TABLE IF NOT EXISTS payments (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tariff_id bigint NOT NULL REFERENCES tariffs(id),
  yookassa_payment_id text UNIQUE,
  amount_rub numeric(12, 2) NOT NULL,
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'waiting_for_capture', 'succeeded', 'canceled')),
  confirmation_url text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_yookassa_payment_id ON payments(yookassa_payment_id);

-- Существующим пользователям — пробный период с текущего момента (grace при внедрении)
INSERT INTO user_subscriptions (user_id, status, trial_ends_at, updated_at)
SELECT
  u.id,
  'trial',
  now() + ((SELECT trial_days FROM billing_settings WHERE id = 1) * interval '1 day'),
  now()
FROM users u
WHERE NOT EXISTS (
  SELECT 1 FROM user_subscriptions s WHERE s.user_id = u.id
);
