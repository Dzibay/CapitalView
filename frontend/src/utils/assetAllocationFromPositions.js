import { effectiveUnitPriceInCurrency } from './effectiveAssetPrice'

/**
 * Распределение по типам активов из списка позиций (как в dashboard.assets).
 */
export function assetAllocationFromPositions(assets) {
  if (!assets?.length) {
    return {
      labels: [],
      datasets: [{ backgroundColor: [], data: [] }],
    }
  }
  const allocation = {}
  for (const asset of assets) {
    const atype = asset.type
    if (!atype) continue
    const quantity = Number(asset.quantity || 0)
    const price = effectiveUnitPriceInCurrency(asset)
    const currencyMultiplier = Number(asset.currency_rate_to_rub || 1)
    const lev = Number(asset.leverage || 1) || 1
    allocation[atype] =
      (allocation[atype] || 0) + (quantity * price * currencyMultiplier) / lev
  }
  return {
    labels: Object.keys(allocation),
    datasets: [
      {
        backgroundColor: [
          '#7381ff', '#b0b8ff', '#5060dc', '#c6cad6', '#8e93a5', '#5f6478', '#a08cf5', '#7a7f92', '#464a57',
        ],
        data: Object.values(allocation),
      },
    ],
  }
}
