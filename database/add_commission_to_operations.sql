-- Вложенная комиссия (Tinkoff: дочерние OPERATION_TYPE_*_FEE с parent_operation_id) — только в cash_operations.

ALTER TABLE public.transactions DROP COLUMN IF EXISTS commission;
ALTER TABLE public.transactions DROP COLUMN IF EXISTS commission_rub;

ALTER TABLE public.cash_operations
  ADD COLUMN IF NOT EXISTS commission numeric(20,6) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS commission_rub numeric(20,6);

COMMENT ON COLUMN public.cash_operations.commission IS 'Комиссия, вложенная в операцию (в т.ч. Buy/Sell по transaction_id)';
COMMENT ON COLUMN public.cash_operations.commission_rub IS 'Комиссия в рублях на дату операции';
