/**
 * Канонический знак суммы cash-операции по типу (как на бэкенде в apply_operations).
 * 6=Withdraw, 7=Commission, 8=Tax — расходы → отрицательное значение.
 * 3=Dividend, 4=Coupon, 5=Deposit — доходы → положительное.
 * 10=Other — без изменения знака.
 */
export function normalizeCashOperationAmount(operationType, amount) {
  const t = Number(operationType)
  const x = Number(amount)
  if (!Number.isFinite(x) || x === 0) return x
  if ([6, 7, 8].includes(t)) return -Math.abs(x)
  if ([3, 4, 5].includes(t)) return Math.abs(x)
  return x
}
