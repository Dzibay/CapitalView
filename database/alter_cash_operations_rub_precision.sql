-- Увеличить точность рублёвых сумм в cash_operations (накопление баланса и сверка с брокером).
-- Выполнить один раз на существующей БД после бэкапа.
ALTER TABLE public.cash_operations
  ALTER COLUMN amount_rub TYPE numeric(20,6),
  ALTER COLUMN commission_rub TYPE numeric(20,6);
