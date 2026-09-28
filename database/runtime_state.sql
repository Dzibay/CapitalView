-- Runtime state for idempotent bootstrap and scheduled reference updates.
CREATE TABLE IF NOT EXISTS service_state (
    state_key text PRIMARY KEY,
    state_value jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamptz NOT NULL DEFAULT now()
);
