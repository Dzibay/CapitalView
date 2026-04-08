-- Существующие БД: последний успешный вход (пароль / Google / подтверждение email).
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at timestamptz NULL;
