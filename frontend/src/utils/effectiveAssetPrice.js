/**
 * Единая цена позиции в валюте актива: чистая котировка + НКД (облигации).
 * На бэкенде last_price — чистая, accrued_coupon — НКД на бумагу; для акций nkd = 0.
 */
export function effectiveUnitPriceInCurrency(asset) {
  if (!asset) return 0
  const clean = Number(asset.last_price ?? 0)
  const nkd = Number(asset.accrued_coupon ?? 0)
  return clean + nkd
}
