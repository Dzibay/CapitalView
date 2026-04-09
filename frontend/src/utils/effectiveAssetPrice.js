/**
 * Единая цена позиции в валюте актива: чистая котировка + НКД (облигации).
 * На бэкенде last_price — чистая, accrued_coupon — НКД на бумагу; для акций nkd = 0.
 * Округление до 2 знаков — иначе clean + nkd даёт «хвост» float в UI (101.44800000000001).
 */
export function effectiveUnitPriceInCurrency(asset) {
  if (!asset) return 0
  const clean = Number(asset.last_price ?? 0)
  const nkd = Number(asset.accrued_coupon ?? 0)
  const sum = clean + nkd
  if (!Number.isFinite(sum)) return 0
  return Math.round(sum * 100) / 100
}
